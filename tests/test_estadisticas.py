import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd

from kalshi_nba import estadisticas as E


def sev(i, t, h, a, hg, ag, stats=True, status="STATUS_FULL_TIME", details=None):
    st = lambda sh, sot, cor, pos: [{"name": "totalShots", "displayValue": str(sh)}, {"name": "shotsOnTarget", "displayValue": str(sot)},
                                    {"name": "wonCorners", "displayValue": str(cor)}, {"name": "possessionPct", "displayValue": str(pos)}]
    return {"id": i, "date": t, "status": {"type": {"name": status}},
            "competitions": [{"venue": {"fullName": "Estadio"}, "details": details or [],
                              "competitors": [{"homeAway": "home", "score": str(hg), "team": {"id": h, "displayName": "T" + h},
                                               "statistics": st(10, 4, 5, 55) if stats else st(0, 0, 0, 0)},
                                              {"homeAway": "away", "score": str(ag), "team": {"id": a, "displayName": "T" + a},
                                               "statistics": st(8, 2, 3, 45) if stats else st(0, 0, 0, 0)}]}]}


class TestEstadisticas(unittest.TestCase):
    def test_parse_cards_scorers_and_zero_stats(self):
        det = [{"yellowCard": True, "team": {"id": "1"}}, {"redCard": True, "team": {"id": "2"}, "clock": {"displayValue": "80'"},
                                                            "athletesInvolved": [{"shortName": "X. Rojo"}]},
               {"scoringPlay": True, "penaltyKick": True, "team": {"id": "1"}, "clock": {"displayValue": "10'"}, "athletesInvolved": [{"shortName": "A. Gol"}]}]
        e = E.parse_soccer(sev("9", "2026-11-01T15:00Z", "1", "2", 1, 0, details=det), "eng.1")
        self.assertEqual((e["h"]["yc"], e["a"]["rc"], e["h"]["sh"], e["venue"]), (1, 1, 10, "Estadio"))
        self.assertEqual([x["k"] for x in e["ev"]], ["r", "g"]); self.assertTrue(e["ev"][1]["pen"])
        z = E.parse_soccer(sev("8", "2026-11-01T15:00Z", "1", "2", 1, 0, stats=False), "aut.1")
        self.assertIsNone(z["h"]["sh"]); self.assertIsNone(z["a"]["pos"])           # ligas sin datos: desconocido, no 0

    def test_panel_uses_only_past_matches(self):
        evs = []
        for k in range(12):
            d = f"2026-10-{k + 1:02d}T15:00Z"
            evs.append(E.parse_soccer(sev(f"a{k}", d, "1", str(10 + k), 2, 1), "eng.1"))
            evs.append(E.parse_soccer(sev(f"b{k}", d, str(30 + k), "2", 0, 0), "eng.1"))
        evs.append(E.parse_soccer(sev("fut", "2026-10-20T15:00Z", "1", "2", 9, 9), "eng.1"))  # después del partido: no cuenta
        rows = E.team_rows(evs)
        p = E.panel(rows, "1", "2", pd.Timestamp("2026-10-15T15:00Z"), ["eng.1"])
        self.assertEqual(p["avg"]["h"]["n"], 10); self.assertEqual(p["avg"]["h"]["gf"], 2.0)
        self.assertEqual(p["form"]["h"][0]["r"], "G"); self.assertEqual(p["form"]["a"][0]["r"], "E")
        self.assertEqual(p["h2h"], [])
        # goles esperados = (2 a favor local + 0 en contra visita)/2 + (0 a favor visita + 1 en contra local)/2
        self.assertAlmostEqual(p["exp"]["goals"], 1.5)
        self.assertAlmostEqual(p["exp"]["corners"], (5 + 5) / 2 + (3 + 3) / 2)

    def test_build_resolves_by_espn_id(self):
        evs = [E.parse_soccer(sev(f"x{k}", f"2026-10-{k + 1:02d}T15:00Z", "1", "2", 1, 1), "uefa.champions") for k in range(5)]
        evs.append(E.parse_soccer(sev("next", "2026-11-20T20:00Z", "1", "2", 0, 0, status="STATUS_SCHEDULED"), "uefa.champions"))
        g = {"sport": "club", "id": "next", "code": "uefa.champions", "t": "2026-11-20T20:00Z", "home": "T1", "away": "T2"}
        out = E.build([g], {"soccer": evs, "national": [], "nba": [], "nfl": []})
        p = out["club:next"]
        self.assertEqual(len(p["h2h"]), 5); self.assertEqual(p["venue"], "Estadio")


if __name__ == "__main__":
    unittest.main()
