#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera el CARRUSEL de Instagram como imagenes PNG (1080x1350) con tu
branding, a partir del ultimo 13F del fondo. Una imagen por slide.

Salida: slides/slide_1.png ... slide_N.png
Uso:    python carousel_images.py
"""

import os
from PIL import Image, ImageDraw, ImageFont

import aschenbrenner_tracker as t
import social_content as sc

# ----------------------------- MARCA ---------------------------------
HANDLE = "@robkubanoinvest"
BRAND = "ROBKUBANO"

W, H = 1080, 1350
MARGIN = 90

# Paleta (coherente con el grafico)
BG = "#0d1117"
CARD = "#161b22"
WHITE = "#e6edf3"
MUTED = "#8b949e"
GREEN = "#2ea043"
BLUE = "#58a6ff"
RED = "#f85149"
ACCENT = "#58a6ff"

FONT_DIR = "/usr/share/fonts/truetype/google-fonts"
def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

F_BOLD = "Poppins-Bold.ttf"
F_MED = "Poppins-Medium.ttf"
F_REG = "Poppins-Regular.ttf"
F_LIGHT = "Poppins-Light.ttf"


# --------------------------- UTILIDADES ------------------------------
def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def truncate(draw, text, fnt, max_w):
    if draw.textlength(text, font=fnt) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=fnt) > max_w:
        text = text[:-1]
    return text + "…"


def base_slide(index, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # Header: marca + handle
    d.text((MARGIN, 70), BRAND, font=font(F_BOLD, 30), fill=WHITE, anchor="la")
    d.text((MARGIN + 215, 73), HANDLE, font=font(F_REG, 26), fill=MUTED, anchor="la")
    # Barra de acento bajo el header
    d.rectangle([MARGIN, 120, MARGIN + 70, 126], fill=ACCENT)
    # Footer: indice + fuente
    d.text((MARGIN, H - 70), f"{index}/{total}", font=font(F_BOLD, 26), fill=ACCENT, anchor="lm")
    d.text((W - MARGIN, H - 70), "Fuente: SEC EDGAR · 13F", font=font(F_REG, 24),
           fill=MUTED, anchor="rm")
    return img, d


def bullet_row(d, y, color, name, value, max_name_w):
    # punto de color
    r = 11
    cx = MARGIN + 14
    d.ellipse([cx - r, y - r, cx + r, y + r], fill=color)
    name = truncate(d, name, font(F_MED, 38), max_name_w)
    d.text((MARGIN + 50, y), name, font=font(F_MED, 38), fill=WHITE, anchor="lm")
    if value:
        d.text((W - MARGIN, y), value, font=font(F_BOLD, 38), fill=color, anchor="rm")


# --------------------------- SLIDES ----------------------------------
def slide_cover(d, total, put_total, q):
    d.text((MARGIN, 300), "13F · " + q, font=font(F_MED, 34), fill=ACCENT, anchor="la")
    d.text((MARGIN, 360), t.fmt_money(put_total), font=font(F_BOLD, 200), fill=RED, anchor="la")
    for i, ln in enumerate(["EN PUTS CONTRA", "NVIDIA Y LOS", "CHIPS DE IA"]):
        d.text((MARGIN, 620 + i * 92), ln, font=font(F_BOLD, 78), fill=WHITE, anchor="la")
    d.text((MARGIN, 960), "La cartera del fondo de IA de", font=font(F_REG, 38), fill=MUTED, anchor="la")
    d.text((MARGIN, 1010), "Leopold Aschenbrenner", font=font(F_BOLD, 44), fill=WHITE, anchor="la")
    d.text((W - MARGIN - 55, 1150), "Desliza", font=font(F_MED, 40), fill=ACCENT, anchor="rm")
    ax = W - MARGIN - 38
    d.polygon([(ax, 1150 - 20), (ax, 1150 + 20), (ax + 34, 1150)], fill=ACCENT)


def slide_quien(d, total):
    d.text((MARGIN, 210), "¿Quién es?", font=font(F_BOLD, 70), fill=WHITE, anchor="la")
    body = ("Leopold Aschenbrenner, 24 años. Ex-investigador de OpenAI. "
            "Fundó Situational Awareness LP, un fondo centrado en la "
            "infraestructura de la inteligencia artificial.")
    y = 360
    for ln in wrap(d, body, font(F_REG, 42), W - 2 * MARGIN):
        d.text((MARGIN, y), ln, font=font(F_REG, 42), fill=WHITE, anchor="la")
        y += 60
    # chips de stats
    y += 50
    for label, val, col in [("Cartera total", t.fmt_money(total), ACCENT),
                            ("Enfoque", "IA · Semiconductores · Energía", GREEN)]:
        d.rounded_rectangle([MARGIN, y, W - MARGIN, y + 130], radius=22, fill=CARD)
        d.text((MARGIN + 40, y + 35), label, font=font(F_REG, 30), fill=MUTED, anchor="la")
        d.text((MARGIN + 40, y + 72), val, font=font(F_BOLD, 44), fill=col, anchor="la")
        y += 165


def slide_bullets(d, title, subtitle, rows, color):
    d.text((MARGIN, 210), title, font=font(F_BOLD, 66), fill=WHITE, anchor="la")
    d.text((MARGIN, 300), subtitle, font=font(F_REG, 36), fill=MUTED, anchor="la")
    y = 440
    max_name_w = W - 2 * MARGIN - 280
    for name, value in rows:
        bullet_row(d, y, color, name, value, max_name_w)
        y += 110


def slide_moves(d, opened, closed, top_open):
    d.text((MARGIN, 210), "Movimientos del", font=font(F_BOLD, 66), fill=WHITE, anchor="la")
    d.text((MARGIN, 285), "trimestre", font=font(F_BOLD, 66), fill=WHITE, anchor="la")
    # dos contadores
    bw = (W - 2 * MARGIN - 30) // 2
    for i, (label, n, col) in enumerate([("ABRIÓ", opened, GREEN), ("CERRÓ", closed, RED)]):
        x = MARGIN + i * (bw + 30)
        d.rounded_rectangle([x, 400, x + bw, 560], radius=22, fill=CARD)
        d.text((x + bw // 2, 455), str(n), font=font(F_BOLD, 70), fill=col, anchor="mm")
        d.text((x + bw // 2, 525), label + " POSICIONES", font=font(F_MED, 26), fill=MUTED, anchor="mm")
    d.text((MARGIN, 630), "Aperturas destacadas:", font=font(F_MED, 36), fill=WHITE, anchor="la")
    y = 730
    max_name_w = W - 2 * MARGIN - 280
    for name, value, col in top_open:
        bullet_row(d, y, col, name, value, max_name_w)
        y += 100


def slide_cta(d):
    d.text((MARGIN, 210), "Antes de copiar", font=font(F_BOLD, 66), fill=WHITE, anchor="la")
    d.text((MARGIN, 285), "nada…", font=font(F_BOLD, 66), fill=WHITE, anchor="la")
    note = ("El 13F es trimestral y se publica con hasta 45 días de retraso. "
            "Es una foto al cierre del trimestre, no el día exacto de cada "
            "operación. Esto es información, no una recomendación de inversión.")
    y = 420
    for ln in wrap(d, note, font(F_REG, 40), W - 2 * MARGIN):
        d.text((MARGIN, y), ln, font=font(F_REG, 40), fill=WHITE, anchor="la")
        y += 58
    y += 60
    d.rounded_rectangle([MARGIN, y, W - MARGIN, y + 200], radius=24, fill=CARD)
    d.text((W // 2, y + 60), "Guarda este post y sígueme", font=font(F_MED, 38), fill=WHITE, anchor="mm")
    d.text((W // 2, y + 130), HANDLE, font=font(F_BOLD, 54), fill=ACCENT, anchor="mm")


# ----------------------------- MAIN ----------------------------------
def main():
    print("Descargando datos del último 13F...")
    fund_name, filings = t.get_13f_filings()
    cur = t.fetch_holdings(filings[-1]["accession"])
    prev = t.fetch_holdings(filings[-2]["accession"]) if len(filings) > 1 else {}
    opened, closed = sc.diff_two(prev, cur)
    q = t.quarter_label(filings[-1]["period"])

    total = sum(h["value"] for h in cur.values())
    put_total = sum(h["value"] for h in cur.values() if h["put_call"] == "Put")
    puts = [(h["name"].title(), t.fmt_money(h["value"])) for h in sc.top_by_type(cur, "Put", 5)]
    longs = [(h["name"].title(), t.fmt_money(h["value"])) for h in sc.top_by_type(cur, "", 5)]
    top_open = [(h["name"].title(), t.fmt_money(h["value"]),
                 RED if h["put_call"] == "Put" else (BLUE if h["put_call"] == "Call" else GREEN))
                for h in opened[:4]]

    os.makedirs("slides", exist_ok=True)
    builders = [
        ("cover", lambda d: slide_cover(d, total, put_total, q)),
        ("quien", lambda d: slide_quien(d, total)),
        ("puts", lambda d: slide_bullets(d, "La apuesta bajista",
                                         "Sus mayores PUTS (cobertura)", puts, RED)),
        ("longs", lambda d: slide_bullets(d, "Lo que SÍ le gusta",
                                          "Sus mayores posiciones alcistas", longs, GREEN)),
        ("moves", lambda d: slide_moves(d, len(opened), len(closed), top_open)),
        ("cta", lambda d: slide_cta(d)),
    ]
    total_slides = len(builders)
    paths = []
    for i, (name, fn) in enumerate(builders, 1):
        img, d = base_slide(i, total_slides)
        fn(d)
        p = f"slides/slide_{i}_{name}.png"
        img.save(p)
        paths.append(p)
        print("  ✓", p)
    print(f"\n{total_slides} slides generadas en ./slides/")
    return paths


if __name__ == "__main__":
    main()
