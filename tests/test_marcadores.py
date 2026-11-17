import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd

from kalshi_nba.marcadores import fetch, hit


def ev(i, home, away, hs, as_, name="STATUS_FINAL", state="post"):
    return {"id": i, "status": {"type": {"name": name, "state": state, "shortDetail": "Final"}},
            "competitions": [{"competitors": [{"homeAway": "home", "score": str(hs), "team": {"displayName": home}},
                                              {"homeAway": "away", "score": str(as_), "team": {"displayName": away}}]}]}


class TestMarcadores(unittest.TestCase):
    def test_fetch_by_id_and_by_names(self):
        now = pd.Timestamp("2026-11-16T12:00Z")
        games = [{"sport": "nba", "id": "1", "t": "2026-11-15T01:00Z", "home": "A", "away": "B"},
                 {"sport": "liga", "id": "x9", "code": "eng.1", "t": "2026-11-15T15:00Z", "home": "Arsenal", "away": "Chelsea"},
                 {"sport": "nba", "id": "2", "t": "2026-11-20T01:00Z", "home": "C", "away": "D"}]          # futuro: no se consulta
        calls = []
        def getter(url, params):
            calls.append(url)
            return {"events": [ev("1", "A", "B", 110, 100)]} if "nba" in url else {"events": [ev("777", "Arsenal", "Chelsea", 2, 1, "STATUS_FULL_TIME")]}
        sc = fetch(games, now, getter=getter)
        self.assertEqual(sc["nba:1"]["hs"], 110); self.assertEqual(sc["liga:x9"]["as"], 1)
        self.assertNotIn("nba:2", sc); self.assertEqual(len(calls), 2)

    def test_hit_rules(self):
        g = {"home": "A", "away": "B", "pick": "A", "three": True}
        self.assertTrue(hit(g, {"state": "post", "hs": 2, "as": 1, "regular": True}))
        self.assertFalse(hit({**g, "pick": "Empate"}, {"state": "post", "hs": 2, "as": 1, "regular": True}))
        self.assertTrue(hit({**g, "pick": "Empate"}, {"state": "post", "hs": 1, "as": 1, "regular": True}))
        self.assertFalse(hit(g, {"state": "post", "hs": 2, "as": 1, "regular": False}))      # prórroga: a 90' fue empate
        self.assertTrue(hit({**g, "pick": "Empate"}, {"state": "post", "hs": 2, "as": 1, "regular": False}))
        self.assertIsNone(hit(g, {"state": "in", "hs": 2, "as": 1, "regular": False}))
        self.assertIsNone(hit(g, None))


if __name__ == "__main__":
    unittest.main()
