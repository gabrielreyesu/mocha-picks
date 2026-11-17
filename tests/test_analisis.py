import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from kalshi_nba.analisis import analyze


def form(rs):
    return [{"r": r, "d": "2026-11-01", "o": "X", "ha": "L", "s": "1-0", "c": "nba"} for r in rs]


class TestAnalisis(unittest.TestCase):
    def test_us_game_reasons_and_risks(self):
        g = {"sport": "nba", "home": "A", "away": "B", "three": False, "pick": "A", "prob": 0.65, "src": "Kalshi + casas + modelo",
             "rows": [["Modelo", [0.6, 0.4]], ["Casas", [0.66, 0.34]], ["Kalshi", [0.65, 0.35]]],
             "kp": {"margin": 4.2, "total": 220.0}, "rest": [1.0, 3.0], "inj": {"home": ["X (out)"], "away": []},
             "st": {"form": {"h": form("GGGGP"), "a": form("PPGPP")}, "vavg": {}, "h2h": []}, "extra": []}
        fiab = {"NBA": {"tramos": [{"tramo": "60–70%", "n": 289, "prob_media": .65, "acierto": .675}]}}
        a = analyze(g, fiab)
        txt = " ".join(a["puntos"])
        self.assertIn("Las 3 fuentes", txt); self.assertIn("68%", txt); self.assertIn("mejor forma", txt)
        self.assertTrue(any("back-to-back" in x for x in a["contra"]))       # el elegido juega en días seguidos
        self.assertTrue(any("bajas" in x or "baja" in x for x in a["contra"]))
        self.assertTrue(any("viene de 4 victorias seguidas" in x for x in a["datos"]))

    def test_soccer_disagreement_and_no_pick(self):
        g = {"sport": "liga", "home": "A", "away": "B", "three": True, "pick": "A", "prob": 0.42, "src": "Kalshi + modelo",
             "rows": [["Modelo", [0.3, 0.3, 0.4]], ["Kalshi", [0.45, 0.28, 0.27]]], "kp": {"xg": 2.4, "o25": 0.45}, "st": {}, "extra": []}
        a = analyze(g, {})
        self.assertTrue(any("No todas coinciden" in x for x in a["contra"]))
        self.assertTrue(any("NO ocurra" in x for x in a["contra"]))
        self.assertTrue(any("2,4 goles" in x for x in a["datos"]))
        none = analyze({**g, "pick": None, "prob": None, "src": "sin cuotas"}, {})
        self.assertTrue(none["titular"].startswith("Sin pick"))


if __name__ == "__main__":
    unittest.main()
