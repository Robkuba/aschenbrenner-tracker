#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera un REEL / TikTok vertical (1080x1920) animado con los datos del
ultimo 13F del fondo. Renderiza frames con Pillow y los codifica a MP4
con ffmpeg (H.264, compatible con Instagram/TikTok).

Salida: reel_aschenbrenner.mp4   (sin audio: añade un sonido de tendencia
        dentro de la app al publicar)
Uso:    python reel_video.py
"""

import os
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont

import aschenbrenner_tracker as t
import social_content as sc

# ----------------------------- AJUSTES -------------------------------
W, H = 1080, 1920
FPS = 30
MARGIN = 90
FRAMES_DIR = "_frames"
OUT = "reel_aschenbrenner.mp4"

HANDLE = "@robkubanoinvest"
BRAND = "ROBKUBANO"

BG = (13, 17, 23)
CARD = (22, 27, 34)
WHITE = (230, 237, 243)
MUTED = (139, 148, 158)
GREEN = (46, 160, 67)
BLUE = (88, 166, 255)
RED = (248, 81, 73)
ACCENT = (88, 166, 255)

FONT_DIR = "/usr/share/fonts/truetype/google-fonts"
from fonts_util import font, F_BOLD, F_MED, F_REG, F_LIGHT


# --------------------------- UTILIDADES ------------------------------
def ease(t):           # ease-out cubico
    return 1 - (1 - t) ** 3


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def lerp(c1, c2, a):   # interpola color (para fundidos sobre fondo)
    return tuple(int(c1[i] + (c2[i] - c1[i]) * a) for i in range(3))


def fade(color, a):    # funde desde el fondo hacia 'color'
    return lerp(BG, color, clamp(a))


def text(d, xy, s, fnt, color, a=1.0, anchor="la"):
    d.text(xy, s, font=fnt, fill=fade(color, a), anchor=anchor)


def chrome(d, progress):
    text(d, (MARGIN, 80), BRAND, font(F_BOLD, 34), WHITE)
    text(d, (MARGIN + 250, 84), HANDLE, font(F_REG, 28), MUTED)
    d.rectangle([MARGIN, 138, MARGIN + 80, 145], fill=ACCENT)
    # barra de progreso del video
    d.rectangle([0, H - 8, int(W * progress), H], fill=ACCENT)


# --------------------------- ESCENAS ---------------------------------
def scene_hook(d, p, put_total_b):
    # numero que cuenta hasta el total de puts
    val = put_total_b * ease(clamp(p / 0.55))
    text(d, (MARGIN, 470), "13F · Q1 2026", font(F_MED, 40), ACCENT)
    text(d, (W // 2, 760), f"${val:.2f}B", font(F_BOLD, 250), RED,
         a=clamp(p / 0.25), anchor="mm")
    sub_a = clamp((p - 0.45) / 0.3)
    for i, ln in enumerate(["EN PUTS CONTRA", "NVIDIA Y LOS CHIPS DE IA"]):
        text(d, (W // 2, 1040 + i * 100), ln, font(F_BOLD, 70 if i == 0 else 58),
             WHITE, a=sub_a, anchor="mm")
    text(d, (W // 2, 1320), "El fondo de IA de Leopold Aschenbrenner",
         font(F_REG, 40), MUTED, a=clamp((p - 0.6) / 0.3), anchor="mm")


def scene_bars(d, p, qdata):
    text(d, (W // 2, 470), "De $0.3B a $13.7B", font(F_BOLD, 72), WHITE,
         a=clamp(p / 0.2), anchor="mm")
    text(d, (W // 2, 560), "en 6 trimestres", font(F_MED, 46), ACCENT,
         a=clamp(p / 0.2), anchor="mm")
    # leyenda
    leg = [("Acciones", GREEN), ("Calls", BLUE), ("Puts", RED)]
    lx = MARGIN
    for label, col in leg:
        d.rectangle([lx, 650, lx + 30, 680], fill=fade(col, clamp(p / 0.25)))
        text(d, (lx + 45, 648), label, font(F_REG, 32), MUTED, a=clamp(p / 0.25))
        lx += d.textlength(label, font=font(F_REG, 32)) + 130

    left, right = 120, W - 90
    top, base = 780, 1640
    maxv = 14.0
    scale = (base - top) / maxv
    n = len(qdata)
    slot = (right - left) / n
    barw = slot * 0.6
    for qi, (q, lv, cv, pv) in enumerate(qdata):
        start = qi * 0.07
        lp = ease(clamp((p - start) / 0.5))
        cx = left + slot * qi + slot / 2
        x0, x1 = cx - barw / 2, cx + barw / 2
        y = base
        for val, col in [(lv, GREEN), (cv, BLUE), (pv, RED)]:
            h = val * scale * lp
            if h > 0.5:
                d.rectangle([x0, y - h, x1, y], fill=col)
            y -= h
        # etiqueta total
        tot = lv + cv + pv
        if lp > 0.85:
            text(d, (cx, y - 36), f"${tot:.1f}B", font(F_BOLD, 30), WHITE,
                 a=clamp((lp - 0.85) / 0.15), anchor="mm")
        # etiqueta trimestre
        text(d, (cx, base + 36), q, font(F_MED, 30), MUTED,
             a=clamp(p / 0.3), anchor="mm")


def scene_puts(d, p, puts):
    text(d, (W // 2, 520), "Las mayores apuestas", font(F_BOLD, 66), WHITE,
         a=clamp(p / 0.2), anchor="mm")
    text(d, (W // 2, 600), "BAJISTAS", font(F_BOLD, 66), RED,
         a=clamp(p / 0.2), anchor="mm")
    y = 800
    for i, (name, val) in enumerate(puts):
        ra = clamp((p - 0.15 - i * 0.14) / 0.25)
        if ra <= 0:
            continue
        # deslizamiento sutil desde la derecha
        dx = int((1 - ease(ra)) * 80)
        cx = MARGIN + 14 + dx
        d.ellipse([cx - 13, y - 13, cx + 13, y + 13], fill=fade(RED, ra))
        text(d, (MARGIN + 55 + dx, y), name, font(F_MED, 46), WHITE, a=ra, anchor="lm")
        text(d, (W - MARGIN, y), val, font(F_BOLD, 46), RED, a=ra, anchor="rm")
        y += 150


def scene_cta(d, p):
    text(d, (W // 2, 640), "¿Tiene razón", font(F_BOLD, 84), WHITE,
         a=clamp(p / 0.25), anchor="mm")
    text(d, (W // 2, 740), "con la IA?", font(F_BOLD, 84), WHITE,
         a=clamp(p / 0.25), anchor="mm")
    box_a = clamp((p - 0.25) / 0.3)
    if box_a > 0:
        d.rounded_rectangle([MARGIN, 950, W - MARGIN, 1200], radius=28,
                            fill=lerp(BG, CARD, box_a))
        text(d, (W // 2, 1030), "Guarda este post y sígueme", font(F_MED, 44),
             WHITE, a=box_a, anchor="mm")
        text(d, (W // 2, 1110), HANDLE, font(F_BOLD, 64), ACCENT, a=box_a, anchor="mm")
    text(d, (W // 2, 1330),
         "El 13F es trimestral y con retraso. Información, no recomendación.",
         font(F_REG, 30), MUTED, a=clamp((p - 0.5) / 0.3), anchor="mm")


# ----------------------------- TIMELINE ------------------------------
def main():
    print("Descargando datos de la SEC...")
    fund_name, filings = t.get_13f_filings()

    qdata = []
    for fil in filings:
        h = t.fetch_holdings(fil["accession"])
        lv = sum(d["value"] for d in h.values() if d["put_call"] == "") / 1e9
        cv = sum(d["value"] for d in h.values() if d["put_call"] == "Call") / 1e9
        pv = sum(d["value"] for d in h.values() if d["put_call"] == "Put") / 1e9
        # etiqueta corta Q4'24
        ql = t.quarter_label(fil["period"]).replace(" 20", " '")
        qdata.append((ql, lv, cv, pv))
    cur = t.fetch_holdings(filings[-1]["accession"])
    put_total_b = sum(d["value"] for d in cur.values() if d["put_call"] == "Put") / 1e9
    puts = [(h["name"].title()[:24], t.fmt_money(h["value"])) for h in sc.top_by_type(cur, "Put", 5)]

    # (escena, duracion_seg)
    scenes = [("hook", 4.0), ("bars", 5.0), ("puts", 4.0), ("cta", 3.0)]
    total_sec = sum(s[1] for s in scenes)
    total_frames = int(total_sec * FPS)
    print(f"Renderizando {total_frames} frames ({total_sec:.0f}s)...")

    if os.path.exists(FRAMES_DIR):
        shutil.rmtree(FRAMES_DIR)
    os.makedirs(FRAMES_DIR)

    # construir lista de (nombre, p_local) por frame
    fno = 0
    for name, dur in scenes:
        nfr = int(dur * FPS)
        for k in range(nfr):
            p = k / max(1, nfr - 1)
            img = Image.new("RGB", (W, H), BG)
            d = ImageDraw.Draw(img)
            chrome(d, fno / total_frames)
            if name == "hook":
                scene_hook(d, p, put_total_b)
            elif name == "bars":
                scene_bars(d, p, qdata)
            elif name == "puts":
                scene_puts(d, p, puts)
            elif name == "cta":
                scene_cta(d, p)
            img.save(f"{FRAMES_DIR}/f_{fno:05d}.png")
            fno += 1
    print(f"  {fno} frames generados. Codificando MP4...")

    cmd = ["ffmpeg", "-y", "-framerate", str(FPS),
           "-i", f"{FRAMES_DIR}/f_%05d.png",
           "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", OUT]
    subprocess.run(cmd, check=True, capture_output=True)
    shutil.rmtree(FRAMES_DIR)
    size = os.path.getsize(OUT) / 1e6
    print(f"\n✅ Video listo: {OUT} ({size:.1f} MB, {total_sec:.0f}s, {W}x{H})")


if __name__ == "__main__":
    main()
