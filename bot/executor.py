from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

from .models import ExecutionResult, TradeOrder

logger = logging.getLogger(__name__)


class TradeExecutor(ABC):
    @abstractmethod
    def place_order(self, order: TradeOrder) -> ExecutionResult:
        raise NotImplementedError


class PaperExecutor(TradeExecutor):
    def place_order(self, order: TradeOrder) -> ExecutionResult:
        logger.info("[PAPER] Executing simulated order: %s", order)
        return ExecutionResult(ok=True, order_id=f"paper-{int(time.time())}", details="simulated")


class BinanceFuturesExecutor(TradeExecutor):
    def __init__(self, api_key: str, api_secret: str, max_retries: int = 3):
        from binance.um_futures import UMFutures  # type: ignore

        self.client = UMFutures(key=api_key, secret=api_secret)
        self.max_retries = max_retries

    def place_order(self, order: TradeOrder) -> ExecutionResult:
        side = "BUY" if order.side == "LONG" else "SELL"
        opposite = "SELL" if side == "BUY" else "BUY"

        for attempt in range(1, self.max_retries + 1):
            try:
                placed = self.client.new_order(
                    symbol=order.symbol,
                    side=side,
                    type="MARKET",
                    quantity=order.quantity,
                )
                self.client.new_order(
                    symbol=order.symbol,
                    side=opposite,
                    type="STOP_MARKET",
                    stopPrice=order.stop_loss,
                    closePosition="true",
                    workingType="MARK_PRICE",
                )
                self.client.new_order(
                    symbol=order.symbol,
                    side=opposite,
                    type="TAKE_PROFIT_MARKET",
                    stopPrice=order.take_profit,
                    closePosition="true",
                    workingType="MARK_PRICE",
                )
                return ExecutionResult(ok=True, order_id=str(placed.get("orderId")), details="live")
            except Exception as exc:  # noqa: BLE001
                logger.exception("Binance order failed (attempt %s/%s)", attempt, self.max_retries)
                if attempt == self.max_retries:
                    return ExecutionResult(ok=False, order_id=None, details=str(exc))
                time.sleep(1)

        return ExecutionResult(ok=False, order_id=None, details="unknown error")
