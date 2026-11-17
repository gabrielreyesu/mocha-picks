import json, os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from kalshi_nba import alineaciones as A


def roster(side, starters, form="4-3-3"):
    r = [{"starter": True, "jersey": str(i + 1), "formationPlace": str(i + 1), "athlete": {"shortName": f"{side}{i}"},
          "position": {"abbreviation": "G" if i == 0 else "CD"}} for i in range(starters)]
    r += [{"starter": False, "jersey": "30", "athlete": {"shortName": f"{side}sub"}, "position": {"abbreviation": "SUB"}}]
    return {"homeAway": "home" if side == "H" else "away", "formation": form, "roster": r}


class TestAlineaciones(unittest.TestCase):
    def test_parse_official(self):
        out = A.parse_rosters({"rosters": [roster("H", 11), roster("A", 11, "5-3-2")]})
        self.assertEqual(len(out["h"]["xi"]), 11); self.assertEqual(out["a"]["formation"], "5-3-2")
        self.assertEqual(out["h"]["xi"][0]["pos"], "G"); self.assertEqual(out["h"]["bench"][0]["n"], "Hsub")
        self.assertEqual(A.parse_rosters({"rosters": [roster("H", 0)]}), {})          # sin titulares aún: nada

    def test_soccer_probable_from_last_match(self):
        calls = []
        def getter(url, params):
            calls.append(params["event"])
            if params["event"] == "now":                                             # aún sin once oficial
                return {"header": {"competitions": [{"status": {"type": {"name": "STATUS_SCHEDULED"}}}]}, "rosters": []}
            return {"header": {"competitions": [{"status": {"type": {"name": "STATUS_FULL_TIME"}}}]},
                    "rosters": [roster("H", 11), roster("A", 11)]}
        st = {"eid": "now", "last": {"h": {"eid": "p1", "code": "eng.1"}, "a": {"eid": "p2", "code": "eng.1"}},
              "form": {"h": [{"ha": "V"}], "a": [{"ha": "L"}]}}
        with tempfile.TemporaryDirectory() as d:
            old = A.CACHE; A.CACHE = Path(d)
            try:
                out = A.soccer({"code": "eng.1"}, st, getter)
            finally:
                A.CACHE = old
        self.assertEqual(out["h"]["tipo"], "probable"); self.assertEqual(out["h"]["xi"][0]["n"], "A0")   # jugó de visitante
        self.assertEqual(out["a"]["xi"][0]["n"], "H0")

    def test_nba_marks_injured(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "e1.json").write_text(json.dumps({"ok": True, "players": [
                {"name": "P1", "team_id": "5", "starter": True}, {"name": "P2", "team_id": "5", "starter": True},
                {"name": "X", "team_id": "9", "starter": True}]}))
            g = {"sport": "nba", "home_id": "5", "away_id": "9", "inj": {"home": ["P2 (out)"], "away": []}}
            st = {"last": {"h": {"eid": "e1"}, "a": None}}
            out = A.us(g, st, Path(d))
        self.assertEqual([x["n"] for x in out["h"]["xi"]], ["P1", "P2"]); self.assertTrue(out["h"]["xi"][1]["baja"])


if __name__ == "__main__":
    unittest.main()
