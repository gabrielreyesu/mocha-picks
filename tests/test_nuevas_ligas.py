import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import numpy as np

from kalshi_intl import ligas
from kalshi_intl.data import GROUPS


class TestNuevasLigas(unittest.TestCase):
    def test_publishable_rules(self):
        self.assertTrue(ligas.publishable("esp.2", 0, 0))                      # liga validada
        self.assertFalse(ligas.publishable("usa.1", 50, 50))                   # no pasó la validación
        self.assertFalse(ligas.publishable("eng.fa", 50, 50))                  # copa no validada
        ligas.PUBLICAR.add("eng.fa")
        try:
            self.assertFalse(ligas.publishable("eng.fa", 50, 3))               # copa: equipo sin historial suficiente
            self.assertTrue(ligas.publishable("eng.fa", 12, 10))
        finally:
            ligas.PUBLICAR.discard("eng.fa")

    def test_market_only_never_uses_model(self):
        p, src = ligas.market_only([0.5, 0.3, 0.3], [0.5, 0.25, 0.25])
        self.assertEqual(src, "casas"); self.assertAlmostEqual(sum(p), 1)
        p, src = ligas.market_only([0.5, 0.3, 0.3], None)
        self.assertEqual(src, "Kalshi"); self.assertAlmostEqual(p[0], 0.5 / 1.1)
        p, src = ligas.market_only(None, [None, None, None])
        self.assertIsNone(p)

    def test_groups_do_not_touch_existing(self):
        self.assertNotIn("ligas", GROUPS["clubes"]["target"])
        self.assertTrue(set(ligas.PUBLICAR) <= set(GROUPS["ligas"]["target"]))
        self.assertTrue(set(GROUPS["ligas"]["league_targets"]) <= set(GROUPS["ligas"]["target"]))

    def test_ece_perfect_and_bad(self):
        P = np.array([[0.9, 0.05, 0.05]] * 10); y = np.array([0] * 9 + [1])
        self.assertAlmostEqual(ligas.ece_top(P, y), 0.0, places=6)
        self.assertGreater(ligas.ece_top(P, np.array([1] * 10)), 0.8)


if __name__ == "__main__":
    unittest.main()
