from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TradeSignal:
    symbol: str
    side: str  # LONG | SHORT
    entry_low: float
    entry_high: float
    take_profit: float
    stop_loss: float
    raw_message: str

    @property
    def entry_price(self) -> float:
        return (self.entry_low + self.entry_high) / 2


@dataclass(frozen=True)
class TradeOrder:
    symbol: str
    side: str
    quantity: float
    entry_price: float
    take_profit: float
    stop_loss: float
    leverage: int
    paper: bool


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    order_id: Optional[str]
    details: str
