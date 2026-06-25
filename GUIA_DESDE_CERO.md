# 🚀 Guía desde cero (explicada fácil)

Esta es la lista de pasos para usar tu robot de inversión **Kubabot**, contada
como si se la explicáramos a un niño de 9 años. Sigue las casillas en orden. ✅

> 🧸 **La idea en una frase:** tenemos unos "robots" (programas) que miran la
> bolsa, te proponen qué comprar, y compran **solo cuando tú dices que sí**.
> Tu dinero nunca se mueve solo.

---

## 🍪 Antes de empezar: ¿qué es cada cosa?

- **eToro** = una app para comprar trocitos de empresas (como cromos que suben
  y bajan de precio).
- **API key** = una "llave secreta" que deja a nuestros robots entrar en tu
  cuenta de eToro. Hay **dos llaves**: `x-api-key` y `x-user-key`.
- **Demo** = jugar con dinero de mentira para practicar. **Real** = dinero de verdad.
- **Stop-loss** = un paracaídas: si algo baja mucho, vende solo para no perder más.
- **Take-profit** = una meta: si algo sube mucho, vende solo para ganar el premio.

---

## ✅ Lista de pasos (del 1 al 10)

### 1. Tener la cuenta de eToro lista
- [ ] Entra en tu cuenta de eToro y comprueba que está **verificada** (que ya
      enviaste tu DNI y te dijeron "ok"). Sin esto, las llaves no funcionan.
- [ ] Mira que tu cartera **kubabot-rkuhwqhq** tiene tus **200 $**.

### 2. Hacer las llaves secretas (API keys)
- [ ] Entra en 👉 **https://api-portal.etoro.com/** con tu cuenta.
- [ ] Si ya pegaste una llave en un chat, **bórrala/regénerala** (botón
      *Regenerate* o *Revoke*). Es como cambiar la cerradura si perdiste la llave.
- [ ] Crea una llave **nueva**. Te dará dos códigos: `x-api-key` y `x-user-key`.
- [ ] **Cópialos y guárdalos** en un sitio privado (a veces solo se ven una vez).
      ❌ Nunca los pongas en un chat ni en una foto.

### 3. Traerte los robots a tu ordenador
- [ ] Abre la app **Terminal** (o "Símbolo del sistema" en Windows).
- [ ] Escribe esto y pulsa Enter (descarga los robots):
```bash
git clone https://github.com/Robkuba/aschenbrenner-tracker.git
cd aschenbrenner-tracker
git checkout claude/etoro-agent-portfolio-2fcabz
```

### 4. Decirle al ordenador tus llaves (sin que nadie las vea)
- [ ] Escribe esto, cambiando los `...` por tus códigos de verdad:
```bash
export ETORO_API_KEY="...tu_x_api_key..."
export ETORO_USER_KEY="...tu_x_user_key..."
```

### 5. Practicar primero con dinero de MENTIRA (demo)
- [ ] Pon el modo de práctica:
```bash
export ETORO_ENV="demo"
export ETORO_DRY_RUN="1"
```
- [ ] Haz una prueba "en seco" (no compra nada, solo enseña qué haría):
```bash
PROPOSED_FILE=orders_kubabot_200.json python3 trade_executor.py
```
- [ ] Si ves la lista de las 12 compras con sus paracaídas (SL) y metas (TP),
      ¡vas genial! 🎉

### 6. Comprar de mentira de verdad (en demo)
- [ ] Quita la simulación para que compre en tu cuenta **demo**:
```bash
export ETORO_DRY_RUN="0"
PROPOSED_FILE=orders_kubabot_200.json python3 trade_executor.py
```
- [ ] Abre eToro en modo **Virtual** y comprueba que aparecen las 12 posiciones.

### 7. Comprar de VERDAD (solo cuando estés seguro)
- [ ] Cambia a dinero real:
```bash
export ETORO_ENV="real"
export ETORO_DRY_RUN="0"
PROPOSED_FILE=orders_kubabot_200.json python3 trade_executor.py
```
- [ ] Te pedirá escribir **SI** para confirmar. Solo entonces compra de verdad.

### 8. Poner los robots automáticos (avisos por WhatsApp)
En GitHub: **Settings → Secrets and variables → Actions**.
- [ ] En *Secrets* añade: `ETORO_API_KEY`, `ETORO_USER_KEY`, `CALLMEBOT_PHONE`,
      `CALLMEBOT_APIKEY`.
- [ ] En *Variables* añade: `ETORO_ENV` = `real` y `REBALANCE_THRESHOLD_PCT` = `5`.
- [ ] Listo: cada **lunes** te avisa si algo se desvió, y cada **viernes** te
      manda el resumen con cuánto llevas ganado o perdido. 📲

### 9. Cómo arreglar la cartera si se desordena (rebalanceo)
- [ ] Cuando quieras, mira las desviaciones:
```bash
python3 rebalance.py
```
- [ ] Si propone compras de ajuste, ábrelas en `rebalance_orders.json`, cambia
      `"approved": false` por `true` en las que quieras, y ejecútalas:
```bash
PROPOSED_FILE=rebalance_orders.json python3 trade_executor.py
```

### 10. Reglas de oro 🏆
- [ ] **Siempre demo primero.** Practicar no cuesta nada.
- [ ] **Nunca compartas tus llaves** en chats ni fotos.
- [ ] Esto son **ideas + señales**, no consejos mágicos: el dinero puede bajar.
      Invierte solo lo que no te importe arriesgar.

---

## 🧩 ¿Qué hace cada robot? (chuleta)

| Robot (archivo) | Lo que hace, fácil |
|---|---|
| `etoro_client.py` | La "mano" que habla con eToro. Por seguridad, de mentira por defecto. |
| `trade_candidates.py` | La lista de empresas buenas que vigilamos. |
| `market_analysis.py` | El "explorador" que mira la bolsa y dice qué comprar. |
| `orders_kubabot_200.json` | Tu plan: las 12 compras, con paracaídas y metas. |
| `trade_executor.py` | El "comprador" que solo actúa con tu permiso. |
| `rebalance.py` | El "ordenador" que avisa si la cartera se desordena. |
| `portfolio_report.py` | El "cartero" que te manda el resumen cada semana. |

¡Y ya está! Sigue las casillas de arriba sin saltarte ninguna y lo harás genial. 🌟
