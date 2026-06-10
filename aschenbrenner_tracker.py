#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
 ASCHENBRENNER TRACKER  -  Situational Awareness LP (13F SEC)
=====================================================================
Vigila los reportes 13F del fondo de Leopold Aschenbrenner en la SEC
(EDGAR) y, cuando se publica uno nuevo, detecta qué posiciones se
ABRIERON y cuáles se CERRARON ese trimestre, y te avisa por WhatsApp.

LIMITES REALES (importante):
  - El 13F es TRIMESTRAL y se publica hasta 45 dias DESPUES del cierre
    del trimestre. No existe dato "en vivo" de un fondo privado.
  - No revela el DIA exacto de compra/venta, solo una foto al cierre
    del trimestre. Por eso "comprado"/"vendido" se expresan en TRIMESTRE.
  - Solo cubre acciones y opciones cotizadas en EE.UU. (largos/calls/puts).

Uso:
  python aschenbrenner_tracker.py            -> revisa si hay 13F nuevo y alerta
  python aschenbrenner_tracker.py --report   -> imprime la cartera actual
  python aschenbrenner_tracker.py --test-wa  -> manda un WhatsApp de prueba
=====================================================================
"""

import os
import sys
import json
import time
import argparse
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

# ----------------------------- CONFIG --------------------------------
# CIK del fondo en la SEC (Situational Awareness LP)
CIK = "0002045724"
CIK_NUM = str(int(CIK))  # sin ceros a la izquierda -> "2045724"

# La SEC EXIGE un User-Agent con tu nombre/proyecto y un email de contacto.
# Cambialo por el tuyo (cualquier email valido sirve).
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "Robkubano Tracker robkubano@example.com")

# --- WhatsApp via CallMeBot (gratis, ideal para avisarte a TI MISMO) ---
# Como obtener tu apikey (2 minutos):
#   1) Guarda el numero +34 644 22 56 67 en tus contactos.
#   2) Mandale por WhatsApp el mensaje:  I allow callmebot to send me messages
#   3) Te responde con tu "apikey". Ponla abajo (o como variable de entorno).
CALLMEBOT_PHONE = os.environ.get("CALLMEBOT_PHONE", "")   # ej: "+4915123456789"
CALLMEBOT_APIKEY = os.environ.get("CALLMEBOT_APIKEY", "")

# --- (Opcional) WhatsApp via Twilio, si prefieres algo profesional ---
TWILIO_SID = os.environ.get("TWILIO_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN", "")
TWILIO_FROM = os.environ.get("TWILIO_FROM", "whatsapp:+14155238886")  # sandbox
TWILIO_TO = os.environ.get("TWILIO_TO", "")  # ej: "whatsapp:+4915123456789"

# Archivo donde el bot recuerda lo que ya proceso (entre ejecuciones)
STATE_FILE = os.environ.get("STATE_FILE", "state.json")

# En la PRIMERA ejecucion: ¿mandar un WhatsApp de "baseline cargado"?
ALERT_ON_FIRST_RUN = True


# --------------------------- HTTP HELPER -----------------------------
def http_get(url, as_json=False, retries=3):
    """GET educado con EDGAR: User-Agent obligatorio + reintentos."""
    headers = {"User-Agent": SEC_USER_AGENT}
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            time.sleep(0.25)  # la SEC pide < 10 req/seg; vamos tranquilos
            return json.loads(data) if as_json else data
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Fallo al pedir {url}: {last_err}")


# ----------------------- EDGAR: LISTA DE 13F -------------------------
def get_13f_filings():
    """Devuelve la lista de 13F-HR ordenada del mas antiguo al mas nuevo."""
    sub = http_get(f"https://data.sec.gov/submissions/CIK{CIK}.json", as_json=True)
    name = sub.get("name", "Situational Awareness LP")
    recent = sub["filings"]["recent"]
    out = []
    for i, form in enumerate(recent["form"]):
        if form.startswith("13F-HR"):  # incluye 13F-HR y enmiendas 13F-HR/A
            out.append({
                "form": form,
                "accession": recent["accessionNumber"][i],
                "filing_date": recent["filingDate"][i],
                "period": recent["reportDate"][i],  # cierre del trimestre
            })
    out.sort(key=lambda x: (x["period"], x["filing_date"]))
    return name, out


# ------------------- EDGAR: POSICIONES DE UN 13F ---------------------
def _localname(tag):
    return tag.split("}")[-1]


def fetch_holdings(accession):
    """
    Descarga y parsea la 'information table' de un 13F.
    Devuelve un dict:  clave (cusip, putCall) -> datos de la posicion.
    putCall = "" significa accion comun (largo). "Call"/"Put" = opciones.
    """
    acc_nodash = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{CIK_NUM}/{acc_nodash}/"
    idx = http_get(base + "index.json", as_json=True)
    files = [it["name"] for it in idx["directory"]["item"]]

    # Buscar el XML que contiene la tabla de posiciones (no el primary_doc)
    info_xml = None
    for f in files:
        if f.lower().endswith(".xml"):
            raw = http_get(base + f).decode("utf-8", "ignore")
            if "infoTable" in raw or "informationTable" in raw:
                info_xml = raw
                break
    if not info_xml:
        return {}

    root = ET.fromstring(info_xml.encode("utf-8"))
    holdings = {}
    for it in root.iter():
        if _localname(it.tag) != "infoTable":
            continue
        d = {"name": "", "cusip": "", "value": 0.0, "shares": 0.0,
             "share_type": "", "put_call": ""}
        for ch in it.iter():
            ln = _localname(ch.tag)
            txt = (ch.text or "").strip()
            if ln == "nameOfIssuer":
                d["name"] = txt
            elif ln == "cusip":
                d["cusip"] = txt
            elif ln == "value":
                d["value"] = float(txt or 0)
            elif ln == "sshPrnamt":
                d["shares"] = float(txt or 0)
            elif ln == "sshPrnamtType":
                d["share_type"] = txt
            elif ln == "putCall":
                d["put_call"] = txt
        key = (d["cusip"], d["put_call"])
        if key in holdings:  # sumar si una posicion aparece en varias lineas
            holdings[key]["value"] += d["value"]
            holdings[key]["shares"] += d["shares"]
        else:
            holdings[key] = d
    return holdings


# --------------------------- ESTADO LOCAL ----------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"processed": [], "last_period": None, "assets": {}}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# --------------------------- LOGICA CORE -----------------------------
def kind_label(put_call):
    return {"": "ACCION (largo)", "Call": "CALL (alcista)", "Put": "PUT (bajista)"}.get(put_call, put_call)


def process_filings(state, filings, verbose=True):
    """
    Procesa cronologicamente los 13F que falten.
    Actualiza state['assets'] con first_seen (trimestre de compra) y
    exit_period (trimestre de venta). Devuelve los cambios del ULTIMO
    filing nuevo procesado (para la alerta).
    """
    processed = set(state["processed"])
    assets = state["assets"]
    prev_keys = set()  # posiciones del trimestre anterior ya procesado

    # Reconstruir prev_keys del estado (las que siguen abiertas)
    for k, a in assets.items():
        if a.get("status") == "open":
            prev_keys.add(k)

    last_changes = None

    for fil in filings:
        if fil["accession"] in processed:
            continue

        period = fil["period"]
        holdings = fetch_holdings(fil["accession"])
        cur_keys = set("|".join(k) for k in holdings.keys())

        opened, closed = [], []

        # Nuevas posiciones (abiertas este trimestre)
        for k, h in holdings.items():
            kid = "|".join(k)
            if kid not in assets:
                assets[kid] = {
                    "name": h["name"], "cusip": h["cusip"], "put_call": h["put_call"],
                    "first_seen": period, "last_seen": period,
                    "value": h["value"], "shares": h["shares"], "status": "open",
                }
                opened.append(assets[kid])
            else:
                a = assets[kid]
                if a.get("status") == "closed":  # reabrio una posicion vieja
                    a["status"] = "open"
                    a["reopened"] = period
                    opened.append(a)
                a["last_seen"] = period
                a["value"] = h["value"]
                a["shares"] = h["shares"]

        # Posiciones cerradas (estaban antes, ya no estan)
        for kid in list(prev_keys):
            if kid not in cur_keys and assets.get(kid, {}).get("status") == "open":
                assets[kid]["status"] = "closed"
                assets[kid]["exit_period"] = period
                closed.append(assets[kid])

        last_changes = {"period": period, "filing_date": fil["filing_date"],
                        "form": fil["form"], "opened": opened, "closed": closed,
                        "total_positions": len(holdings)}
        prev_keys = cur_keys
        processed.add(fil["accession"])
        state["last_period"] = period
        if verbose:
            print(f"  Procesado {fil['form']} ({period}): "
                  f"{len(holdings)} posiciones, +{len(opened)} abiertas, -{len(closed)} cerradas")

    state["processed"] = sorted(processed)
    return last_changes


# --------------------------- FORMATO ---------------------------------
def fmt_money(v):
    v = float(v)
    if v >= 1e9:
        return f"${v/1e9:.2f}B"
    if v >= 1e6:
        return f"${v/1e6:.1f}M"
    if v >= 1e3:
        return f"${v/1e3:.0f}K"
    return f"${v:.0f}"


def quarter_label(period_yyyy_mm_dd):
    """'2026-03-31' -> 'Q1 2026'."""
    try:
        d = datetime.strptime(period_yyyy_mm_dd, "%Y-%m-%d")
        q = (d.month - 1) // 3 + 1
        return f"Q{q} {d.year}"
    except Exception:
        return period_yyyy_mm_dd


def build_report(fund_name, state):
    """Reporte legible de la cartera: abiertas + cerradas, con trimestres."""
    assets = state["assets"]
    lines = []
    lines.append("=" * 60)
    lines.append(f" {fund_name}")
    lines.append(f" Ultimo trimestre reportado: {quarter_label(state.get('last_period'))}")
    lines.append("=" * 60)

    open_assets = [a for a in assets.values() if a.get("status") == "open"]
    closed_assets = [a for a in assets.values() if a.get("status") == "closed"]
    open_assets.sort(key=lambda a: -a.get("value", 0))

    total = sum(a.get("value", 0) for a in open_assets)
    lines.append(f"\nPOSICIONES ABIERTAS: {len(open_assets)}  |  Valor total: {fmt_money(total)}")
    lines.append("-" * 60)
    for a in open_assets:
        lines.append(
            f"{a['name'][:30]:30} | {kind_label(a['put_call']):16} | "
            f"{fmt_money(a.get('value',0)):>9} | comprado: {quarter_label(a['first_seen'])}"
        )

    if closed_assets:
        closed_assets.sort(key=lambda a: a.get("exit_period", ""), reverse=True)
        lines.append(f"\nPOSICIONES CERRADAS (vendidas): {len(closed_assets)}")
        lines.append("-" * 60)
        for a in closed_assets:
            lines.append(
                f"{a['name'][:30]:30} | {kind_label(a['put_call']):16} | "
                f"comprado: {quarter_label(a['first_seen'])} -> "
                f"vendido: {quarter_label(a.get('exit_period',''))}"
            )

    lines.append("\nNota: el 13F es trimestral (foto al cierre, +45 dias de retraso).")
    lines.append("'comprado/vendido' = TRIMESTRE en que aparecio/desaparecio, no dia exacto.")
    return "\n".join(lines)


def build_alert_message(fund_name, changes):
    """Mensaje corto para WhatsApp cuando sale un 13F nuevo."""
    q = quarter_label(changes["period"])
    msg = [f"🚨 {fund_name}", f"Nuevo 13F publicado ({changes['filing_date']}) — cartera al cierre de {q}.", ""]
    if changes["opened"]:
        msg.append(f"🟢 ABRIO {len(changes['opened'])} posicion(es):")
        for a in changes["opened"][:15]:
            msg.append(f"  • {a['name']} [{kind_label(a['put_call'])}] {fmt_money(a.get('value',0))}")
    if changes["closed"]:
        msg.append(f"\n🔴 CERRO {len(changes['closed'])} posicion(es):")
        for a in changes["closed"][:15]:
            msg.append(f"  • {a['name']} [{kind_label(a['put_call'])}]")
    if not changes["opened"] and not changes["closed"]:
        msg.append("Sin cambios de apertura/cierre vs el trimestre anterior.")
    msg.append(f"\nTotal de posiciones: {changes['total_positions']}")
    return "\n".join(msg)


# --------------------------- WHATSAPP --------------------------------
def send_whatsapp(text):
    """Manda el mensaje por WhatsApp. Usa CallMeBot; si no, Twilio."""
    if CALLMEBOT_PHONE and CALLMEBOT_APIKEY:
        return _send_callmebot(text)
    if TWILIO_SID and TWILIO_TOKEN and TWILIO_TO:
        return _send_twilio(text)
    print("\n[WhatsApp NO configurado] El mensaje habria sido:\n")
    print(text)
    return False


def _send_callmebot(text):
    base = "https://api.callmebot.com/whatsapp.php"
    params = urllib.parse.urlencode({
        "phone": CALLMEBOT_PHONE, "text": text, "apikey": CALLMEBOT_APIKEY,
    })
    try:
        http_get(f"{base}?{params}")
        print("[WhatsApp] Enviado via CallMeBot ✅")
        return True
    except Exception as e:
        print(f"[WhatsApp] Error CallMeBot: {e}")
        return False


def _send_twilio(text):
    import base64
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    data = urllib.parse.urlencode({"From": TWILIO_FROM, "To": TWILIO_TO, "Body": text}).encode()
    auth = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        urllib.request.urlopen(req, timeout=30)
        print("[WhatsApp] Enviado via Twilio ✅")
        return True
    except Exception as e:
        print(f"[WhatsApp] Error Twilio: {e}")
        return False


# ----------------------------- MAIN ----------------------------------
def main():
    ap = argparse.ArgumentParser(description="Tracker del fondo de Aschenbrenner (13F)")
    ap.add_argument("--report", action="store_true", help="Imprime la cartera actual y sale")
    ap.add_argument("--test-wa", action="store_true", help="Manda un WhatsApp de prueba")
    args = ap.parse_args()

    if args.test_wa:
        send_whatsapp("✅ Prueba del Aschenbrenner Tracker: WhatsApp funcionando.")
        return

    print("Consultando SEC EDGAR...")
    fund_name, filings = get_13f_filings()
    print(f"Fondo: {fund_name} | {len(filings)} reportes 13F historicos\n")

    state = load_state()
    first_run = len(state["processed"]) == 0

    changes = process_filings(state, filings)
    save_state(state)

    if args.report:
        print("\n" + build_report(fund_name, state))
        return

    if changes is None:
        print("\nNo hay 13F nuevo desde la ultima revision. Nada que alertar.")
        return

    # Hubo filings nuevos procesados -> decidir si alertar
    if first_run:
        print("\nBaseline cargado (primera ejecucion).")
        if ALERT_ON_FIRST_RUN:
            q = quarter_label(state.get("last_period"))
            n = len([a for a in state["assets"].values() if a.get("status") == "open"])
            send_whatsapp(f"✅ Tracker activado para {fund_name}.\n"
                          f"Cartera base cargada: {n} posiciones (cierre {q}).\n"
                          f"Te avisare en cuanto publiquen el proximo 13F.")
    else:
        print("\n¡13F NUEVO detectado! Enviando alerta...")
        send_whatsapp(build_alert_message(fund_name, changes))
        # Enganchar con Make.com -> Buffer/Metricool (si publish.py existe)
        try:
            import publish
            publish.publish_new_filing(fund_name, changes)
        except ModuleNotFoundError:
            pass
        except Exception as e:
            print(f"[Publish] No se pudo programar el contenido: {e}")

    print("\nListo. Estado guardado en", STATE_FILE)


if __name__ == "__main__":
    main()
