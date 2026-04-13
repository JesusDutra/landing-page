import pytest

from bot.risk_manager import SymbolConstraints, calculate_position_size


def test_calculate_position_size() -> None:
    qty = calculate_position_size(
        capital=1000,
        risk_per_trade=0.02,
        entry_price=100,
        stop_loss=95,
        leverage=5,
        constraints=SymbolConstraints(qty_precision=3, min_qty=0.001),
    )
    assert qty == 20.0


def test_calculate_position_size_below_min_qty() -> None:
    with pytest.raises(ValueError):
        calculate_position_size(
            capital=10,
            risk_per_trade=0.01,
            entry_price=1000,
            stop_loss=999,
            leverage=1,
            constraints=SymbolConstraints(qty_precision=3, min_qty=0.5),
        )
