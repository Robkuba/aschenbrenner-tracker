#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
 TRADE EXECUTOR  -  Ejecuta SOLO las ordenes que tu apruebas
=====================================================================
Flujo seguro de 3 pasos:

  1) python market_analysis.py            -> genera proposed_orders.json
  2) Revisas el fichero y pones  "approved": true  en lo que SI quieras
  3) python trade_executor.py             -> ejecuta solo lo aprobado

Salvaguardas (a proposito):
  - DRY_RUN por defecto: no manda nada hasta poner ETORO_DRY_RUN=0.
  - Entorno "demo" por defecto: practica con dinero virtual primero.
  - Solo procesa ordenes con  approved == true.
  - Tope por orden  ETORO_MAX_ORDER_USD  (lo aplica el propio cliente).
  - Pide confirmacion final salvo que pases  --yes.
  - Registra todo en  executed_orders.log  (auditoria).

Resolucion de instrumento:
  Cada orden trae "etoro" (ticker/busqueda). El ejecutor pregunta al API
  por su instrument_id real si no viene puesto. Si no lo encuentra, salta
  la orden y te avisa (nunca adivina un id).
=====================================================================
"""

import os
import json
import sys
from datetime import datetime

from etoro_client import EtoroClient, EtoroError

PROPOSED_FILE = os.environ.get("PROPOSED_FILE", "proposed_orders.json")
LOG_FILE = os.environ.get("EXEC_LOG", "executed_orders.log")


def load_proposed():
    if not os.path.exists(PROPOSED_FILE):
        sys.exit(f"No existe {PROPOSED_FILE}. Ejecuta antes:  python market_analysis.py")
    with open(PROPOSED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def log(line):
    stamp = datetime.now().isoformat(timespec="seconds")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{stamp}  {line}\n")
    print(line)


import io
import csv
import urllib.request

# Precio en vivo. Fuente 1: Yahoo Finance (usa el ticker, ej. SPY).
# Fuente 2 (reserva): Stooq (usa el simbolo, ej. spy.us).
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
STOOQ_QUOTE = "https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcv&h&e=csv"


def _http_text(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _yahoo_price(ticker):
    """Precio actual via Yahoo Finance, o None."""
    d = json.loads(_http_text(YAHOO_URL.format(sym=ticker)))
    res = (d.get("chart") or {}).get("result") or []
    if res:
        p = (res[0].get("meta") or {}).get("regularMarketPrice")
        return float(p) if p is not None else None
    return None


def _stooq_price(symbol):
    """Precio (Close) de un simbolo en Stooq, o None."""
    for row in csv.DictReader(io.StringIO(_http_text(STOOQ_QUOTE.format(sym=symbol)))):
        try:
            return float(row.get("Close") or row.get("close"))
        except (TypeError, ValueError):
            return None
    return None


def fetch_prices(orders):
    """Mapa simbolo(lower) -> precio en vivo. Prueba Yahoo y luego Stooq."""
    out, fails = {}, 0
    for o in orders:
        ssym = (o.get("symbol") or "")
        ticker = (o.get("etoro") or "").upper()
        price = None
        if ticker:
            try:
                price = _yahoo_price(ticker)
            except Exception:
                price = None
        if price is None and ssym:
            try:
                price = _stooq_price(ssym)
            except Exception:
                price = None
        if price is not None:
            out[ssym.lower()] = price
        else:
            fails += 1
    if not out:
        print(f"[aviso] No se pudieron leer precios (Yahoo/Stooq). Fallos: {fails}")
    return out


def _instrument_price(it):
    """Intenta sacar el precio actual de los metadatos (varios nombres posibles)."""
    for k in ("currentRate", "lastPrice", "price", "close", "Ask", "ask", "rate"):
        v = it.get(k)
        try:
            if v is not None:
                return float(v)
        except (TypeError, ValueError):
            continue
    return None


def _index_instruments(client):
    """Mapa ticker(upper) -> {id, price} a partir del universo del API."""
    idx = {}
    try:
        data = client.get_instruments()
    except EtoroError as e:
        print(f"[aviso] No se pudo listar instrumentos: {e}")
        return idx
    items = (data.get("instrumentDisplayDatas") or data.get("instruments")
             or (data if isinstance(data, list) else []))
    for it in items:
        sym = (it.get("symbolFull") or it.get("symbol") or it.get("ticker") or "").upper()
        iid = (it.get("instrumentID") or it.get("instrumentId")
               or it.get("InstrumentID") or it.get("id"))
        if sym and iid:
            idx[sym] = {"id": iid, "price": _instrument_price(it)}
    return idx


def resolve_instrument(order, idx):
    """Devuelve (instrument_id, precio_actual) para una orden."""
    if order.get("instrument_id"):
        return order["instrument_id"], None
    info = idx.get((order.get("etoro") or "").upper())
    if info:
        return info["id"], info.get("price")
    return None, None


def compute_stop_loss(order, price):
    """
    Convierte stop_loss_pct (%) en precio absoluto (StopLossRate) usando el
    precio actual. Si ya viene stop_loss_rate fijo, se respeta tal cual.
    """
    if order.get("stop_loss_rate") is not None:
        return order["stop_loss_rate"]
    pct = order.get("stop_loss_pct")
    if not pct or not price:
        return None
    f = pct / 100.0
    # Largo: stop por debajo. Corto: stop por encima.
    rate = price * (1 - f) if order.get("is_buy", True) else price * (1 + f)
    return round(rate, 2)


def compute_take_profit(order, price):
    """Convierte take_profit_pct (%) en precio absoluto (TakeProfitRate)."""
    if order.get("take_profit_rate") is not None:
        return order["take_profit_rate"]
    pct = order.get("take_profit_pct")
    if not pct or not price:
        return None
    f = pct / 100.0
    # Largo: objetivo por encima. Corto: por debajo.
    rate = price * (1 + f) if order.get("is_buy", True) else price * (1 - f)
    return round(rate, 2)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Ejecuta ordenes aprobadas en eToro")
    ap.add_argument("--yes", action="store_true", help="No pedir confirmacion interactiva")
    args = ap.parse_args()

    data = load_proposed()
    orders = [o for o in data.get("orders", []) if o.get("approved") is True]

    client = EtoroClient()
    print(f"Entorno: {client.env.upper()}  |  DRY_RUN: {client.dry_run}")
    if not orders:
        sys.exit("No hay ordenes con \"approved\": true. Nada que ejecutar.")

    total = sum(o.get("amount_usd", 0) for o in orders)
    print(f"\nOrdenes aprobadas: {len(orders)}  |  Inversion total: ${total:,.2f}")
    for o in orders:
        print(f"  - {o['name']:14} {'COMPRA' if o['is_buy'] else 'VENTA':6} "
              f"${o['amount_usd']:>8.2f}  SL={o.get('stop_loss_rate')}  ({o['etoro']})")

    if not client.dry_run and not args.yes:
        resp = input("\n¿Ejecutar EN REAL estas ordenes? escribe 'SI' para continuar: ")
        if resp.strip().upper() not in ("SI", "SÍ", "YES"):
            sys.exit("Cancelado por el usuario.")

    idx = _index_instruments(client)

    # Resolver ids primero y pedir todos los precios (Stooq) de una vez.
    resolved = []
    for o in orders:
        iid, _ = resolve_instrument(o, idx)
        resolved.append((o, iid))
    prices = fetch_prices(orders)

    ok, skipped = 0, 0
    for o, iid in resolved:
        if not iid:
            log(f"SALTADA {o['name']} ({o['etoro']}): no se resolvio instrument_id")
            skipped += 1
            continue
        price = prices.get((o.get("symbol") or "").lower())
        sl_rate = compute_stop_loss(o, price)
        tp_rate = compute_take_profit(o, price)
        if (o.get("stop_loss_pct") or o.get("take_profit_pct")) and price is None:
            print(f"  [aviso] {o['name']}: sin precio en vivo, va SIN stop/take-profit "
                  f"(ponlos a mano en eToro).")
        else:
            if sl_rate is not None:
                print(f"  [SL] {o['name']}: stop-loss en {sl_rate} (-{o.get('stop_loss_pct')}%)")
            if tp_rate is not None:
                print(f"  [TP] {o['name']}: take-profit en {tp_rate} (+{o.get('take_profit_pct')}%)")
        try:
            res = client.open_position(
                instrument_id=iid, is_buy=o.get("is_buy", True),
                amount_usd=o["amount_usd"], leverage=o.get("leverage", 1),
                stop_loss_rate=sl_rate,
                take_profit_rate=tp_rate,
            )
            log(f"OK {o['name']} instr={iid} ${o['amount_usd']:.2f} -> {json.dumps(res, ensure_ascii=False)}")
            ok += 1
        except EtoroError as e:
            log(f"ERROR {o['name']} instr={iid}: {e}")
            skipped += 1

    print(f"\nResumen: {ok} enviadas, {skipped} saltadas. Log: {LOG_FILE}")
    if client.dry_run:
        print("(Era simulacion. Para operar de verdad: ETORO_DRY_RUN=0 y ETORO_ENV=real)")


if __name__ == "__main__":
    main()
