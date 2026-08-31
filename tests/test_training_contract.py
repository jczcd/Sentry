from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "training" / "isaac_lab"))

import contract  # noqa: E402


class TrainingContractTest(unittest.TestCase):
    def test_action_decode(self) -> None:
        raw = [0.5, -0.25, 0.0] + [0.0] * 6 + [3.0]
        action = contract.decode_continuous_heads(raw)
        self.assertAlmostEqual(action.goal_dx_m, 3.75)
        self.assertAlmostEqual(action.goal_dy_m, -2.0)
        self.assertAlmostEqual(action.weapons_free_probability, 0.5)
        self.assertEqual(action.target_slot, contract.NO_TARGET)
        self.assertAlmostEqual(sum(action.target_probabilities), 1.0)

    def test_observation_contract(self) -> None:
        values = contract.validate_observation([0.0] * 161)
        self.assertEqual(len(values), 161)
        with self.assertRaises(ValueError):
            contract.validate_observation([0.0] * 160)
        invalid = [0.0] * 161
        invalid[4] = math.nan
        with self.assertRaises(ValueError):
            contract.validate_observation(invalid)


if __name__ == "__main__":
    unittest.main()
