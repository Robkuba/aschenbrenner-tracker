# 🧾 Chuleta de comandos (Windows PowerShell)

Comandos exactos para usar el robot **Kubabot**. Copia y pega tal cual.
Cambia los `...` por tus valores reales.

> 📛 **Nombres actuales:** cartera de agentes **kubabot-rkuhwqhq** ·
> clave API de **demo** = **xbot** (para practicar en la cuenta principal).

> 🔑 Recuerda: las llaves **se borran al cerrar la ventana** de PowerShell.
> Si abres una nueva, vuelve a pegar los pasos 1 y 2.

---

## 0) Ir a la carpeta y bajar lo último (una vez)
```powershell
cd $HOME\aschenbrenner-tracker
git pull origin claude/etoro-agent-portfolio-2fcabz
```

## 1) Poner tus DOS llaves
```powershell
$env:ETORO_API_KEY="...tu_API_KEY..."
$env:ETORO_USER_KEY="...tu_USER_KEY..."
```

## 2) Elegir el mundo
```powershell
# PRACTICAR (cuenta principal, dinero de mentira):
$env:ETORO_ENV="demo"

# REAL (cartera Kubabot, dinero de verdad):
# $env:ETORO_ENV="real"
```

## 3) Comprobar permisos (NO compra nada)
```powershell
python diag_perm.py
```
Tiene que salir:  `Leer el mercado: OK ✅`  y  `Acceder a tu cartera / operar: OK ✅`

> Si las llaves dan 401, prueba a ver cuál va en cada sitio:
> ```powershell
> python diag_keys.py
> ```

## 4) Ver qué compraría (SIMULACIÓN, no envía)
```powershell
$env:ETORO_DRY_RUN="1"
$env:PROPOSED_FILE="orders_kubabot_200.json"
python trade_executor.py
```

## 5) COMPRAR de verdad (envía las 12 órdenes)
```powershell
$env:ETORO_DRY_RUN="0"
$env:PROPOSED_FILE="orders_kubabot_200.json"
python trade_executor.py
```
Escribe **`SI`** cuando lo pida. Verás `OK ...` y `Resumen: 12 enviadas, 0 saltadas`.

---

## Extras (cuando ya tengas posiciones)
```powershell
# Ver tu cartera y ganancias/pérdidas:
python portfolio_report.py

# Revisar desviaciones del plan:
python rebalance.py
```

---

## 🆘 Si algo falla
| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| `401 Unauthorized` | Las dos llaves no casan | `python diag_keys.py` (intercámbialas) |
| `403 InsufficientPermissions` | La llave no puede operar | Usa la llave con **escritura**; en Kubabot usa `ETORO_ENV="real"` |
| `sin precio en vivo` | No bajó el precio | No es grave; la orden entra sin stop/take-profit |
| `No existe orders_kubabot_200.json` | Carpeta equivocada | Vuelve al paso 0 (`cd ...`) |

---

## 🔒 Reglas de oro
- Practica en **demo** antes de ir a **real**.
- **Nunca** compartas tus llaves (ni chat, ni fotos).
- Kubabot es **dinero real**: revisa antes de escribir `SI`.
