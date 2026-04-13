from bot.signal_parser import parse_signal


def test_parse_valid_long_signal() -> None:
    msg = "BTCUSDT LONG\nEntry: 68000 - 68200\nTP: 69000\nSL: 67500"
    signal = parse_signal(msg)
    assert signal is not None
    assert signal.symbol == "BTCUSDT"
    assert signal.side == "LONG"
    assert signal.entry_low == 68000
    assert signal.entry_high == 68200


def test_parse_reject_invalid_long_sl() -> None:
    msg = "BTCUSDT LONG\nEntry: 68000\nTP: 69000\nSL: 68100"
    assert parse_signal(msg) is None
