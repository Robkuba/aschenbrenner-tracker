#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
 REBALANCE  -  Vigila la desviacion de tu cartera vs el plan
=====================================================================
Compara tu cartera REAL en eToro (via API) con los pesos objetivo del
plan (orders_kubabot_200.json) y avisa cuando algo se ha desviado
demasiado. NO opera por su cuenta:

  - Genera un informe legible.
  - Escribe  rebalance_orders.json  con las COMPRAS de ajuste sugeridas
    (approved:false) para que las revises y las ejecutes con trade_executor.
  - Las VENTAS/recortes se listan como accion manual (mas conservador):
    reducir una posicion es una decision que conviene que tomes tu.

Umbral de aviso:
  Una posicion se marca si su peso real se desvia del objetivo mas de
  REBALANCE_THRESHOLD_PCT puntos porcentuales (por defecto 5).

Uso:
  python rebalance.py                 -> informe + propuesta de ajustes
  python rebalance.py --wa            -> ademas avisa por WhatsApp
=====================================================================
"""

import os
import json
import sys
from datetime import datetime

from etoro_client import EtoroClient, EtoroError

PLAN_FILE = os.environ.get("PROPOSED_FILE", "orders_kubabot_200.json")
OUT_FILE = os.environ.get("REBALANCE_FILE", "rebalance_orders.json")
THRESHOLD = float(os.environ.get("REBALANCE_THRESHOLD_PCT", "5"))  # puntos %
MIN_TRADE = float(os.environ.get("ETORO_MIN_ORDER_USD", "10"))


# ----------------------------- PLAN ----------------------------------
def load_targets(plan_file):
    """ticker(upper) -> {name, target_pct} a partir del plan aprobado."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = json.load(f)
    orders = plan.get("orders", [])
    total = sum(o.get("amount_usd", 0) for o in orders) or 1.0
    targets = {}
    for o in orders:
        tk = (o.get("etoro") or "").upper()
        targets[tk] = {
            "name": o.get("name", tk),
            "target_pct": o.get("amount_usd", 0) / total * 100.0,
            "etoro": tk, "symbol": o.get("symbol"),
            "stop_loss_pct": o.get("stop_loss_pct"),
            "take_profit_pct": o.get("take_profit_pct"),
        }
    return targets


# -------------------------- CARTERA REAL -----------------------------
def _id_to_ticker(client):
    """Mapa instrument_id -> ticker(upper) consultando el universo del API."""
    out = {}
    try:
        data = client.get_instruments()
    except EtoroError as e:
        print(f"[aviso] No se pudo listar instrumentos: {e}")
        return out
    items = data.get("instruments", data if isinstance(data, list) else [])
    for it in items:
        iid = it.get("instrumentId") or it.get("InstrumentID") or it.get("id")
        sym = (it.get("symbolFull") or it.get("symbol") or it.get("ticker") or "").upper()
        if iid and sym:
            out[str(iid)] = sym
    return out


def read_current(client):
    """
    Lee la cartera real. Devuelve:
      ticker(upper) -> valor_usd   y   valor total de la cartera.
    Soporta varias formas del JSON de eToro (positions/value).
    """
    pf = client.get_portfolio()
    positions = (pf.get("positions") or pf.get("Positions")
                 or pf.get("openPositions") or [])
    id2tk = _id_to_ticker(client)

    by_ticker, total = {}, 0.0
    for p in positions:
        iid = p.get("instrumentId") or p.get("InstrumentID") or p.get("instrumentID")
        val = (p.get("value") or p.get("Value") or p.get("netProfit", 0)
               or p.get("investment") or p.get("Amount") or 0)
        try:
            val = float(val)
        except (TypeError, ValueError):
            val = 0.0
        tk = id2tk.get(str(iid), str(iid))
        by_ticker[tk] = by_ticker.get(tk, 0.0) + val
        total += val

    # Liquidez disponible (si el API la expone)
    cash = float(pf.get("availableAmount") or pf.get("cash") or 0) or 0.0
    return by_ticker, total, cash


# --------------------------- ANALISIS --------------------------------
def analyze(targets, current, total_value):
    """Calcula desviaciones y acciones sugeridas."""
    rows, base = [], (total_value or 1.0)
    tickers = set(targets) | set(current)
    for tk in sorted(tickers):
        t = targets.get(tk)
        cur_val = current.get(tk, 0.0)
        cur_pct = cur_val / base * 100.0
        tgt_pct = t["target_pct"] if t else 0.0
        drift = cur_pct - tgt_pct
        usd_delta = (tgt_pct - cur_pct) / 100.0 * base  # + = comprar, - = vender
        action = "OK"
        if abs(drift) >= THRESHOLD:
            action = "VENDER" if drift > 0 else "COMPRAR"
        if t is None:
            action = "FUERA-DE-PLAN"
        rows.append({
            "ticker": tk, "name": (t or {}).get("name", tk),
            "cur_pct": round(cur_pct, 1), "tgt_pct": round(tgt_pct, 1),
            "drift": round(drift, 1), "usd_delta": round(usd_delta, 2),
            "action": action, "target": t,
        })
    rows.sort(key=lambda r: -abs(r["drift"]))
    return rows


def build_rebalance_orders(rows):
    """Solo las COMPRAS de ajuste (>= minimo) como ordenes ejecutables."""
    orders = []
    for r in rows:
        if r["action"] == "COMPRAR" and r["usd_delta"] >= MIN_TRADE and r["target"]:
            t = r["target"]
            orders.append({
                "symbol": t.get("symbol"), "name": r["name"], "etoro": r["ticker"],
                "instrument_id": None, "is_buy": True,
                "amount_usd": round(r["usd_delta"], 2), "leverage": 1,
                "stop_loss_pct": t.get("stop_loss_pct"),
                "take_profit_pct": t.get("take_profit_pct"),
                "stop_loss_rate": None, "take_profit_rate": None,
                "approved": False, "reason": f"ajuste +{r['usd_delta']:.0f}$ (drift {r['drift']:+.1f}pp)",
            })
    return orders


# ----------------------------- MAIN ----------------------------------
def main():
    import argparse
    ap = argparse.ArgumentParser(description="Rebalanceo: cartera real vs plan")
    ap.add_argument("--wa", action="store_true", help="Avisar por WhatsApp del resumen")
    args = ap.parse_args()

    if not os.path.exists(PLAN_FILE):
        sys.exit(f"No existe el plan {PLAN_FILE}.")
    targets = load_targets(PLAN_FILE)

    client = EtoroClient()
    print(f"Entorno: {client.env.upper()}  |  Umbral de aviso: +-{THRESHOLD:.0f}pp\n")
    try:
        current, total, cash = read_current(client)
    except EtoroError as e:
        sys.exit(f"No se pudo leer la cartera (¿credenciales?): {e}")

    rows = analyze(targets, current, total)

    print("=" * 66)
    print(f" REBALANCEO - {datetime.now():%Y-%m-%d %H:%M}  |  Cartera: ${total:,.2f}"
          f"  |  Liquidez: ${cash:,.2f}")
    print("=" * 66)
    print(f"{'ACTIVO':14}{'REAL%':>8}{'OBJ%':>8}{'DRIFT':>8}{'AJUSTE$':>10}  ACCION")
    print("-" * 66)
    flagged = 0
    for r in rows:
        if r["action"] in ("OK",):
            continue
        flagged += 1
        print(f"{r['name'][:13]:14}{r['cur_pct']:>8}{r['tgt_pct']:>8}"
              f"{r['drift']:>+8}{r['usd_delta']:>+10.0f}  {r['action']}")
    if flagged == 0:
        print("Todo dentro de rango. No hace falta rebalancear. 👍")
    print("-" * 66)

    rb_orders = build_rebalance_orders(rows)
    payload = {"generated_at": datetime.now().isoformat(timespec="seconds"),
               "portfolio_value": total, "cash": cash, "orders": rb_orders}
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    trims = [r for r in rows if r["action"] == "VENDER"]
    if rb_orders:
        print(f"\nCompras de ajuste propuestas: {len(rb_orders)} -> {OUT_FILE}")
        print('Aprueba ("approved": true) y ejecuta:')
        print(f'  PROPOSED_FILE={OUT_FILE} python3 trade_executor.py')
    if trims:
        print(f"\nRecortes sugeridos (hazlos a mano en eToro, mas conservador):")
        for r in trims:
            print(f"  - {r['name']}: reduce ~${abs(r['usd_delta']):.0f} (sobrepeso {r['drift']:+.1f}pp)")

    if args.wa:
        try:
            from aschenbrenner_tracker import send_whatsapp
            lines = [f"📊 Rebalanceo Kubabot (${total:,.0f})"]
            if flagged == 0:
                lines.append("Todo en rango, sin cambios.")
            else:
                for r in rows:
                    if r["action"] in ("COMPRAR", "VENDER"):
                        lines.append(f"{r['action']} {r['name']} {r['usd_delta']:+.0f}$ ({r['drift']:+.1f}pp)")
            send_whatsapp("\n".join(lines))
        except Exception as e:
            print(f"[WhatsApp] No se pudo enviar: {e}")


if __name__ == "__main__":
    main()
