#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
 TRADE CANDIDATES  -  Universo de ideas para la cartera de agentes
=====================================================================
Lista CURADA y editable de activos candidatos. NO es una orden: es la
materia prima que market_analysis.py puntua y de la que tu eliges que
operar.

Cada candidato:
  symbol      : ticker (formato Stooq/USA para cotizar: p.ej. "nvda.us")
  name        : nombre legible
  etoro       : nombre/busqueda del activo en eToro (el id se resuelve via API)
  tier        : "core" (nucleo L/P), "growth" (crecimiento), "gem" (mas riesgo)
  thesis      : por que esta aqui (1 linea)
  target_pct  : peso objetivo sugerido en la cartera (%)
  max_pct     : tope duro de peso (%) para control de riesgo

IMPORTANTE: esto NO es asesoramiento financiero. Son ideas para revisar.
Ajusta libremente la lista; el motor se adapta a lo que pongas aqui.
=====================================================================
"""

CANDIDATES = [
    # ---------------------- NUCLEO (core) ----------------------------
    # Diversificacion barata y base de la cartera a largo plazo.
    {"symbol": "spy.us",  "name": "S&P 500 (ETF)",          "etoro": "SPY",
     "tier": "core", "target_pct": 18, "max_pct": 25,
     "thesis": "Base diversificada del mercado USA; el ancla de largo plazo."},
    {"symbol": "qqq.us",  "name": "Nasdaq 100 (ETF)",       "etoro": "QQQ",
     "tier": "core", "target_pct": 10, "max_pct": 18,
     "thesis": "Sesgo tecnologico/calidad; motor de crecimiento secular."},

    # --------------------- CRECIMIENTO (growth) ----------------------
    # Lideres de calidad con vientos de cola estructurales (IA, cloud).
    {"symbol": "nvda.us", "name": "NVIDIA",                 "etoro": "NVDA",
     "tier": "growth", "target_pct": 9, "max_pct": 14,
     "thesis": "Lider en computo de IA; foso por CUDA y ecosistema. Volatil."},
    {"symbol": "msft.us", "name": "Microsoft",              "etoro": "MSFT",
     "tier": "growth", "target_pct": 8, "max_pct": 12,
     "thesis": "Cloud (Azure) + IA + flujo de caja muy estable. Calidad."},
    {"symbol": "googl.us","name": "Alphabet",               "etoro": "GOOGL",
     "tier": "growth", "target_pct": 7, "max_pct": 11,
     "thesis": "Busqueda, cloud, IA (Gemini) y opcionalidad; valoracion razonable."},
    {"symbol": "amzn.us", "name": "Amazon",                 "etoro": "AMZN",
     "tier": "growth", "target_pct": 6, "max_pct": 10,
     "thesis": "AWS + retail + publicidad; margenes en expansion."},
    {"symbol": "tsm.us",  "name": "TSMC",                   "etoro": "TSM",
     "tier": "growth", "target_pct": 6, "max_pct": 10,
     "thesis": "Fundicion clave de chips de IA; cuello de botella mundial."},
    {"symbol": "avgo.us", "name": "Broadcom",               "etoro": "AVGO",
     "tier": "growth", "target_pct": 5, "max_pct": 9,
     "thesis": "ASICs de IA + software de infraestructura; dividendo creciente."},

    # ------------------------- GEMAS (gem) ---------------------------
    # Mayor potencial y MAYOR riesgo/volatilidad. Pesos pequenos.
    {"symbol": "amd.us",  "name": "AMD",                    "etoro": "AMD",
     "tier": "gem", "target_pct": 4, "max_pct": 7,
     "thesis": "Segundo jugador en GPU/IA; turnaround con mucho recorrido y riesgo."},
    {"symbol": "asml.us", "name": "ASML",                   "etoro": "ASML",
     "tier": "gem", "target_pct": 4, "max_pct": 7,
     "thesis": "Monopolio de litografia EUV; imprescindible para chips avanzados."},
    {"symbol": "vrt.us",  "name": "Vertiv",                 "etoro": "VRT",
     "tier": "gem", "target_pct": 3, "max_pct": 6,
     "thesis": "Energia/refrigeracion para datacenters de IA; pico-y-pala del boom."},
    {"symbol": "nu.us",   "name": "Nubank",                 "etoro": "NU",
     "tier": "gem", "target_pct": 3, "max_pct": 6,
     "thesis": "Neobanco LatAm en fuerte crecimiento; banca digital emergente."},
]


def by_tier():
    """Agrupa los candidatos por categoria de riesgo."""
    out = {}
    for c in CANDIDATES:
        out.setdefault(c["tier"], []).append(c)
    return out


def total_target_pct():
    return sum(c["target_pct"] for c in CANDIDATES)


if __name__ == "__main__":
    print(f"{len(CANDIDATES)} candidatos | suma de pesos objetivo: {total_target_pct()}%")
    for tier, items in by_tier().items():
        print(f"\n[{tier.upper()}]")
        for c in items:
            print(f"  {c['name']:14} {c['target_pct']:>3}%  - {c['thesis']}")
