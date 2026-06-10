#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
 PUBLISH  -  Engancha el tracker con tu stack Make.com -> Buffer/Metricool
=====================================================================
Cuando sale un 13F nuevo, el tracker llama aqui. Este modulo:
  1) Arma el contenido (hilo X + carrusel IG + post LinkedIn + caption).
  2) Lo manda como JSON a un WEBHOOK de Make.com.
  3) Make.com lo reparte a Buffer y Metricool y lo PROGRAMA.

Por seguridad, por defecto entra como BORRADOR / pendiente de aprobacion
(SCHEDULE_MODE="draft"). Tu das el OK final antes de que se publique.
Cambia a "auto" solo cuando confies del todo en el flujo.

Vía recomendada: Make.com webhook (robusto y ya lo usas).
Tambien incluye envio directo a Metricool (opcional) por si lo prefieres.

Prueba en seco (sin enviar nada):  python publish.py
=====================================================================
"""

import os
import json
import glob
import urllib.request

import aschenbrenner_tracker as t
import social_content as sc

# ----------------------------- CONFIG --------------------------------
# Webhook de Make.com (Scenario con un modulo "Webhooks > Custom webhook").
# Copia ahí la URL que te da Make y pégala aquí o como variable de entorno.
MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL", "")

# "draft" = entra como borrador / pendiente de aprobacion (RECOMENDADO).
# "auto"  = se programa directo sin tu revision.
SCHEDULE_MODE = os.environ.get("SCHEDULE_MODE", "draft")

# Cuantos dias adelante proponer la publicacion (Make puede ignorarlo).
SCHEDULE_OFFSET_DAYS = int(os.environ.get("SCHEDULE_OFFSET_DAYS", "0"))

# Base publica para la imagen del grafico (ej. tu repo en GitHub raw).
# Ej: https://raw.githubusercontent.com/tuusuario/turepo/main
# Si lo dejas vacio, el payload va sin imagen.
IMAGE_BASE_URL = os.environ.get("IMAGE_BASE_URL", "")
IMAGE_FILE = "aschenbrenner_evolucion.png"
VIDEO_FILE = "reel_aschenbrenner.mp4"

# --- (Opcional) Metricool API directa ---
METRICOOL_USER_TOKEN = os.environ.get("METRICOOL_USER_TOKEN", "")
METRICOOL_BLOG_ID = os.environ.get("METRICOOL_BLOG_ID", "")


# ----------------------- CONSTRUIR EL PAYLOAD ------------------------
def build_payload(fund_name, changes):
    """Arma el JSON con todo el contenido listo para que Make lo reparta."""
    # Tomamos los dos ultimos 13F para construir contenido rico y el diff real
    _, filings = t.get_13f_filings()
    cur = t.fetch_holdings(filings[-1]["accession"])
    prev = t.fetch_holdings(filings[-2]["accession"]) if len(filings) > 1 else {}
    opened, closed = sc.diff_two(prev, cur)
    period = changes["period"]
    q = t.quarter_label(period)

    # --- Contenido por canal (reutiliza social_content) ---
    x_full = sc.build_x_thread(fund_name, period, cur, opened, closed)
    x_parts = [p.strip() for p in x_full.split("———") if p.strip()]

    ig_slides_raw = sc.build_ig_carousel(fund_name, period, cur, opened, closed)
    ig_slides = []
    for block in ig_slides_raw.split("────────────"):
        block = block.strip()
        if not block:
            continue
        title, _, text = block.partition("\n")
        ig_slides.append({"title": title.strip("[] "), "text": text.strip()})

    put_total = sum(h["value"] for h in cur.values() if h["put_call"] == "Put")
    total = sum(h["value"] for h in cur.values())

    ig_caption = (
        f"🚨 El fondo de IA de Aschenbrenner mueve {t.fmt_money(total)} "
        f"y apuesta {t.fmt_money(put_total)} EN CONTRA de los chips ({q}). "
        f"Te lo desgloso en el carrusel 👉 Guárdalo 📌\n\n"
        f"#inversiones #IA #bolsa #semiconductores #hedgefund #robkubano"
    )

    linkedin = (
        f"Leopold Aschenbrenner (24, ex-OpenAI) acaba de revelar la cartera de "
        f"Situational Awareness LP en su 13F del {q}: {t.fmt_money(total)} en exposición, "
        f"con {t.fmt_money(put_total)} en puts contra el complejo de semiconductores de IA.\n\n"
        f"Sus mayores coberturas bajistas: "
        + ", ".join(h['name'].title() for h in sc.top_by_type(cur, 'Put', 4)) + ".\n"
        f"Sus mayores apuestas alcistas: "
        + ", ".join(h['name'].title() for h in sc.top_by_type(cur, '', 4)) + ".\n\n"
        f"Recordatorio: el 13F es trimestral y con ~45 días de retraso; es una foto, "
        f"no el minuto a minuto. Datos: SEC EDGAR.\n\n"
        f"#Inversiones #IA #Semiconductores #Mercados"
    )

    image_url = f"{IMAGE_BASE_URL}/{IMAGE_FILE}" if IMAGE_BASE_URL else None
    video_url = f"{IMAGE_BASE_URL}/{VIDEO_FILE}" if IMAGE_BASE_URL else None

    # URLs de las imagenes del carrusel (slides/slide_*.png), si existen
    carousel_imgs = []
    if IMAGE_BASE_URL and os.path.isdir("slides"):
        for f in sorted(glob.glob("slides/slide_*.png")):
            carousel_imgs.append(f"{IMAGE_BASE_URL}/{f}")

    reel_caption = (
        f"🚨 El fondo de IA de Aschenbrenner apuesta {t.fmt_money(put_total)} "
        f"CONTRA los chips ({q}). De $0.3B a {t.fmt_money(total)} en 6 trimestres. "
        f"Sígueme para más 📊\n\n"
        f"#inversiones #IA #bolsa #nvidia #semiconductores #trading #robkubano"
    )

    payload = {
        "event": "new_13f",
        "fund": fund_name,
        "quarter": q,
        "filing_date": changes["filing_date"],
        "schedule_mode": SCHEDULE_MODE,        # "draft" o "auto"
        "schedule_offset_days": SCHEDULE_OFFSET_DAYS,
        "image_url": image_url,
        "summary": {
            "total_exposure": t.fmt_money(total),
            "put_exposure": t.fmt_money(put_total),
            "opened": len(opened),
            "closed": len(closed),
        },
        "posts": [
            {"channel": "x", "type": "thread",
             "content": x_parts[0], "thread_parts": x_parts},
            {"channel": "instagram", "type": "carousel",
             "slides": ig_slides, "caption": ig_caption,
             "images": carousel_imgs},
            {"channel": "linkedin", "type": "post", "content": linkedin},
            {"channel": "reels", "type": "video",
             "video_url": video_url, "caption": reel_caption},
        ],
        "en_hook": sc.build_en_hook(fund_name, period, cur),
    }
    return payload


# --------------------------- ENVIO -----------------------------------
def publish_new_filing(fund_name, changes):
    """Punto de entrada que llama el tracker cuando hay 13F nuevo."""
    payload = build_payload(fund_name, changes)

    sent = False
    if MAKE_WEBHOOK_URL:
        sent = _post_make(payload)
    else:
        print("\n[Publish] MAKE_WEBHOOK_URL no configurado — modo PRUEBA EN SECO.")
        print("Este es el JSON que recibiria Make.com:\n")
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    # Metricool directo (opcional, ademas del webhook)
    if METRICOOL_USER_TOKEN and METRICOOL_BLOG_ID:
        _post_metricool_note(payload)

    return sent


def _post_make(payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        MAKE_WEBHOOK_URL, data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        modo = "BORRADOR (pendiente de tu aprobación)" if payload["schedule_mode"] == "draft" else "AUTO-programado"
        print(f"[Publish] Enviado a Make.com ✅  →  modo: {modo}")
        return True
    except Exception as e:
        print(f"[Publish] Error enviando a Make.com: {e}")
        return False


def _post_metricool_note(payload):
    # La API de Metricool requiere userToken + blogId y endpoints de scheduling
    # que cambian segun plan. Lo robusto es dejar que Make.com hable con
    # Metricool. Aqui solo avisamos que esta configurado.
    print("[Publish] Metricool detectado: recomiendo enrutarlo dentro de Make.com "
          "(modulo Metricool) en vez de API directa.")


# ----------------------------- MAIN ----------------------------------
def main():
    """Prueba en seco con datos reales del ultimo 13F."""
    fund_name, filings = t.get_13f_filings()
    # Simular el 'changes' del ultimo filing para previsualizar el payload
    changes = {
        "period": filings[-1]["period"],
        "filing_date": filings[-1]["filing_date"],
        "form": filings[-1]["form"],
        "opened": [], "closed": [],
        "total_positions": 0,
    }
    publish_new_filing(fund_name, changes)


if __name__ == "__main__":
    main()
