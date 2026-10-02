import unittest
from math import log1p
from aquaflow.api import AquaFlowService
from aquaflow.leak.localize import Signal, rank
from aquaflow.operations.control_tower import leak_dispatch


def score(drop, acoustic, night_delta):
    return max(0, drop) * .5 + max(0, acoustic) * 1.6 + log1p(max(0, night_delta)) * 2


# Two moderate but independent sensors on P1; one stronger lone signal on P2.
# Each P1 reading alone is weaker than P2's, so overwrite/max ranking would
# put P2 first; accumulated evidence must put P1 first.
CORROBORATING = [
    Signal("s1", "P1", 2.0, 1.0, 3.0),
    Signal("s2", "P1", 1.0, 0.5, 3.0),
    Signal("s3", "P2", 4.0, 2.0, 5.0),
]
P1_TOTAL = score(2.0, 1.0, 3.0) + score(1.0, 0.5, 3.0)
P2_TOTAL = score(4.0, 2.0, 5.0)


class T(unittest.TestCase):
    def test_corroborating_sensors_accumulate(self):
        self.assertLess(score(2.0, 1.0, 3.0), P2_TOTAL)  # each P1 signal alone is weaker
        ranked = rank(CORROBORATING)
        self.assertEqual([p for p, _, _ in ranked], ["P1", "P2"])
        pipe, s, n = ranked[0]
        self.assertEqual((pipe, n), ("P1", 2))
        self.assertAlmostEqual(s, P1_TOTAL)

    def test_single_strong_signal_keeps_own_score(self):
        ranked = rank(CORROBORATING)
        pipe, s, n = ranked[1]
        self.assertEqual((pipe, n), ("P2", 1))
        self.assertAlmostEqual(s, P2_TOTAL)
        lone = rank([CORROBORATING[2]])
        self.assertEqual([p for p, _, _ in lone], ["P2"])

    def test_all_zero_signals_rank_stably(self):
        rows = [
            Signal("s1", "P9", 0.0, 0.0, 0.0),
            Signal("s2", "P1", 0.0, 0.0, 0.0),
            Signal("s3", "P5", 0.0, 0.0, 0.0),
            Signal("s1", "P5", 0.0, 0.0, 0.0),
            Signal("s3", "P5", 0.0, 0.0, 0.0),
        ]
        ranked = rank(rows)
        self.assertEqual([p for p, _, _ in ranked], ["P9", "P1", "P5"])  # first-seen order on ties
        self.assertEqual([s for _, s, _ in ranked], [0, 0, 0])
        self.assertEqual([n for _, _, n in ranked], [1, 1, 2])  # distinct sensors per pipe

    def test_negative_drop_and_night_delta_truncated(self):
        ranked = rank([Signal("s1", "P1", -5.0, 2.0, -3.0), Signal("s2", "P2", -1.0, -0.5, -2.0)])
        self.assertEqual([p for p, _, _ in ranked], ["P1", "P2"])
        self.assertAlmostEqual(ranked[0][1], 3.2)  # only the acoustic term survives
        self.assertEqual(ranked[1][1], 0)

    def test_workflow_accumulates_end_to_end(self):
        payload = {"signals": [vars(s) for s in CORROBORATING]}
        result = AquaFlowService().run_workflow("leak_localization", payload)
        self.assertEqual(result["decision"], "inspect")
        self.assertEqual([v[0] for v in result["value"]], ["P1", "P2"])
        self.assertAlmostEqual(result["value"][0][1], P1_TOTAL)  # night_delta reaches ranking
        self.assertEqual([v[2] for v in result["value"]], [2, 1])
        self.assertEqual(result["evidence"]["sensors"], 3)

    def test_dispatch_follows_accumulated_ranking(self):
        self.assertEqual(leak_dispatch(CORROBORATING, 1, 5.0), ["P1"])
        self.assertEqual(leak_dispatch(CORROBORATING, 5, 0.0), ["P1", "P2"])


if __name__ == "__main__":
    unittest.main()
