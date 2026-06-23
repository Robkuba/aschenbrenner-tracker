# Cartera de Agentes — Trading en eToro (compra/venta)

Sistema mínimo (solo Python estándar, sin dependencias) para **analizar el
mercado, proponer operaciones y ejecutarlas en eToro** con tu aprobación.

> ⚠️ **Aviso importante.** Esto **no es asesoramiento financiero**. Son
> herramientas + ideas para que **tú** decidas. Empieza siempre en **demo**
> (dinero virtual) y con `DRY_RUN` activado. La inversión conlleva riesgo de
> pérdida, incluida la pérdida total. Las señales técnicas no garantizan nada.

---

## ¿Qué es real y qué no?

- ✅ **eToro SÍ tiene API pública** (lanzada a finales de 2025) que permite
  leer cartera y **abrir/cerrar posiciones** en cuentas retail verificadas.
  - Base: `https://public-api.etoro.com/api/v1/`
  - Auth: cabeceras `x-api-key` y `x-user-key`
  - Entornos: **demo** (virtual) y **real**
- ❗ Necesitas **cuenta verificada (KYC)** y generar tus claves en
  [api-portal.etoro.com](https://api-portal.etoro.com/). Yo **no** puedo
  crear esas claves por ti: me las pasas tú por variables de entorno.
- ❗ Sobre la **"cartera de agentes" de eToro Alemania**: el flujo de aquí
  funciona contra la API estándar de eToro. Si esa modalidad expone un
  endpoint distinto, solo hay que cambiar la ruta base en `etoro_client.py`.

---

## Flujo de trabajo (3 pasos, seguro)

```
1) python market_analysis.py     →  genera  proposed_orders.json
2) revisas el JSON y pones  "approved": true  en lo que quieras operar
3) python trade_executor.py      →  ejecuta SOLO lo aprobado
```

El paso 1 no toca tu cuenta. El paso 3 respeta `DRY_RUN` y los topes.

---

## Configuración

```bash
# Credenciales (las generas en api-portal.etoro.com)
export ETORO_API_KEY="tu_api_key"
export ETORO_USER_KEY="tu_user_key"

# Seguridad (valores por defecto recomendados para empezar)
export ETORO_ENV="demo"        # demo = virtual | real = dinero real
export ETORO_DRY_RUN="1"       # 1 = simula (no envía) | 0 = ejecuta de verdad
export ETORO_MAX_ORDER_USD="500"   # tope por orden
export ETORO_CAPITAL_USD="1000"    # capital base para dimensionar pesos
```

Para operar **de verdad** (cuando ya hayas practicado en demo):
```bash
export ETORO_ENV="real"
export ETORO_DRY_RUN="0"
```

---

## Ficheros

| Fichero | Qué hace |
|---|---|
| `etoro_client.py` | Cliente de la API de eToro (cartera, balance, abrir/cerrar). DRY-RUN y demo por defecto. |
| `trade_candidates.py` | Universo **curado** de ideas (núcleo, crecimiento y "gemas"), con tesis y pesos. **Edítalo libremente.** |
| `market_analysis.py` | Cotiza en vivo (Stooq), calcula señales (SMA200, golden cross, momentum) y propone órdenes dimensionadas. |
| `trade_executor.py` | Ejecuta **solo** las órdenes con `approved: true`, resuelve `instrument_id` vía API y registra en `executed_orders.log`. |

---

## Comandos útiles

```bash
python trade_candidates.py            # ver el universo y los pesos
python market_analysis.py             # análisis + proponer compras
python market_analysis.py --all       # incluir también WATCH/AVOID
python etoro_client.py --portfolio    # ver tu cartera (requiere claves)
python trade_executor.py              # ejecutar lo aprobado (demo/dry-run)
python trade_executor.py --yes        # sin confirmación interactiva
```

---

## Señales que usa el análisis (transparentes)

- **Tendencia:** precio por encima de la media de 200 sesiones (SMA200).
- **Estructura:** SMA50 por encima de SMA200 (*golden cross*).
- **Momentum:** rentabilidad de los últimos ~6 meses.
- **Distancia a máximos de 52 semanas.**

De ahí sale un `score 0–100` y una acción: `BUY` / `WATCH` / `AVOID`.
Es deliberadamente simple y auditable: puedes ajustar los pesos en
`market_analysis.py`.
