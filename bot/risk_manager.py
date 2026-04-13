from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolConstraints:
    qty_precision: int
    min_qty: float


def calculate_position_size(
    capital: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss: float,
    leverage: int,
    constraints: SymbolConstraints,
) -> float:
    risk_amount = capital * risk_per_trade
    sl_distance = abs(entry_price - stop_loss)
    if sl_distance <= 0:
        raise ValueError("Stop loss distance must be greater than zero")

    raw_qty = (risk_amount / sl_distance) * leverage
    factor = 10 ** constraints.qty_precision
    adjusted_qty = int(raw_qty * factor) / factor

    if adjusted_qty < constraints.min_qty:
        raise ValueError(
            f"Calculated quantity {adjusted_qty} is below exchange minimum {constraints.min_qty}"
        )

    return adjusted_qty
