#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
 ETORO CLIENT  -  Cliente para la API publica de eToro
=====================================================================
Envoltorio minimo (solo stdlib) sobre la API publica de eToro para:
  - consultar cartera, balance y P&L
  - consultar metadatos de instrumentos (precios, ids)
  - ABRIR posiciones (compra/venta) a mercado
  - CERRAR posiciones

API real (lanzada por eToro a finales de 2025):
  - Base:   https://public-api.etoro.com/api/v1/
  - Auth:   cabeceras  x-api-key  y  x-user-key  (+ x-request-id)
  - Entornos: "demo" (dinero virtual) y "real" (dinero real)

SEGURIDAD (leelo):
  - Por defecto ETORO_ENV="demo"  -> opera en la cuenta VIRTUAL.
  - Por defecto ETORO_DRY_RUN="1" -> NO envia ninguna orden real; solo
    imprime lo que haria. Para ejecutar de verdad hay que poner "0"
    EXPRESAMENTE. Asi nada se ejecuta por accidente.
  - Las claves NUNCA van en el codigo: se leen de variables de entorno.

Como conseguir las claves (resumen):
  1) Cuenta de eToro verificada (KYC completo).
  2) Portal de desarrolladores: https://api-portal.etoro.com/
  3) Genera tu  x-api-key  y tu  x-user-key  y exportalas:
       export ETORO_API_KEY="..."
       export ETORO_USER_KEY="..."
=====================================================================
"""

import os
import json
import time
import uuid
import urllib.request
import urllib.parse
import urllib.error

# ----------------------------- CONFIG --------------------------------
ETORO_BASE = os.environ.get("ETORO_BASE", "https://public-api.etoro.com/api/v1")

# "demo" = cuenta virtual (recomendado para probar) | "real" = dinero real
ETORO_ENV = os.environ.get("ETORO_ENV", "demo").lower()

# "1" => simulacion (no manda ordenes). "0" => ejecuta de verdad.
DRY_RUN = os.environ.get("ETORO_DRY_RUN", "1") != "0"

ETORO_API_KEY = os.environ.get("ETORO_API_KEY", "")
ETORO_USER_KEY = os.environ.get("ETORO_USER_KEY", "")

# eToro esta detras de Cloudflare y BLOQUEA el User-Agent por defecto de
# Python (error 1010). Hay que presentarse como un navegador normal.
# Puedes cambiarlo por env si en el futuro hiciera falta otro.
ETORO_USER_AGENT = os.environ.get(
    "ETORO_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
)

# Topes de seguridad (se pueden subir por entorno, pero existen a proposito)
MAX_ORDER_USD = float(os.environ.get("ETORO_MAX_ORDER_USD", "500"))


class EtoroError(RuntimeError):
    pass


class EtoroClient:
    """Cliente fino sobre la API publica de eToro."""

    def __init__(self, env=None, dry_run=None, api_key=None, user_key=None):
        self.env = (env or ETORO_ENV).lower()
        if self.env not in ("demo", "real"):
            raise EtoroError(f"ETORO_ENV invalido: {self.env!r} (usa 'demo' o 'real')")
        self.dry_run = DRY_RUN if dry_run is None else bool(dry_run)
        self.api_key = api_key or ETORO_API_KEY
        self.user_key = user_key or ETORO_USER_KEY

    # ------------------------- HTTP interno --------------------------
    def _headers(self):
        if not self.api_key or not self.user_key:
            raise EtoroError(
                "Faltan credenciales. Exporta ETORO_API_KEY y ETORO_USER_KEY "
                "(las generas en https://api-portal.etoro.com/)."
            )
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": ETORO_USER_AGENT,
            "x-api-key": self.api_key,
            "x-user-key": self.user_key,
            "x-request-id": str(uuid.uuid4()),
        }

    def _request(self, method, path, params=None, body=None, retries=3):
        url = f"{ETORO_BASE}/{path.lstrip('/')}"
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)

        data = json.dumps(body).encode("utf-8") if body is not None else None
        last_err = None
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, data=data, method=method,
                                             headers=self._headers())
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read()
                return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                # 4xx normalmente no se arregla reintentando -> aborta con detalle
                detail = e.read().decode("utf-8", "ignore")
                raise EtoroError(f"HTTP {e.code} en {method} {path}: {detail}")
            except Exception as e:
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        raise EtoroError(f"Fallo de red en {method} {path}: {last_err}")

    # --------------------------- LECTURA -----------------------------
    def get_pnl(self):
        """Estado completo de la cuenta (incluye clientPortfolio con posiciones)."""
        return self._request("GET", f"trading/info/{self.env}/pnl")

    def get_portfolio(self):
        """Atajo: devuelve solo la parte de cartera/posiciones del P&L."""
        pnl = self.get_pnl()
        return pnl.get("clientPortfolio", pnl)

    def get_instruments(self, instrument_ids=None):
        """
        Metadatos de instrumentos (precio, nombre, tipo...).
        instrument_ids: lista de ids de eToro. Si es None, trae el universo.
        """
        params = {}
        if instrument_ids:
            params["instrumentIds"] = ",".join(str(i) for i in instrument_ids)
        return self._request("GET", "market-data/instruments", params=params)

    # -------------------------- EJECUCION ----------------------------
    def open_position(self, instrument_id, is_buy, amount_usd,
                      leverage=1, stop_loss_rate=None, take_profit_rate=None,
                      trailing_stop=False):
        """
        Abre una posicion a mercado por importe (USD).
          instrument_id    : id de eToro del activo (ver get_instruments / mapping)
          is_buy           : True=compra (largo), False=venta (corto)
          amount_usd       : importe a invertir en USD
          leverage         : apalancamiento (1 = sin apalancar; lo normal a L/P)
          stop_loss_rate   : precio de stop-loss (opcional)
          take_profit_rate : precio de take-profit (opcional)
          trailing_stop    : stop dinamico (trailing) si True
        """
        if amount_usd > MAX_ORDER_USD:
            raise EtoroError(
                f"Importe {amount_usd} > tope de seguridad {MAX_ORDER_USD} USD. "
                f"Sube ETORO_MAX_ORDER_USD si de verdad lo quieres."
            )

        body = {
            "InstrumentID": int(instrument_id),
            "IsBuy": bool(is_buy),
            "Leverage": int(leverage),
            "Amount": float(amount_usd),
            "IsTslEnabled": bool(trailing_stop),
            "IsNoStopLoss": stop_loss_rate is None,
            "IsNoTakeProfit": take_profit_rate is None,
        }
        if stop_loss_rate is not None:
            body["StopLossRate"] = float(stop_loss_rate)
        if take_profit_rate is not None:
            body["TakeProfitRate"] = float(take_profit_rate)

        path = f"trading/execution/{self.env}/market-open-orders/by-amount"
        side = "COMPRA" if is_buy else "VENTA"
        label = f"{side} instr {instrument_id} por {amount_usd} USD (x{leverage}) [{self.env}]"

        if self.dry_run:
            print(f"[DRY-RUN] No se envia. Orden simulada -> {label}")
            print(f"          POST /{path}\n          body={json.dumps(body)}")
            return {"dry_run": True, "would_send": body, "path": path}

        print(f"[LIVE:{self.env}] Enviando -> {label}")
        return self._request("POST", path, body=body)

    def close_position(self, position_id):
        """Cierra (vende/recompra) una posicion abierta por su id."""
        path = f"trading/execution/{self.env}/positions/{position_id}/close"
        if self.dry_run:
            print(f"[DRY-RUN] No se envia. Cerraria posicion {position_id} [{self.env}]")
            return {"dry_run": True, "close_position": position_id}
        print(f"[LIVE:{self.env}] Cerrando posicion {position_id}")
        return self._request("POST", path)


# --------------------------- CLI rapido ------------------------------
def _main():
    import argparse
    ap = argparse.ArgumentParser(description="Cliente API eToro (lectura/diagnostico)")
    ap.add_argument("--portfolio", action="store_true", help="Muestra la cartera actual")
    ap.add_argument("--instruments", help="Ids separados por coma para consultar")
    args = ap.parse_args()

    c = EtoroClient()
    print(f"Entorno: {c.env}  |  DRY_RUN: {c.dry_run}")
    if args.portfolio:
        print(json.dumps(c.get_portfolio(), indent=2, ensure_ascii=False))
    if args.instruments:
        ids = [x.strip() for x in args.instruments.split(",") if x.strip()]
        print(json.dumps(c.get_instruments(ids), indent=2, ensure_ascii=False))
    if not (args.portfolio or args.instruments):
        ap.print_help()


if __name__ == "__main__":
    _main()
