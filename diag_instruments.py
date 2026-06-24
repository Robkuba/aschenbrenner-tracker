#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostico: enseña como viene la lista de instrumentos del API de eToro,
para poder mapear bien ticker -> instrument_id. No opera nada, solo lee.
Uso:  python diag_instruments.py
"""
import json
from etoro_client import EtoroClient

c = EtoroClient()
print(f"Entorno: {c.env}\n")

print(">>> Probando get_instruments() SIN filtro...")
try:
    data = c.get_instruments()
except Exception as e:
    print("ERROR:", e)
    raise SystemExit

print("TIPO de la respuesta:", type(data).__name__)
if isinstance(data, dict):
    print("CLAVES de primer nivel:", list(data.keys()))

# Localizar la lista de instrumentos sea cual sea su nombre
items = None
if isinstance(data, list):
    items = data
elif isinstance(data, dict):
    for k in ("instruments", "data", "items", "result", "results", "instrumentDisplayDatas"):
        v = data.get(k)
        if isinstance(v, list):
            items = v
            print(f"Lista encontrada bajo la clave: '{k}'")
            break

if items:
    print(f"\nNumero de instrumentos: {len(items)}")
    print("\n--- PRIMER instrumento (sus campos) ---")
    print(json.dumps(items[0], indent=2, ensure_ascii=False)[:1800])
else:
    print("\nNo encontre una lista de instrumentos. Vuelco crudo (recortado):")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:1800])
