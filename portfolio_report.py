#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
 PORTFOLIO REPORT  -  Resumen semanal de tu cartera de eToro
=====================================================================
Lee tu cartera real (via API, SOLO LECTURA) y te manda por WhatsApp un
resumen: valor total, liquidez, P&L global y P&L por posicion. Se manda
SIEMPRE, haya o no rebalanceo pendiente.

Uso:
  python portfolio_report.py          -> imprime el informe por consola
  python portfolio_report.py --wa     -> ademas lo envia por WhatsApp
=====================================================================
"""

import sys
import argparse
from datetime import datetime

from etoro_client import EtoroClient, EtoroError


def _num(d, *keys, default=0.0):
    """Primer valor numerico encontrado entre varias claves posibles."""
    for k in keys:
        v = d.get(k)
        try:
            if v is not None:
                return float(v)
        except (TypeError, ValueError):
            continue
    return default


def _id_to_ticker(client):
    out = {}
    try:
        data = client.get_instruments()
    except EtoroError:
        return out
    items = data.get("instruments", data if isinstance(data, list) else [])
    for it in items:
        iid = it.get("instrumentId") or it.get("InstrumentID") or it.get("id")
        sym = (it.get("symbolFull") or it.get("symbol") or it.get("ticker") or "").upper()
        if iid and sym:
            out[str(iid)] = sym
    return out


def collect(client):
    """Devuelve (resumen_dict, lista_posiciones)."""
    pf = client.get_portfolio()
    positions = (pf.get("positions") or pf.get("Positions")
                 or pf.get("openPositions") or [])
    id2tk = _id_to_ticker(client)

    rows, total_val, total_pl = [], 0.0, 0.0
    for p in positions:
        iid = p.get("instrumentId") or p.get("InstrumentID") or p.get("instrumentID")
        tk = id2tk.get(str(iid), str(iid))
        val = _num(p, "value", "Value", "investment", "Amount")
        pl = _num(p, "netProfit", "NetProfit", "profit", "openPl", "unrealizedPl")
        pl_pct = _num(p, "netProfitPct", "profitPct", "plPct", default=None) if (
            "netProfitPct" in p or "profitPct" in p or "plPct" in p) else None
        if pl_pct is None and val:
            base = val - pl
            pl_pct = (pl / base * 100.0) if base else 0.0
        rows.append({"ticker": tk, "value": val, "pl": pl, "pl_pct": pl_pct or 0.0})
        total_val += val
        total_pl += pl

    cash = _num(pf, "availableAmount", "cash", "credit")
    equity = total_val + cash
    base_total = total_val - total_pl
    total_pl_pct = (total_pl / base_total * 100.0) if base_total else 0.0
    rows.sort(key=lambda r: -r["pl_pct"])
    summary = {"positions_value": total_val, "cash": cash, "equity": equity,
               "pl": total_pl, "pl_pct": total_pl_pct, "n": len(rows)}
    return summary, rows


def render_console(summary, rows):
    print("=" * 60)
    print(f" INFORME DE CARTERA - {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 60)
    print(f"Patrimonio (equity): ${summary['equity']:,.2f}")
    print(f"  Posiciones:        ${summary['positions_value']:,.2f}")
    print(f"  Liquidez:          ${summary['cash']:,.2f}")
    print(f"P&L abierto:         ${summary['pl']:+,.2f}  ({summary['pl_pct']:+.1f}%)")
    print(f"Posiciones abiertas: {summary['n']}")
    print("-" * 60)
    for r in rows:
        print(f"  {r['ticker']:8} ${r['value']:>9,.2f}  "
              f"P&L {r['pl']:>+8,.2f} ({r['pl_pct']:>+5.1f}%)")
    print("-" * 60)
    print("Solo lectura. No es asesoramiento financiero.")


def render_whatsapp(summary, rows):
    sign = "🟢" if summary["pl"] >= 0 else "🔴"
    lines = [f"{sign} Informe Kubabot — {datetime.now():%d/%m}",
             f"Patrimonio: ${summary['equity']:,.0f}  (liq. ${summary['cash']:,.0f})",
             f"P&L abierto: ${summary['pl']:+,.0f} ({summary['pl_pct']:+.1f}%)",
             f"Posiciones: {summary['n']}", ""]
    top = rows[:3]
    bottom = [r for r in rows[-3:] if r not in top]
    if top:
        lines.append("Mejores:")
        for r in top:
            lines.append(f"  {r['ticker']} {r['pl_pct']:+.1f}%")
    if bottom:
        lines.append("Peores:")
        for r in reversed(bottom):
            lines.append(f"  {r['ticker']} {r['pl_pct']:+.1f}%")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Informe semanal de cartera eToro")
    ap.add_argument("--wa", action="store_true", help="Enviar por WhatsApp")
    args = ap.parse_args()

    client = EtoroClient()
    try:
        summary, rows = collect(client)
    except EtoroError as e:
        sys.exit(f"No se pudo leer la cartera (¿credenciales?): {e}")

    render_console(summary, rows)

    if args.wa:
        try:
            from aschenbrenner_tracker import send_whatsapp
            send_whatsapp(render_whatsapp(summary, rows))
        except Exception as e:
            print(f"[WhatsApp] No se pudo enviar: {e}")


if __name__ == "__main__":
    main()
