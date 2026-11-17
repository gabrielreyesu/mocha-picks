import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd

from kalshi_nba import combinadas as C
from kalshi_nba.marcadores import pick_hit


def game(i, t, state="pre", prob=0.8, price=None, hit=None):
    return {"sport": "nba", "id": str(i), "home": f"H{i}", "away": f"A{i}", "comp": "NBA", "t": t, "state": state, "three": False,
            "picks": [{"mercado": "Ganador", "pick": f"H{i}", "prob": prob, "fuente": "casas", "precio": price, "hit": hit}]}


class TestPickHit(unittest.TestCase):
    def test_markets(self):
        g = {"home": "A", "away": "B", "three": True}
        sc = {"state": "post", "hs": 2, "as": 1, "regular": True}
        self.assertTrue(pick_hit(g, {"mercado": "Doble oportunidad", "pick": "A o empate"}, sc))
        self.assertFalse(pick_hit(g, {"mercado": "Doble oportunidad", "pick": "B o empate"}, sc))
        self.assertTrue(pick_hit(g, {"mercado": "Goles", "pick": "Más de 2.5"}, sc))
        self.assertFalse(pick_hit(g, {"mercado": "Goles (línea segura)", "pick": "Menos de 1.5"}, sc))
        self.assertTrue(pick_hit(g, {"mercado": "Ambos anotan", "pick": "Sí"}, sc))
        et = {**sc, "regular": False}                                     # prórroga: empate a 90', goles desconocidos
        self.assertTrue(pick_hit(g, {"mercado": "Ganador", "pick": "Empate"}, et))
        self.assertIsNone(pick_hit(g, {"mercado": "Goles", "pick": "Más de 2.5"}, et))
        u = {"home": "X", "away": "Y", "three": False}
        s2 = {"state": "post", "hs": 110, "as": 104, "regular": True}
        self.assertTrue(pick_hit(u, {"mercado": "Hándicap", "pick": "X gana por más de 3.5"}, s2))
        self.assertFalse(pick_hit(u, {"mercado": "Hándicap", "pick": "Y +5.5 (gana o pierde por menos de 5.5)"}, s2))
        self.assertTrue(pick_hit(u, {"mercado": "Total de puntos", "pick": "Más de 210.5"}, s2))
        self.assertIsNone(pick_hit(u, {"mercado": "Ganador", "pick": "X"}, {**s2, "state": "in"}))


class TestCombinadas(unittest.TestCase):
    def test_build_distinct_games_and_odds(self):
        gs = [game(i, "2026-11-20T01:00Z", prob=0.9 - 0.02 * i) for i in range(8)]
        tk = C.build(C.legs(gs))
        self.assertTrue(tk)
        for t in tk:
            self.assertEqual(len({l["id"] for l in t["legs"]}), len(t["legs"]))
            self.assertGreaterEqual(t["O"], 1.6)
        self.assertEqual(tk[0]["perfil"], "Más segura")

    def test_freeze_and_resolve(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            gs = [game(i, "2026-11-20T01:00Z", prob=0.85) for i in range(6)]
            out = C.update(gs, pd.Timestamp("2026-11-19T12:00Z"), d, "America/Chicago")
            day = next(iter(out)); n1 = len(C.load(d / C.FILE_NAME))
            self.assertFalse(out[day]["congelada"])
            gs2 = [game(i, "2026-11-20T01:00Z", state="post", prob=0.55, hit=True) for i in range(6)]
            out2 = C.update(gs2, pd.Timestamp("2026-11-20T06:00Z"), d, "America/Chicago")
            self.assertTrue(out2[day]["congelada"])
            self.assertEqual(out2[day]["tickets"][0]["legs"][0]["prob"], 0.85)    # no se recalcula tras empezar
            self.assertTrue(all(t["acierto"] for t in out2[day]["tickets"]))
            rows = C.load(d / C.FILE_NAME)
            self.assertEqual(sum(r["tipo"] == "combinadas" for r in rows), n1)
            self.assertEqual(sum(r["tipo"] == "resultado" for r in rows), 1)
            self.assertEqual(C.summary(d)["dias"], 1)

    def test_record_picks_once(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            gs = [game(1, "2026-11-20T01:00Z", state="post", hit=True), game(2, "2026-11-20T01:00Z", state="post", hit=False)]
            self.assertEqual(C.record_picks(gs, d, "America/Chicago"), 2)
            self.assertEqual(C.record_picks(gs, d, "America/Chicago"), 0)
            s = C.picks_summary(d)
            self.assertEqual((s[0]["mercado"], s[0]["n"], s[0]["acierto"]), ("Ganador", 2, 0.5))


if __name__ == "__main__":
    unittest.main()
