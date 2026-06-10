#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera contenido LISTO PARA PUBLICAR a partir del ultimo 13F del fondo:
  - Un hilo para X/Twitter (ES)
  - Un guion de carrusel para Instagram (ES)
  - Un hook corto en EN (para reels/captions)

Compara los dos ultimos 13F y arma el contenido sobre lo que abrio/cerro.
Es contenido INFORMATIVO/educativo (datos publicos de la SEC), no es
recomendacion de inversion.

Uso:  python social_content.py
"""

import aschenbrenner_tracker as t


def diff_two(prev_holdings, cur_holdings):
    """Devuelve (abiertas, cerradas) comparando dos carteras."""
    opened = [h for k, h in cur_holdings.items() if k not in prev_holdings]
    closed = [h for k, h in prev_holdings.items() if k not in cur_holdings]
    opened.sort(key=lambda h: -h["value"])
    closed.sort(key=lambda h: -h["value"])
    return opened, closed


def top_by_type(holdings, put_call, n=5):
    items = [h for h in holdings.values() if h["put_call"] == put_call]
    items.sort(key=lambda h: -h["value"])
    return items[:n]


def build_x_thread(fund_name, period, cur, opened, closed):
    q = t.quarter_label(period)
    puts = top_by_type(cur, "Put", 6)
    longs = top_by_type(cur, "", 5)
    total = sum(h["value"] for h in cur.values())
    put_total = sum(h["value"] for h in cur.values() if h["put_call"] == "Put")

    lines = []
    lines.append(
        f"🧵 Leopold Aschenbrenner acaba de revelar su cartera ({q}).\n\n"
        f"El ex-OpenAI de 24 años mueve {t.fmt_money(total)}… y "
        f"{t.fmt_money(put_total)} de eso son APUESTAS BAJISTAS contra los chips de IA.\n\n"
        f"Esto es lo que compró y vendió 👇"
    )
    lines.append(
        "2/ La jugada que dio que hablar: un muro de PUTS contra el sector semiconductores.\n\n"
        + "\n".join(f"🔴 {h['name'].title()} — {t.fmt_money(h['value'])}" for h in puts)
    )
    lines.append(
        "3/ Pero no es bajista en todo. Sus mayores apuestas ALCISTAS (acciones):\n\n"
        + "\n".join(f"🟢 {h['name'].title()} — {t.fmt_money(h['value'])}" for h in longs)
    )
    if opened:
        lines.append(
            f"4/ NUEVO este trimestre (abrió {len(opened)} posiciones). Las más grandes:\n\n"
            + "\n".join(f"• {h['name'].title()} [{_kind(h['put_call'])}] {t.fmt_money(h['value'])}"
                        for h in opened[:5])
        )
    if closed:
        lines.append(
            f"5/ CERRÓ {len(closed)} posiciones. Salió de:\n\n"
            + "\n".join(f"• {h['name'].title()}" for h in closed[:6])
        )
    lines.append(
        "6/ Recuerda: el 13F es trimestral y se publica con ~45 días de retraso. "
        "Es una foto, no el día exacto de cada operación.\n\n"
        "¿Tiene razón con su tesis de IA? Te leo 👇\n\n"
        "Sígueme para más desgloses de las grandes carteras. @robkubanoinvest"
    )
    return "\n\n———\n\n".join(lines)


def build_ig_carousel(fund_name, period, cur, opened, closed):
    q = t.quarter_label(period)
    puts = top_by_type(cur, "Put", 4)
    longs = top_by_type(cur, "", 4)
    total = sum(h["value"] for h in cur.values())
    put_total = sum(h["value"] for h in cur.values() if h["put_call"] == "Put")

    slides = []
    slides.append(("PORTADA",
        f"El fondo de IA de Aschenbrenner\nmueve {t.fmt_money(total)}\n\n"
        f"y apuesta {t.fmt_money(put_total)} EN CONTRA\nde los chips. Te lo explico 👉"))
    slides.append(("SLIDE 2 — Quién es",
        "Leopold Aschenbrenner, 24 años, ex-OpenAI.\n"
        "Fundó 'Situational Awareness LP', un fondo enfocado\n"
        "en la infraestructura de la IA. Cartera: " + t.fmt_money(total) + "."))
    slides.append(("SLIDE 3 — La apuesta bajista",
        "Su mayor jugada: PUTS contra los semiconductores.\n\n"
        + "\n".join(f"🔴 {h['name'].title()} · {t.fmt_money(h['value'])}" for h in puts)))
    slides.append(("SLIDE 4 — Lo que SÍ le gusta",
        "Sus mayores posiciones alcistas (acciones):\n\n"
        + "\n".join(f"🟢 {h['name'].title()} · {t.fmt_money(h['value'])}" for h in longs)))
    if opened:
        slides.append(("SLIDE 5 — Movimientos nuevos",
            f"Este trimestre abrió {len(opened)} posiciones nuevas.\n"
            f"Cerró {len(closed)}.\n\n"
            "Las grandes aperturas:\n"
            + "\n".join(f"• {h['name'].title()} ({_kind(h['put_call'])})" for h in opened[:4])))
    slides.append(("SLIDE FINAL — CTA",
        "Dato clave: el 13F es trimestral y con retraso.\n"
        "Es una foto, no el minuto a minuto.\n\n"
        "Guarda este post 📌 y sígueme para más.\n@robkubanoinvest"))

    out = []
    for titulo, texto in slides:
        out.append(f"[{titulo}]\n{texto}")
    return "\n\n────────────\n\n".join(out)


def build_en_hook(fund_name, period, cur):
    put_total = sum(h["value"] for h in cur.values() if h["put_call"] == "Put")
    total = sum(h["value"] for h in cur.values())
    return (f"A 24-year-old ex-OpenAI researcher is running a {t.fmt_money(total)} fund — "
            f"and just placed {t.fmt_money(put_total)} in bets AGAINST AI chip stocks. "
            f"Here's the full breakdown of what Leopold Aschenbrenner bought and sold 🧵")


def _kind(pc):
    return {"": "acción", "Call": "call", "Put": "put"}.get(pc, pc)


def main():
    print("Descargando los dos últimos 13F...")
    fund_name, filings = t.get_13f_filings()
    if len(filings) < 2:
        print("No hay suficientes 13F para comparar.")
        return

    cur_fil = filings[-1]
    prev_fil = filings[-2]
    cur = t.fetch_holdings(cur_fil["accession"])
    prev = t.fetch_holdings(prev_fil["accession"])
    opened, closed = diff_two(prev, cur)
    period = cur_fil["period"]

    sep = "\n" + "=" * 64 + "\n"
    print(sep + "HILO PARA X / TWITTER (ES)" + sep)
    print(build_x_thread(fund_name, period, cur, opened, closed))
    print(sep + "CARRUSEL PARA INSTAGRAM (ES)" + sep)
    print(build_ig_carousel(fund_name, period, cur, opened, closed))
    print(sep + "HOOK EN INGLÉS (reels / captions)" + sep)
    print(build_en_hook(fund_name, period, cur))

    # Guardar tambien en archivo
    with open("contenido_social.txt", "w", encoding="utf-8") as f:
        f.write("HILO X (ES)\n\n" + build_x_thread(fund_name, period, cur, opened, closed))
        f.write("\n\n\nCARRUSEL IG (ES)\n\n" + build_ig_carousel(fund_name, period, cur, opened, closed))
        f.write("\n\n\nHOOK EN\n\n" + build_en_hook(fund_name, period, cur))
    print("\n\n(Guardado también en contenido_social.txt)")


if __name__ == "__main__":
    main()
