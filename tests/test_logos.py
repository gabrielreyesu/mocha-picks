import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from kalshi_nba.logos import Logos, build


def team(name, rels):
    return {"team": {"displayName": name, "logos": [{"href": f"https://x/{name}/{'-'.join(r)}.png", "rel": r} for r in rels]}}


class TestLogos(unittest.TestCase):
    def test_build_prefers_dark_and_survives_errors(self):
        def getter(url):
            if "nba/teams" in url:
                return {"sports": [{"leagues": [{"teams": [team("Memphis Grizzlies", [["full", "default"], ["full", "dark"]])]}]}]}
            if "nba/scoreboard" in url:
                return {"leagues": [{"logos": [{"href": "https://x/nba.png"}]}]}
            raise RuntimeError("caído")
        d = build(getter)
        self.assertEqual(d["teams"]["nba"]["Memphis Grizzlies"], "https://x/Memphis Grizzlies/full-dark.png")
        self.assertEqual(d["comps"]["nba"], "https://x/nba.png")
        self.assertEqual(d["teams"]["nfl"], {})

    def test_lookup_aliases_and_missing(self):
        L = Logos({"teams": {"soccer": {"Manchester United": "u1", "AS Roma": "u2"}, "national": {"Spain": "es"}},
                   "comps": {"eng.1": "pl", "nba": "n"}})
        self.assertEqual(L.team("liga", "Man United"), "u1")
        self.assertEqual(L.team("liga", "Roma"), "u2")
        self.assertEqual(L.team("intl", "Spain"), "es")
        self.assertIsNone(L.team("liga", "Equipo Inventado FC"))
        self.assertEqual(L.comp("liga", "eng.1"), "pl"); self.assertEqual(L.comp("nba", None), "n")
        self.assertIsNone(Logos.load("/no/existe.json").team("nba", "X"))


if __name__ == "__main__":
    unittest.main()
