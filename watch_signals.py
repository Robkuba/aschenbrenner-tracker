#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
 WATCH SIGNALS  -  Vigia de momento alcista (24/7 via GitHub Actions)
=====================================================================
Vigila una watchlist (tu plan + ideas nuevas), calcula tendencia,
momentum y RSI con datos de Yahoo Finance, y dice que activos estan en
BUEN MOMENTO de compra. Pensado para correr en GitHub Actions y avisarte
por WhatsApp cuando sea buen momento para pasar a real.

Senales (transparentes):
  - Tendencia: precio por encima de SMA200 y SMA50 >= SMA200 (alcista)
  - RSI(14): fuerza sin sobrecompra (ideal 50-72)
  - Cercania a maximos de 52 semanas (proximidad a ruptura)

Veredicto por activo:
  ENTRAR  -> alcista + RSI 50-72 + cerca de maximos (buen momento)
  VIGILAR -> alcista pero sobrecomprado o alejado de maximos
  ESPERAR -> sin tendencia alcista (mejor no entrar aun)

AVISO: senales tecnicas, NO asesoramiento financiero.
=====================================================================
"""

import json
import argparse
import urllib.request
from datetime import datetime

# (ticker Yahoo, nombre, tier).  Las 12 del plan + ideas de investigacion.
WATCH = [
    ("SPY", "S&P 500", "core"), ("QQQ", "Nasdaq 100", "core"),
    ("NVDA", "NVIDIA", "growth"), ("MSFT", "Microsoft", "growth"),
    ("GOOGL", "Alphabet", "growth"), ("AMZN", "Amazon", "growth"),
    ("TSM", "TSMC", "growth"), ("AVGO", "Broadcom", "growth"),
    ("AMD", "AMD", "gem"), ("ASML", "ASML", "gem"),
    ("VRT", "Vertiv", "gem"), ("NU", "Nubank", "gem"),
    # --- ideas nuevas (investigacion jun-2026) ---
    ("META", "Meta Platforms", "growth"), ("NOW", "ServiceNow", "growth"),
    ("MU", "Micron", "gem"), ("NVO", "Novo Nordisk", "gem"),
]

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1y"
PLAN_SIZE = 12  # los primeros 12 son los del plan actual


def get_closes(sym):
    req = urllib.request.Request(YAHOO.format(sym=sym), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode("utf-8", "ignore"))
    res = (d.get("chart") or {}).get("result") or []
    if not res:
        return []
    q = (((res[0].get("indicators") or {}).get("quote") or [{}])[0]).get("close") or []
    return [c for c in q if c is not None]


def sma(v, n):
    return sum(v[-n:]) / n if len(v) >= n else None


def rsi(v, n=14):
    if len(v) < n + 1:
        return None
    gains = losses = 0.0
    for i in range(-n, 0):
        ch = v[i] - v[i - 1]
        gains += ch if ch > 0 else 0
        losses += -ch if ch < 0 else 0
    if losses == 0:
        return 100.0
    rs = (gains / n) / (losses / n)
    return 100 - 100 / (1 + rs)


def analyze(sym):
    v = get_closes(sym)
    if len(v) < 60:
        return None
    price = v[-1]
    s50 = sma(v, 50)
    s200 = sma(v, 200) or sma(v, min(len(v), 150))
    high = max(v[-252:]) if len(v) >= 252 else max(v)
    mom = (price / v[-126] - 1) * 100 if len(v) > 126 else None
    r = rsi(v)
    uptrend = bool(s200 and price > s200 and (not s50 or s50 >= s200))
    dist = (price / high - 1) * 100
    if uptrend and r is not None and 50 <= r <= 72 and dist >= -8:
        sig = "ENTRAR"
    elif uptrend:
        sig = "VIGILAR"
    else:
        sig = "ESPERAR"
    return {"price": round(price, 2), "rsi": round(r) if r is not None else None,
            "mom": round(mom) if mom is not None else None,
            "dist": round(dist, 1), "uptrend": uptrend, "sig": sig}


def run(send_wa=False):
    print("=" * 62)
    print(f" VIGIA DE MOMENTO ALCISTA - {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 62)
    print(f"{'ACTIVO':16}{'PRECIO':>9}{'RSI':>5}{'MOM6M':>7}{'vsMAX':>7}  SENAL")
    print("-" * 62)
    rows = []
    for i, (sym, name, tier) in enumerate(WATCH):
        try:
            a = analyze(sym)
        except Exception as e:
            print(f"{name[:15]:16}  s/datos ({str(e)[:25]})")
            continue
        if not a:
            print(f"{name[:15]:16}  s/datos")
            continue
        a.update({"sym": sym, "name": name, "tier": tier, "in_plan": i < PLAN_SIZE})
        rows.append(a)
        mom = f"{a['mom']:+d}%" if a['mom'] is not None else "  -"
        print(f"{name[:15]:16}{a['price']:>9}{a['rsi'] or 0:>5}{mom:>7}"
              f"{a['dist']:>6}%  {a['sig']}")
    print("-" * 62)

    entrar = [r for r in rows if r["sig"] == "ENTRAR"]
    plan_entrar = [r for r in entrar if r["in_plan"]]
    print(f"En BUEN MOMENTO (ENTRAR): {len(entrar)}  |  del plan: {len(plan_entrar)}/{PLAN_SIZE}")

    # Veredicto para pasar a real
    verdict = "ESPERAR un mejor momento general."
    if len(plan_entrar) >= max(1, PLAN_SIZE // 2):
        verdict = "BUEN MOMENTO: mayoria del plan en tendencia alcista."
    print("Veredicto:", verdict)
    print("Nota: senales tecnicas, NO asesoramiento financiero.")

    if send_wa:
        try:
            from aschenbrenner_tracker import send_whatsapp
            lines = [f"🟢 Vigia Kubabot — {datetime.now():%d/%m %H:%M}",
                     f"En buen momento (ENTRAR): {len(entrar)}", ""]
            for r in entrar[:10]:
                star = "⭐" if r["in_plan"] else "🔎"
                lines.append(f"{star} {r['name']} RSI{r['rsi']} ({r['mom']:+d}% 6m)")
            lines.append("")
            lines.append(verdict)
            send_whatsapp("\n".join(lines))
            print("[WhatsApp] aviso enviado.")
        except Exception as e:
            print(f"[WhatsApp] no se pudo enviar: {e}")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Vigia de momento alcista")
    ap.add_argument("--wa", action="store_true", help="Avisar por WhatsApp")
    args = ap.parse_args()
    run(send_wa=args.wa)
