# Binance Scale-Out Bot (+2% → cerrar 80% y BE)

Bot en Python para **Binance Futures (USDⓈ-M)** que implementa exactamente tu lógica:

1. Vos abrís la operación manualmente (long o short).
2. El bot detecta posición abierta (entry, tamaño y lado).
3. Espera que el precio avance **+2% a favor** (configurable).
4. Cuando llega:
   - Cierra el **80%** con orden market `reduceOnly`.
   - Cancela SLs previos tipo STOP.
   - Coloca un nuevo `STOP_MARKET` al **Break Even** (precio de entrada) para el 20% restante.

> ⚠️ Recomendado usar primero en **testnet**.

## Requisitos

- Python 3.10+
- API key de Binance Futures

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Variables de entorno

```bash
export BINANCE_API_KEY="tu_api_key"
export BINANCE_API_SECRET="tu_api_secret"

# Opcional (por defecto true)
export BINANCE_TESTNET="true"

# Opcional
export BOT_SYMBOL="BTCUSDT"
export BOT_TRIGGER_PCT="0.02"   # +2%
export BOT_CLOSE_PCT="0.80"     # 80%
export BOT_POLL_SECONDS="2"
```

## Ejecutar

```bash
python binance_scaleout_bot.py
```

## Notas importantes

- Este script está hecho para modo **one-way** (no hedge mode).
- Usa `MARK_PRICE` para evaluar trigger y para el stop de BE.
- Revisá comisiones, slippage y restricciones del símbolo (tick/step).
- No es asesoramiento financiero.


## Troubleshooting

### Error `code=-1021` (Timestamp ahead/behind)

Si ves `Timestamp for this request was ... ahead/behind`, tu reloj local está desfasado.
Este bot ahora resincroniza automáticamente el reloj con Binance al iniciar y cuando detecta ese error.

En Windows, además conviene:

1. Configuración → Hora e idioma → Fecha y hora → activar ajuste automático.
2. Sincronizar hora manualmente (`w32tm /resync` en CMD como administrador).

