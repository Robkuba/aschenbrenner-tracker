#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prueba las dos llaves en los DOS ordenes posibles y te dice cual es la
combinacion correcta. Asi no hay que adivinar cual es la API_KEY y cual la
USER_KEY. Solo lee (no opera nada).

Uso (pon las dos llaves primero, en cualquier orden):
  $env:ETORO_API_KEY="valorA"
  $env:ETORO_USER_KEY="valorB"
  python diag_keys.py
"""
import os
from etoro_client import EtoroClient, EtoroError

a = os.environ.get("ETORO_API_KEY", "")
u = os.environ.get("ETORO_USER_KEY", "")

if not a or not u:
    raise SystemExit("Faltan llaves. Pon ETORO_API_KEY y ETORO_USER_KEY primero.")


def test(api, user, label):
    try:
        c = EtoroClient(api_key=api, user_key=user)
        data = c.get_instruments()
        n = len(data.get("instrumentDisplayDatas") or [])
        print(f"  {label}: OK ✅  ({n} instrumentos)")
        return True
    except EtoroError as e:
        print(f"  {label}: falla ❌  ({str(e)[:90]})")
        return False


print("Probando las dos combinaciones de tus llaves...\n")
ok_actual = test(a, u, "Como estan ahora")
ok_swap = test(u, a, "Intercambiadas")
print()

if ok_actual:
    print("✅ Tu configuracion ACTUAL es correcta. Deja las variables como estan.")
    print("   Ya puedes ejecutar:  python trade_executor.py")
elif ok_swap:
    print("🔁 ¡Estan al reves! Intercambialas asi y vuelve a probar:")
    print('   $env:ETORO_API_KEY="<el valor que ahora tienes en ETORO_USER_KEY>"')
    print('   $env:ETORO_USER_KEY="<el valor que ahora tienes en ETORO_API_KEY>"')
else:
    print("❌ Ninguna combinacion funciona -> una de las dos llaves no es valida.")
    print("   Genera una clave nueva (lectura + escritura) y copia bien LAS DOS.")
