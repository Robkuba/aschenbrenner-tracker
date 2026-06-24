#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Explorador (solo LECTURA) para descubrir la estructura de las carteras de
agentes en la API de eToro y la ruta correcta para operar dentro de ellas.
No envia ninguna orden. Usa tu token actual.

Uso:  python diag_agent.py
"""
import json
from etoro_client import EtoroClient, EtoroError

c = EtoroClient()
print(f"Entorno: {c.env}\n")


def probe(method, path):
    print(f">>> {method} /{path}")
    try:
        data = c._request(method, path)
        s = json.dumps(data, ensure_ascii=False)
        print("   OK ✅ :", (s[:700] + ("..." if len(s) > 700 else "")))
    except EtoroError as e:
        print("   ", str(e)[:200])
    print()


# Candidatos de lectura para mapear las carteras de agentes
for p in [
    "agent-portfolios",
    f"agent-portfolios/{c.env}",
    "agent-portfolios/mine",
    "portfolios",
    f"trading/info/{c.env}/pnl",
    f"trading/info/{c.env}/credit",
]:
    probe("GET", p)
