#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostico: comprueba que los tickers de tus ordenes existen en eToro y
muestra su instrumentID. No opera nada, solo lee.
Uso:  python diag_instruments.py
"""
import json
from etoro_client import EtoroClient

PLAN_FILE = "orders_kubabot_200.json"

c = EtoroClient()
print(f"Entorno: {c.env}\n")
data = c.get_instruments()
items = (data.get("instrumentDisplayDatas") or data.get("instruments")
         or (data if isinstance(data, list) else []))
print(f"Instrumentos recibidos: {len(items)}\n")

# Indexar por ticker (symbolFull) -> instrumentID
idx = {}
for it in items:
    sym = (it.get("symbolFull") or "").upper()
    iid = it.get("instrumentID") or it.get("instrumentId") or it.get("id")
    if sym and iid:
        idx[sym] = iid

# Comprobar los tickers del plan
with open(PLAN_FILE, encoding="utf-8") as f:
    orders = json.load(f)["orders"]

print("--- Comprobacion de tus 12 ordenes ---")
faltan = []
for o in orders:
    tk = (o.get("etoro") or "").upper()
    iid = idx.get(tk)
    estado = f"OK  id={iid}" if iid else "NO ENCONTRADO"
    print(f"  {o['name'][:16]:16} {tk:6} -> {estado}")
    if not iid:
        faltan.append(o)

if faltan:
    print("\n--- Buscando parecidos para los que faltan ---")
    for o in faltan:
        base = (o.get("etoro") or "").upper()
        cand = [s for s in idx if base in s or s in base][:8]
        print(f"  {o['name']} ({base}): posibles -> {cand}")
else:
    print("\n¡Todos encontrados! El robot ya puede operarlos. ✅")
    print("(El precio en vivo lo saca el ejecutor de Yahoo, no de eToro.)")
