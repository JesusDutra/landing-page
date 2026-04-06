import unittest
from decimal import Decimal

from strategy_engine import PositionSnapshot, StrategyConfig, StrategyEngine, StrategyState


class StrategyEngineTests(unittest.TestCase):
    def make_engine(self) -> StrategyEngine:
        cfg = StrategyConfig(
            trigger_pct=Decimal("0.02"),
            partial_close_pct=Decimal("0.8"),
            trailing_enabled=True,
            trailing_gap_pct=Decimal("0.005"),
            trailing_step_pct=Decimal("0.0025"),
        )
        return StrategyEngine(cfg)

    def test_trigger_long_and_short(self) -> None:
        eng = self.make_engine()

        long_pos = PositionSnapshot(entry_price=Decimal("100"), side="LONG")
        self.assertTrue(eng.reached_trigger(long_pos, Decimal("102")))
        self.assertFalse(eng.reached_trigger(long_pos, Decimal("101.99")))

        short_pos = PositionSnapshot(entry_price=Decimal("100"), side="SHORT")
        self.assertTrue(eng.reached_trigger(short_pos, Decimal("98")))
        self.assertFalse(eng.reached_trigger(short_pos, Decimal("98.01")))

    def test_best_price_and_candidate_stop_long(self) -> None:
        eng = self.make_engine()
        state = StrategyState(partial_taken=True)
        pos = PositionSnapshot(entry_price=Decimal("100"), side="LONG")

        eng.update_best_price(state, pos, Decimal("103"))
        eng.update_best_price(state, pos, Decimal("104"))
        eng.update_best_price(state, pos, Decimal("103.5"))

        self.assertEqual(state.best_price, Decimal("104"))
        self.assertEqual(eng.candidate_trailing_stop(state, pos), Decimal("103.480"))


    def test_best_price_and_candidate_stop_short(self) -> None:
        eng = self.make_engine()
        state = StrategyState(partial_taken=True)
        pos = PositionSnapshot(entry_price=Decimal("100"), side="SHORT")

        eng.update_best_price(state, pos, Decimal("97"))
        eng.update_best_price(state, pos, Decimal("96"))
        eng.update_best_price(state, pos, Decimal("96.8"))

        self.assertEqual(state.best_price, Decimal("96"))
        self.assertEqual(eng.candidate_trailing_stop(state, pos), Decimal("96.480"))

    def test_should_trail_step_filter(self) -> None:
        eng = self.make_engine()
        pos = PositionSnapshot(entry_price=Decimal("100"), side="LONG")

        state = StrategyState(current_stop_price=Decimal("102"))
        self.assertFalse(eng.should_trail(state, pos, Decimal("102.20")))
        self.assertTrue(eng.should_trail(state, pos, Decimal("102.30")))


    def test_should_trail_step_filter_short(self) -> None:
        eng = self.make_engine()
        pos = PositionSnapshot(entry_price=Decimal("100"), side="SHORT")

        state = StrategyState(current_stop_price=Decimal("98"))
        self.assertFalse(eng.should_trail(state, pos, Decimal("97.80")))
        self.assertTrue(eng.should_trail(state, pos, Decimal("97.70")))

    def test_reset_state(self) -> None:
        state = StrategyState(
            partial_taken=True,
            current_stop_price=Decimal("100"),
            best_price=Decimal("110"),
        )
        StrategyEngine.reset_state(state)

        self.assertFalse(state.partial_taken)
        self.assertIsNone(state.current_stop_price)
        self.assertIsNone(state.best_price)


if __name__ == "__main__":
    unittest.main()
