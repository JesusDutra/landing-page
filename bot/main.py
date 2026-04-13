from __future__ import annotations

import hashlib
import logging

from .config import Settings
from .executor import BinanceFuturesExecutor, PaperExecutor
from .models import TradeOrder
from .risk_manager import SymbolConstraints, calculate_position_size
from .signal_parser import parse_signal
from .whatsapp_listener import MockWhatsAppListener

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class TradingBot:
    def __init__(self, settings: Settings, capital: float):
        self.settings = settings
        self.capital = capital
        self.seen_signals: set[str] = set()
        self.open_symbols: set[str] = set()

        if settings.paper_trading:
            self.executor = PaperExecutor()
        else:
            self.executor = BinanceFuturesExecutor(
                api_key=settings.binance_api_key,
                api_secret=settings.binance_api_secret,
                max_retries=settings.max_retries,
            )

    def process_message(self, message: str) -> None:
        signal = parse_signal(message)
        if signal is None:
            logger.info("Message ignored (not a valid signal)")
            return

        fingerprint = hashlib.sha256(signal.raw_message.encode()).hexdigest()
        if fingerprint in self.seen_signals:
            logger.info("Duplicate signal ignored: %s", signal.symbol)
            return

        if (not self.settings.allow_multiple_same_symbol) and signal.symbol in self.open_symbols:
            logger.info("Signal ignored, already open position for %s", signal.symbol)
            return

        constraints = SymbolConstraints(qty_precision=3, min_qty=0.001)
        try:
            qty = calculate_position_size(
                capital=self.capital,
                risk_per_trade=self.settings.risk_per_trade,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                leverage=self.settings.leverage,
                constraints=constraints,
            )
        except ValueError as exc:
            logger.warning("Risk manager rejected signal: %s", exc)
            return

        order = TradeOrder(
            symbol=signal.symbol,
            side=signal.side,
            quantity=qty,
            entry_price=signal.entry_price,
            take_profit=signal.take_profit,
            stop_loss=signal.stop_loss,
            leverage=self.settings.leverage,
            paper=self.settings.paper_trading,
        )

        result = self.executor.place_order(order)
        self.seen_signals.add(fingerprint)

        if result.ok:
            self.open_symbols.add(signal.symbol)
            logger.info("Order placed successfully: %s", result)
        else:
            logger.error("Order failed: %s", result.details)


def run_demo() -> None:
    settings = Settings()
    bot = TradingBot(settings=settings, capital=1000)
    listener = MockWhatsAppListener(
        messages=[
            "BTCUSDT LONG\nEntry: 68000 - 68200\nTP: 69000\nSL: 67500",
            "ETHUSDT SHORT\nEntry: 3500\nTP: 3400\nSL: 3560",
        ]
    )

    for msg in listener.stream_messages():
        bot.process_message(msg)


if __name__ == "__main__":
    run_demo()
