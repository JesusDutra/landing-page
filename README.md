# Bot de trading automático: WhatsApp → Binance Futures (MVP)

Este proyecto implementa un MVP en Python para:

1. Escuchar mensajes (mock) de WhatsApp.
2. Parsear señales (`LONG/SHORT`, `Entry`, `TP`, `SL`).
3. Calcular tamaño de posición por riesgo.
4. Ejecutar órdenes en modo **paper trading** por defecto.
5. Preparar integración para ejecución real en Binance Futures.

## Estructura

- `bot/whatsapp_listener.py`: listener (mock para MVP).
- `bot/signal_parser.py`: parser de señales con regex.
- `bot/risk_manager.py`: cálculo de posición.
- `bot/executor.py`: ejecutor paper + Binance Futures.
- `bot/main.py`: orquestador del flujo completo.
- `tests/`: pruebas unitarias.

## Requisitos

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Variables de entorno

- `PAPER_TRADING=true` (default)
- `RISK_PER_TRADE=0.02`
- `LEVERAGE=5`
- `MAX_RETRIES=3`
- `ALLOW_MULTIPLE_SAME_SYMBOL=false`
- `BINANCE_API_KEY=...`
- `BINANCE_API_SECRET=...`

## Ejecutar demo

```bash
python -m bot.main
```

## Seguridad

- No se hardcodean credenciales.
- Claves sólo por variables de entorno.
- Recomendado operar en paper trading antes de pasar a real.

## Nota importante

Para conectar WhatsApp real, sustituir `MockWhatsAppListener` por una implementación real (por ejemplo, Selenium para WhatsApp Web o un puente en Node con `whatsapp-web.js`).
