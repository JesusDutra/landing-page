"""Bot de gestión de riesgo para Binance Futures.

Flujo:
1) Espera posición abierta.
2) Al avance favorable de 2%: cierra 80% y mueve SL a break-even.
3) Opcional: trailing stop del remanente.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException

from strategy_engine import PositionSnapshot, StrategyConfig, StrategyEngine, StrategyState


API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")

SYMBOL = os.getenv("BINANCE_SYMBOL", "BTCUSDT")
POLL_SECONDS = float(os.getenv("BOT_POLL_SECONDS", "2"))
TRIGGER_PCT = Decimal(os.getenv("BOT_TRIGGER_PCT", "0.02"))
PARTIAL_CLOSE_PCT = Decimal(os.getenv("BOT_PARTIAL_CLOSE_PCT", "0.80"))
DRY_RUN = os.getenv("BOT_DRY_RUN", "true").lower() == "true"

TRAILING_ENABLED = os.getenv("BOT_TRAILING_ENABLED", "true").lower() == "true"
TRAILING_GAP_PCT = Decimal(os.getenv("BOT_TRAILING_GAP_PCT", "0.005"))
TRAILING_STEP_PCT = Decimal(os.getenv("BOT_TRAILING_STEP_PCT", "0.0025"))


@dataclass
class SymbolFilters:
    step_size: Decimal
    tick_size: Decimal


@dataclass
class Position:
    symbol: str
    entry_price: Decimal
    qty: Decimal
    side: str


class RiskManagerBot:
    def __init__(self, client: Client, symbol: str) -> None:
        self.client = client
        self.symbol = symbol
        self.filters = self._load_symbol_filters()

        config = StrategyConfig(
            trigger_pct=TRIGGER_PCT,
            partial_close_pct=PARTIAL_CLOSE_PCT,
            trailing_enabled=TRAILING_ENABLED,
            trailing_gap_pct=TRAILING_GAP_PCT,
            trailing_step_pct=TRAILING_STEP_PCT,
        )
        self.engine = StrategyEngine(config)
        self.state = StrategyState()

    def _load_symbol_filters(self) -> SymbolFilters:
        info = self.client.futures_exchange_info()
        symbol_data = next(s for s in info["symbols"] if s["symbol"] == self.symbol)

        lot_filter = next(f for f in symbol_data["filters"] if f["filterType"] == "LOT_SIZE")
        price_filter = next(f for f in symbol_data["filters"] if f["filterType"] == "PRICE_FILTER")

        return SymbolFilters(
            step_size=Decimal(lot_filter["stepSize"]),
            tick_size=Decimal(price_filter["tickSize"]),
        )

    def _round_qty(self, quantity: Decimal) -> Decimal:
        step_size = self.filters.step_size
        return (quantity // step_size) * step_size

    def _round_price(self, price: Decimal) -> Decimal:
        tick_size = self.filters.tick_size
        return (price // tick_size) * tick_size

    def get_open_position(self) -> Optional[Position]:
        positions = self.client.futures_position_information(symbol=self.symbol)
        for p in positions:
            amt = Decimal(p["positionAmt"])
            if amt == 0:
                continue

            side = "LONG" if amt > 0 else "SHORT"
            return Position(
                symbol=p["symbol"],
                entry_price=Decimal(p["entryPrice"]),
                qty=abs(amt),
                side=side,
            )
        return None

    def get_mark_price(self) -> Decimal:
        data = self.client.futures_mark_price(symbol=self.symbol)
        return Decimal(data["markPrice"])

    def _close_partial(self, position: Position) -> None:
        qty_to_close = self._round_qty(position.qty * self.engine.config.partial_close_pct)
        if qty_to_close <= 0:
            print("[WARN] qty_to_close <= 0. Revisa tamaño de posición y stepSize.")
            return

        side = "SELL" if position.side == "LONG" else "BUY"
        print(f"[INFO] Cerrando parcial: {side} {qty_to_close} {position.symbol}")

        if DRY_RUN:
            return

        self.client.futures_create_order(
            symbol=position.symbol,
            side=side,
            type="MARKET",
            quantity=str(qty_to_close),
            reduceOnly=True,
        )

    def _cancel_existing_stops(self) -> None:
        open_orders = self.client.futures_get_open_orders(symbol=self.symbol)
        for order in open_orders:
            if order.get("type") in {"STOP", "STOP_MARKET"}:
                if not DRY_RUN:
                    self.client.futures_cancel_order(symbol=self.symbol, orderId=order["orderId"])

    def _place_stop_market(self, position: Position, stop_price: Decimal) -> None:
        close_side = "SELL" if position.side == "LONG" else "BUY"
        rounded_stop = self._round_price(stop_price)

        print(f"[INFO] Colocando SL {close_side} en {rounded_stop} | dry_run={DRY_RUN}")

        if not DRY_RUN:
            self.client.futures_create_order(
                symbol=position.symbol,
                side=close_side,
                type="STOP_MARKET",
                stopPrice=str(rounded_stop),
                closePosition=True,
                workingType="MARK_PRICE",
            )

        self.state.current_stop_price = rounded_stop

    def _move_to_break_even(self, position: Position) -> None:
        self._cancel_existing_stops()
        self._place_stop_market(position, position.entry_price)

    def _manage_trailing(self, position: Position, mark_price: Decimal) -> None:
        if not self.engine.config.trailing_enabled or not self.state.partial_taken:
            return

        snapshot = PositionSnapshot(entry_price=position.entry_price, side=position.side)
        self.engine.update_best_price(self.state, snapshot, mark_price)

        candidate = self.engine.candidate_trailing_stop(self.state, snapshot)
        if candidate is None:
            return

        if self.engine.should_trail(self.state, snapshot, candidate):
            print(f"[INFO] Ajuste trailing candidate={candidate}")
            self._cancel_existing_stops()
            self._place_stop_market(position, candidate)

    def run(self) -> None:
        print(
            f"[INFO] Iniciando bot {self.symbol} | DRY_RUN={DRY_RUN} | trailing={self.engine.config.trailing_enabled}"
        )

        while True:
            try:
                pos = self.get_open_position()
                if not pos:
                    StrategyEngine.reset_state(self.state)
                    time.sleep(POLL_SECONDS)
                    continue

                mark = self.get_mark_price()
                snapshot = PositionSnapshot(entry_price=pos.entry_price, side=pos.side)

                if not self.state.partial_taken and self.engine.reached_trigger(snapshot, mark):
                    self._close_partial(pos)
                    self._move_to_break_even(pos)
                    self.state.partial_taken = True
                    self.state.best_price = mark
                    print("[INFO] Gestión inicial aplicada (2% -> parcial + BE).")

                self._manage_trailing(pos, mark)
                time.sleep(POLL_SECONDS)

            except BinanceAPIException as ex:
                print(f"[ERROR] Binance API: {ex}")
                time.sleep(POLL_SECONDS)
            except Exception as ex:  # noqa: BLE001
                print(f"[ERROR] Error inesperado: {ex}")
                time.sleep(POLL_SECONDS)


def main() -> None:
    if not API_KEY or not API_SECRET:
        raise RuntimeError("Faltan BINANCE_API_KEY y BINANCE_API_SECRET.")

    client = Client(API_KEY, API_SECRET)
    bot = RiskManagerBot(client=client, symbol=SYMBOL)
    bot.run()


if __name__ == "__main__":
    main()
