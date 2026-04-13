from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    risk_per_trade: float = float(os.getenv("RISK_PER_TRADE", "0.02"))
    leverage: int = int(os.getenv("LEVERAGE", "5"))
    paper_trading: bool = os.getenv("PAPER_TRADING", "true").lower() == "true"
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    allow_multiple_same_symbol: bool = os.getenv("ALLOW_MULTIPLE_SAME_SYMBOL", "false").lower() == "true"

    binance_api_key: str = os.getenv("BINANCE_API_KEY", "")
    binance_api_secret: str = os.getenv("BINANCE_API_SECRET", "")
