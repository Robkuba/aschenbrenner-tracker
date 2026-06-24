#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mini-diagnostico de fuentes de precio (Yahoo y Stooq) para SPY."""
import json
import urllib.request


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "ignore")


print(">>> YAHOO (SPY):")
try:
    d = json.loads(get("https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=1d&range=1d"))
    print("   precio =", d["chart"]["result"][0]["meta"]["regularMarketPrice"])
except Exception as e:
    print("   ERROR:", e)

print(">>> STOOQ (spy.us):")
try:
    print("   respuesta:", get("https://stooq.com/q/l/?s=spy.us&f=sd2t2ohlcv&h&e=csv").strip()[:200])
except Exception as e:
    print("   ERROR:", e)
