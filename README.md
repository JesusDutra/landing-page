# Binance Futures Risk Manager Bot (2:1 + parcial + break-even + trailing)

Si quieres quitar el factor emocional, este enfoque es el más sólido: separar la **lógica de riesgo** del **conector de exchange** y testear esa lógica de forma automática.

## Qué hace

Cuando detecta una posición abierta en `BINANCE_SYMBOL`:

1. Espera a que el precio avance **2%** a favor de la posición.
2. Cierra **80%** de la posición (parcial).
3. Mueve el **Stop Loss a precio de entrada** (break-even).
4. Deja correr el 20%.
5. Si trailing está activo, reajusta el SL del remanente con distancia configurable al mejor precio.

## Arquitectura

- `risk_manager_bot.py`: integración con Binance (órdenes, polling, redondeos por filtros).
- `strategy_engine.py`: motor puro de estrategia (sin API externa), fácil de probar.
- `tests/test_strategy_engine.py`: pruebas unitarias de trigger, trailing y reset de estado.

## Configuración

Variables de entorno:

- `BINANCE_API_KEY`
- `BINANCE_API_SECRET`
- `BINANCE_SYMBOL` (default: `BTCUSDT`)
- `BOT_TRIGGER_PCT` (default: `0.02` = 2%)
- `BOT_PARTIAL_CLOSE_PCT` (default: `0.80` = 80%)
- `BOT_POLL_SECONDS` (default: `2`)
- `BOT_DRY_RUN` (default: `true`)
- `BOT_TRAILING_ENABLED` (default: `true`)
- `BOT_TRAILING_GAP_PCT` (default: `0.005` = 0.5%)
- `BOT_TRAILING_STEP_PCT` (default: `0.0025` = 0.25%)

---

## Guía rápida (correcta) para ejecutarlo

### 1) Preparar API de Binance

1. Crea una API Key para **Futures**.
2. Activa permisos de trading (sin retiro).
3. Si puedes, comienza en testnet o con monto mínimo.

### 2) Preparar entorno local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con tus claves.

### 4) Cargar variables

```bash
set -a
source .env
set +a
```

### 5) Verificar que la lógica está sana

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

### 6) Ejecutar en modo seguro (simulación)

Asegúrate de tener:

```bash
export BOT_DRY_RUN=true
```

Luego corre:

```bash
python risk_manager_bot.py
```

### 7) Pasar a real (solo cuando valides logs)

```bash
export BOT_DRY_RUN=false
python risk_manager_bot.py
```

---

## ¿Funciona para LONG y SHORT?

Sí. El motor y el bot soportan ambos lados:

- **LONG**: trigger cuando el precio sube desde entrada, parcial con `SELL`, SL/trailing por debajo del mejor precio.
- **SHORT**: trigger cuando el precio baja desde entrada, parcial con `BUY`, SL/trailing por encima del mejor precio.

## Checklist antes de real

- [ ] El test unitario pasa.
- [ ] Revisaste logs en `DRY_RUN=true` varios días.
- [ ] Verificaste redondeos (`tickSize` y `stepSize`) en tu símbolo.
- [ ] Empezaste con tamaño mínimo.

## Nota

Automatizar futuros implica riesgo alto (slippage, latencia, gaps, liquidación). Usa este bot como framework inicial y adapta tus reglas exactas.
