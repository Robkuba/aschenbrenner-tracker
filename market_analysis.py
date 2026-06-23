#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
 MARKET ANALYSIS  -  Motor de senales para la cartera de agentes
=====================================================================
Toma el universo de trade_candidates.py, descarga precios (gratis, via
Stooq), calcula senales tecnicas sencillas y robustas, puntua cada
activo y PROPONE ordenes de compra dimensionadas por peso objetivo.

NO ejecuta nada. Su salida es:
  1) un informe legible por consola
  2) un fichero  proposed_orders.json  con las ordenes sugeridas

Tu revisas ese fichero, borras/editas lo que no quieras, y luego
trade_executor.py ejecuta SOLO lo aprobado.

Senales (deliberadamente simples y transparentes):
  - Tendencia : precio por encima de la media de 200 sesiones (SMA200)
  - Estructura: SMA50 por encima de SMA200 ("golden cross")
  - Momentum  : rentabilidad de los ultimos ~6 meses (126 sesiones)
  - Distancia a maximos: cuanto le falta a su maximo de 52 semanas

AVISO: esto NO es asesoramiento financiero. Senales tecnicas != certeza.
=====================================================================
"""

import os
import io
import csv
import json
import time
import urllib.request
from datetime import datetime

from trade_candidates import CANDIDATES

# Capital total asumido para dimensionar (USD). Cambialo por env.
CAPITAL_USD = float(os.environ.get("ETORO_CAPITAL_USD", "1000"))
PROPOSED_FILE = os.environ.get("PROPOSED_FILE", "proposed_orders.json")

STOOQ_HIST = "https://stooq.com/q/d/l/?s={sym}&i=d"


def _http_get(url, retries=3):
    headers = {"User-Agent": "Mozilla/5.0 (cartera-agentes etoro)"}
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            last = e
            time.sleep(1.0 * (i + 1))
    raise RuntimeError(f"No se pudo descargar {url}: {last}")


def fetch_history(symbol):
    """Devuelve lista de cierres (float) ordenados antiguo->reciente."""
    raw = _http_get(STOOQ_HIST.format(sym=symbol))
    closes = []
    for row in csv.DictReader(io.StringIO(raw)):
        c = row.get("Close") or row.get("close")
        try:
            closes.append(float(c))
        except (TypeError, ValueError):
            continue
    return closes


def sma(values, n):
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def analyze_one(cand):
    """Calcula senales y un score 0-100 para un candidato."""
    try:
        closes = fetch_history(cand["symbol"])
    except Exception as e:
        return {"ok": False, "error": str(e)}

    if len(closes) < 60:
        return {"ok": False, "error": "historico insuficiente"}

    price = closes[-1]
    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200) or sma(closes, min(len(closes), 150))
    high52 = max(closes[-252:]) if len(closes) >= 252 else max(closes)
    mom = None
    if len(closes) > 126:
        mom = (price / closes[-126] - 1) * 100  # % a ~6 meses

    # ----- puntuacion (transparente y acotada 0..100) -----
    score = 50
    above200 = sma200 is not None and price > sma200
    golden = sma50 is not None and sma200 is not None and sma50 > sma200
    if above200:
        score += 20
    else:
        score -= 15
    if golden:
        score += 10
    if mom is not None:
        score += max(-15, min(20, mom / 2.0))  # momentum acotado
    dist_high = (price / high52 - 1) * 100  # negativo si por debajo de maximos
    if dist_high > -5:
        score += 5   # cerca de maximos = fuerza
    if dist_high < -35:
        score -= 5   # caida fuerte = mas riesgo (o value)
    score = max(0, min(100, round(score)))

    if score >= 65 and above200:
        action = "BUY"
    elif score >= 50:
        action = "WATCH"
    else:
        action = "AVOID"

    # Stop-loss sugerido: el mayor entre -15% y la SMA200 (si esta debajo)
    stop = round(price * 0.85, 2)
    if sma200 and sma200 < price:
        stop = round(max(stop, sma200 * 0.98), 2)

    return {
        "ok": True, "price": round(price, 2),
        "sma50": round(sma50, 2) if sma50 else None,
        "sma200": round(sma200, 2) if sma200 else None,
        "above_sma200": above200, "golden_cross": golden,
        "momentum_6m_pct": round(mom, 1) if mom is not None else None,
        "dist_to_52w_high_pct": round(dist_high, 1),
        "score": score, "action": action, "stop_loss": stop,
    }


def size_order(cand, capital):
    """Importe sugerido = peso objetivo * capital (acotado por max_pct)."""
    pct = min(cand["target_pct"], cand["max_pct"])
    return round(capital * pct / 100.0, 2)


def run(capital=CAPITAL_USD, only_buys=True, save=True):
    print("=" * 64)
    print(" ANALISIS DE MERCADO - CARTERA DE AGENTES (eToro)")
    print(f" Fecha: {datetime.now():%Y-%m-%d %H:%M}  |  Capital base: ${capital:,.0f}")
    print("=" * 64)
    print(f"{'ACTIVO':14}{'PRECIO':>9}{'>SMA200':>9}{'MOM6M':>8}{'SCORE':>7}  ACCION")
    print("-" * 64)

    results, proposed = [], []
    for cand in CANDIDATES:
        a = analyze_one(cand)
        if not a.get("ok"):
            print(f"{cand['name'][:13]:14}{'  s/datos':>33}   ({a.get('error','?')})")
            results.append({"candidate": cand, "analysis": a})
            time.sleep(0.2)
            continue

        flag = "Si" if a["above_sma200"] else "no"
        mom = f"{a['momentum_6m_pct']:+.0f}%" if a["momentum_6m_pct"] is not None else "  -"
        print(f"{cand['name'][:13]:14}{a['price']:>9}{flag:>9}{mom:>8}"
              f"{a['score']:>7}  {a['action']}")
        results.append({"candidate": cand, "analysis": a})

        if a["action"] == "BUY" or not only_buys:
            amount = size_order(cand, capital)
            proposed.append({
                "symbol": cand["symbol"], "name": cand["name"],
                "etoro": cand["etoro"], "tier": cand["tier"],
                "instrument_id": None,           # <- se resuelve via API al ejecutar
                "is_buy": True, "amount_usd": amount, "leverage": 1,
                "stop_loss_rate": a["stop_loss"], "take_profit_rate": None,
                "ref_price": a["price"], "score": a["score"],
                "action": a["action"], "approved": False,   # <- TU lo pones en true
                "thesis": cand["thesis"],
            })

    print("-" * 64)
    invest = sum(p["amount_usd"] for p in proposed)
    print(f"Propuestas de COMPRA: {len(proposed)}  |  Inversion sugerida: ${invest:,.0f}"
          f"  ({invest/capital*100:.0f}% del capital)")
    print("Nota: senales tecnicas, NO asesoramiento financiero. Revisa antes de operar.")

    if save:
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "capital_usd": capital, "orders": proposed,
        }
        with open(PROPOSED_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\nOrdenes propuestas guardadas en: {PROPOSED_FILE}")
        print('Para aprobar una orden, pon  "approved": true  en ella y guarda.')
    return results, proposed


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Analisis de mercado y propuesta de ordenes")
    ap.add_argument("--capital", type=float, default=CAPITAL_USD, help="Capital base en USD")
    ap.add_argument("--all", action="store_true", help="Incluye tambien WATCH/AVOID en el JSON")
    args = ap.parse_args()
    run(capital=args.capital, only_buys=not args.all)
