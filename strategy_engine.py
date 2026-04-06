"""Motor puro de estrategia para gestionar riesgo sin depender del exchange."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class StrategyConfig:
    trigger_pct: Decimal
    partial_close_pct: Decimal
    trailing_enabled: bool
    trailing_gap_pct: Decimal
    trailing_step_pct: Decimal


@dataclass
class StrategyState:
    partial_taken: bool = False
    current_stop_price: Optional[Decimal] = None
    best_price: Optional[Decimal] = None


@dataclass
class PositionSnapshot:
    entry_price: Decimal
    side: str  # LONG | SHORT


class StrategyEngine:
    def __init__(self, config: StrategyConfig) -> None:
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        if self.config.trigger_pct <= 0:
            raise ValueError("trigger_pct debe ser > 0")
        if not (Decimal("0") < self.config.partial_close_pct <= Decimal("1")):
            raise ValueError("partial_close_pct debe estar en (0, 1]")
        if self.config.trailing_gap_pct <= 0:
            raise ValueError("trailing_gap_pct debe ser > 0")
        if self.config.trailing_step_pct <= 0:
            raise ValueError("trailing_step_pct debe ser > 0")

    def reached_trigger(self, position: PositionSnapshot, mark_price: Decimal) -> bool:
        if position.side == "LONG":
            return mark_price >= position.entry_price * (Decimal("1") + self.config.trigger_pct)
        return mark_price <= position.entry_price * (Decimal("1") - self.config.trigger_pct)

    def update_best_price(
        self, state: StrategyState, position: PositionSnapshot, mark_price: Decimal
    ) -> None:
        if state.best_price is None:
            state.best_price = mark_price
            return

        if position.side == "LONG":
            state.best_price = max(state.best_price, mark_price)
        else:
            state.best_price = min(state.best_price, mark_price)

    def candidate_trailing_stop(
        self, state: StrategyState, position: PositionSnapshot
    ) -> Optional[Decimal]:
        if state.best_price is None:
            return None

        if position.side == "LONG":
            return state.best_price * (Decimal("1") - self.config.trailing_gap_pct)
        return state.best_price * (Decimal("1") + self.config.trailing_gap_pct)

    def should_trail(
        self, state: StrategyState, position: PositionSnapshot, candidate_stop: Decimal
    ) -> bool:
        if state.current_stop_price is None:
            return True

        min_move = position.entry_price * self.config.trailing_step_pct

        if position.side == "LONG":
            return candidate_stop > state.current_stop_price + min_move
        return candidate_stop < state.current_stop_price - min_move

    @staticmethod
    def reset_state(state: StrategyState) -> None:
        state.partial_taken = False
        state.current_stop_price = None
        state.best_price = None
