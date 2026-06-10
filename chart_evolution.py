#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera un grafico de la evolucion de la cartera de Situational Awareness LP
trimestre a trimestre, separando exposicion ALCISTA (acciones + calls) y
BAJISTA (puts). Usa los datos reales de los 13F en la SEC.

Salida: aschenbrenner_evolucion.png
Uso:    python chart_evolution.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import aschenbrenner_tracker as t


def main():
    print("Descargando los 13F de la SEC...")
    fund_name, filings = t.get_13f_filings()

    quarters, longs, calls, puts = [], [], [], []
    for fil in filings:
        h = t.fetch_holdings(fil["accession"])
        lv = sum(d["value"] for d in h.values() if d["put_call"] == "")
        cv = sum(d["value"] for d in h.values() if d["put_call"] == "Call")
        pv = sum(d["value"] for d in h.values() if d["put_call"] == "Put")
        quarters.append(t.quarter_label(fil["period"]))
        longs.append(lv / 1e9)
        calls.append(cv / 1e9)
        puts.append(pv / 1e9)
        print(f"  {t.quarter_label(fil['period'])}: largos ${lv/1e9:.2f}B | "
              f"calls ${cv/1e9:.2f}B | puts ${pv/1e9:.2f}B")

    # ---------------------- ESTILO ----------------------
    plt.rcParams.update({
        "figure.facecolor": "#0d1117",
        "axes.facecolor": "#0d1117",
        "savefig.facecolor": "#0d1117",
        "text.color": "#e6edf3",
        "axes.labelcolor": "#e6edf3",
        "xtick.color": "#8b949e",
        "ytick.color": "#8b949e",
        "font.size": 12,
    })
    C_LONG = "#2ea043"   # verde  - acciones (alcista)
    C_CALL = "#58a6ff"   # azul   - calls (alcista)
    C_PUT = "#f85149"    # rojo   - puts (bajista)

    fig, ax = plt.subplots(figsize=(11, 6.5))
    x = range(len(quarters))

    b1 = ax.bar(x, longs, color=C_LONG, label="Acciones (largo)")
    b2 = ax.bar(x, calls, bottom=longs, color=C_CALL, label="Calls (alcista)")
    bottom2 = [a + b for a, b in zip(longs, calls)]
    b3 = ax.bar(x, puts, bottom=bottom2, color=C_PUT, label="Puts (bajista / cobertura)")

    # Totales encima de cada barra
    for i in x:
        total = longs[i] + calls[i] + puts[i]
        ax.text(i, total + 0.25, f"${total:.1f}B", ha="center",
                color="#e6edf3", fontweight="bold", fontsize=11)

    ax.set_xticks(list(x))
    ax.set_xticklabels(quarters, fontweight="bold")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:.0f}B"))
    ax.set_ylabel("Exposición (notional)")
    ax.set_title(f"{fund_name} — Evolución de la cartera (13F SEC)",
                 fontsize=15, fontweight="bold", pad=16, color="#e6edf3")
    ax.grid(axis="y", color="#21262d", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#30363d")
    ax.legend(loc="upper left", frameon=False, fontsize=11)

    fig.text(0.5, 0.01,
             "Fuente: Formularios 13F-HR (SEC EDGAR) · foto al cierre de cada trimestre · "
             "@robkubanoinvest",
             ha="center", color="#8b949e", fontsize=9)

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    out = "aschenbrenner_evolucion.png"
    plt.savefig(out, dpi=160)
    print(f"\nGrafico guardado: {out}")


if __name__ == "__main__":
    main()
