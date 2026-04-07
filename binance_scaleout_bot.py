#!/usr/bin/env python3
"""Bot de gestión de posición para Binance Futures (USDⓈ-M).

Lógica:
1) El usuario abre una operación manualmente (long o short).
2) El bot detecta precio de entrada, tamaño de posición y SL actual.
3) Espera +2% a favor (configurable).
4) Al alcanzarlo:
   - Cierra el 80% (reduceOnly) con orden MARKET.
   - Mueve SL a Break Even (precio de entrada) para el 20% restante.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Tuple

from binance.client import Client
from binance.exceptions import BinanceAPIException


@dataclass
class BotConfig:
    symbol: str
    trigger_pct: Decimal = Decimal("0.02")
    close_pct: Decimal = Decimal("0.80")
    poll_seconds: int = 2


@dataclass
class PositionState:
    side: str  # "LONG" | "SHORT"
    qty: Decimal
    entry_price: Decimal


class BinanceScaleoutBot:
    def __init__(self, client: Client, config: BotConfig):
        self.client = client
        self.config = config
        self.qty_step, self.price_tick = self._load_symbol_filters(config.symbol)

    def _load_symbol_filters(self, symbol: str) -> Tuple[Decimal, Decimal]:
        info = self.client.futures_exchange_info()
        for s in info["symbols"]:
            if s["symbol"] == symbol:
                lot_step = next(f for f in s["filters"] if f["filterType"] == "LOT_SIZE")["stepSize"]
                tick_size = next(f for f in s["filters"] if f["filterType"] == "PRICE_FILTER")["tickSize"]
                return Decimal(lot_step), Decimal(tick_size)
        raise ValueError(f"No se encontró el símbolo {symbol} en exchange info")

    def _quantize_qty(self, qty: Decimal) -> Decimal:
        precision = abs(self.qty_step.as_tuple().exponent)
        stepped = (qty / self.qty_step).to_integral_value(rounding=ROUND_DOWN) * self.qty_step
        return stepped.quantize(Decimal(10) ** -precision)

    def _quantize_price(self, price: Decimal) -> Decimal:
        precision = abs(self.price_tick.as_tuple().exponent)
        stepped = (price / self.price_tick).to_integral_value(rounding=ROUND_DOWN) * self.price_tick
        return stepped.quantize(Decimal(10) ** -precision)

    def read_position(self) -> Optional[PositionState]:
        risk = self.client.futures_position_information(symbol=self.config.symbol)
        # En modo one-way suele venir una sola fila utilizable.
        for row in risk:
            amt = Decimal(row["positionAmt"])
            entry = Decimal(row["entryPrice"])
            if amt == 0:
                continue
            side = "LONG" if amt > 0 else "SHORT"
            return PositionState(side=side, qty=abs(amt), entry_price=entry)
        return None

    def current_mark_price(self) -> Decimal:
        data = self.client.futures_mark_price(symbol=self.config.symbol)
        return Decimal(data["markPrice"])

    def unrealized_pct(self, position: PositionState, mark: Decimal) -> Decimal:
        if position.side == "LONG":
            return (mark - position.entry_price) / position.entry_price
        return (position.entry_price - mark) / position.entry_price

    def _cancel_existing_stop_orders(self) -> None:
        orders = self.client.futures_get_open_orders(symbol=self.config.symbol)
        for o in orders:
            if o.get("type") in {"STOP", "STOP_MARKET"}:
                self.client.futures_cancel_order(symbol=self.config.symbol, orderId=o["orderId"])

    def _place_market_reduce(self, position: PositionState, close_qty: Decimal) -> None:
        side = "SELL" if position.side == "LONG" else "BUY"
        self.client.futures_create_order(
            symbol=self.config.symbol,
            side=side,
            type="MARKET",
            quantity=str(close_qty),
            reduceOnly="true",
        )

    def _place_break_even_stop(self, position: PositionState, remaining_qty: Decimal) -> None:
        stop_side = "SELL" if position.side == "LONG" else "BUY"
        stop_price = self._quantize_price(position.entry_price)
        self.client.futures_create_order(
            symbol=self.config.symbol,
            side=stop_side,
            type="STOP_MARKET",
            stopPrice=str(stop_price),
            closePosition="false",
            quantity=str(remaining_qty),
            reduceOnly="true",
            workingType="MARK_PRICE",
        )

    def run(self) -> None:
        print(f"▶ Bot iniciado para {self.config.symbol}. Esperando posición abierta...")
        while True:
            try:
                position = self.read_position()
                if not position:
                    time.sleep(self.config.poll_seconds)
                    continue

                print(
                    f"Posición detectada: {position.side} qty={position.qty} entry={position.entry_price}"
                )

                target_reached = False
                while not target_reached:
                    pos_check = self.read_position()
                    if not pos_check:
                        print("Posición cerrada manualmente antes del trigger. Reiniciando espera...")
                        break

                    mark = self.current_mark_price()
                    pnl_pct = self.unrealized_pct(pos_check, mark)
                    print(f"Mark={mark} | PnL%={pnl_pct * Decimal('100'):.3f}%")

                    if pnl_pct >= self.config.trigger_pct:
                        target_reached = True
                        close_qty = self._quantize_qty(pos_check.qty * self.config.close_pct)
                        if close_qty <= 0:
                            print("Cantidad calculada para cierre parcial es 0. No se ejecuta.")
                            break

                        remaining_qty = self._quantize_qty(pos_check.qty - close_qty)
                        if remaining_qty <= 0:
                            print("No queda remanente tras cierre parcial; se cancela BE.")
                            break

                        print(
                            f"✅ Trigger alcanzado (+{self.config.trigger_pct * 100}%). "
                            f"Cerrando {close_qty} y moviendo SL a BE para {remaining_qty}."
                        )

                        self._place_market_reduce(pos_check, close_qty)
                        self._cancel_existing_stop_orders()
                        self._place_break_even_stop(pos_check, remaining_qty)
                        print("✅ Gestión aplicada. Esperando nueva operación manual...")
                        break

                    time.sleep(self.config.poll_seconds)

            except BinanceAPIException as e:
                print(f"Error API Binance: {e.message} (code={e.code})")
                time.sleep(max(self.config.poll_seconds, 3))
            except Exception as e:  # noqa: BLE001
                print(f"Error inesperado: {e}")
                time.sleep(max(self.config.poll_seconds, 3))


def build_client() -> Client:
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    use_testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

    if not api_key or not api_secret:
        raise RuntimeError("Faltan BINANCE_API_KEY y/o BINANCE_API_SECRET en variables de entorno")

    client = Client(api_key, api_secret)
    if use_testnet:
        client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"
    return client


def main() -> None:
    symbol = os.getenv("BOT_SYMBOL", "BTCUSDT").upper()
    trigger = Decimal(os.getenv("BOT_TRIGGER_PCT", "0.02"))
    close_pct = Decimal(os.getenv("BOT_CLOSE_PCT", "0.80"))
    poll = int(os.getenv("BOT_POLL_SECONDS", "2"))

    if close_pct <= 0 or close_pct >= 1:
        raise ValueError("BOT_CLOSE_PCT debe estar entre 0 y 1 (ejemplo: 0.80)")

    cfg = BotConfig(symbol=symbol, trigger_pct=trigger, close_pct=close_pct, poll_seconds=poll)
    bot = BinanceScaleoutBot(build_client(), cfg)
    bot.run()


if __name__ == "__main__":
    main()
