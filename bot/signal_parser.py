from __future__ import annotations

import re
from typing import Optional

from .models import TradeSignal

SIGNAL_PATTERN = re.compile(
    r"(?P<symbol>[A-Z]{3,20}USDT)\s+(?P<side>LONG|SHORT).*?"
    r"Entry\s*:\s*(?P<entry_low>\d+(?:\.\d+)?)\s*(?:-|to)?\s*(?P<entry_high>\d+(?:\.\d+)?)?.*?"
    r"TP\s*:\s*(?P<tp>\d+(?:\.\d+)?).*?"
    r"SL\s*:\s*(?P<sl>\d+(?:\.\d+)?)",
    flags=re.IGNORECASE | re.DOTALL,
)


def parse_signal(message: str) -> Optional[TradeSignal]:
    match = SIGNAL_PATTERN.search(message.strip())
    if not match:
        return None

    symbol = match.group("symbol").upper()
    side = match.group("side").upper()
    entry_low = float(match.group("entry_low"))
    entry_high_raw = match.group("entry_high")
    entry_high = float(entry_high_raw) if entry_high_raw else entry_low
    tp = float(match.group("tp"))
    sl = float(match.group("sl"))

    if side == "LONG" and sl >= entry_low:
        return None
    if side == "SHORT" and sl <= entry_low:
        return None

    return TradeSignal(
        symbol=symbol,
        side=side,
        entry_low=min(entry_low, entry_high),
        entry_high=max(entry_low, entry_high),
        take_profit=tp,
        stop_loss=sl,
        raw_message=message,
    )
