#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprueba, en cristiano, que permisos tiene tu llave actual:
  1) Leer el mercado (publico)
  2) Acceder a tu cartera / operar
No envia ninguna orden.  Uso:  python diag_perm.py
"""
from etoro_client import EtoroClient, EtoroError

c = EtoroClient()
print(f"Entorno: {c.env}\n")


def check(label, fn):
    try:
        fn()
        print(f"  {label}: OK ✅")
        return True
    except EtoroError as e:
        print(f"  {label}: NO ❌  ({str(e)[:80]})")
        return False


pub = check("Leer el mercado (publico)", lambda: c.get_instruments())
acc = check("Acceder a tu cartera / operar", lambda: c.get_pnl())
print()

if pub and acc:
    print("✅ Permisos correctos. Ya puedes operar:  python trade_executor.py")
elif pub and not acc:
    print("⚠️  Tu llave solo MIRA el mercado, no puede operar tu cartera.")
    print("    -> Usa como ETORO_USER_KEY la llave 'kubabot' con LECTURA + ESCRITURA.")
    print("    -> Si tienes varias llaves y dudas, borra las viejas y deja solo esa.")
else:
    print("❌ La llave no autentica. Revisa ETORO_API_KEY / ETORO_USER_KEY (orden y valor).")
