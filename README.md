# Binance Futures Risk Manager Bot (2:1 + parcial + break-even + trailing)

Si quieres quitar el factor emocional, este enfoque es el más sólido: separar la **lógica de riesgo** del **conector de exchange** y testear esa lógica de forma automática.

## Qué hace

Cuando detecta una posición abierta en `BINANCE_SYMBOL`:

1. Espera a que el precio avance **2%** a favor de la posición.
2. Cierra **80%** de la posición (parcial).
3. Mueve el **Stop Loss a precio de entrada** (break-even).
4. Deja correr el 20%.
5. Si trailing está activo, reajusta el SL del remanente con distancia configurable al mejor precio.

## Arquitectura (mejor práctica aplicada)

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

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecución (simulación)

```bash
export BINANCE_API_KEY="tu_api_key"
export BINANCE_API_SECRET="tu_api_secret"
export BINANCE_SYMBOL="BTCUSDT"
export BOT_DRY_RUN="true"
python risk_manager_bot.py
```

## Tests

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

## Recomendación fuerte antes de real

1. Ejecuta mínimo 1-2 semanas en `BOT_DRY_RUN=true`.
2. Revisa logs de cada ajuste de SL.
3. Luego prueba con tamaño mínimo.
4. Solo después escala riesgo.

## Nota

Automatizar futuros implica riesgo alto (slippage, latencia, gaps, liquidación). Usa este bot como framework inicial y adapta tus reglas exactas.


## ¿Funciona para LONG y SHORT?

Sí. El motor y el bot soportan ambos lados:

- **LONG**: trigger cuando el precio sube desde entrada, parcial con `SELL`, SL/trailing por debajo del mejor precio.
- **SHORT**: trigger cuando el precio baja desde entrada, parcial con `BUY`, SL/trailing por encima del mejor precio.

Puedes verlo en la lógica y también en los tests unitarios para ambos casos.
