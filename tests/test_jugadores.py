import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd

from kalshi_nba import jugadores as J


def mk(title, ticker, bid, ask, ev="KXNBAPTS-26NOV17DETSAS"):
    return {"title": title, "ticker": ticker, "event_ticker": ev, "yes_bid_dollars": str(bid), "yes_ask_dollars": str(ask)}


class TestJugadores(unittest.TestCase):
    def test_parse_and_attach_by_market_date(self):
        r = J.parse("KXNBAPTS", mk("Keldon Johnson: 20+ points", "KXNBAPTS-26NOV17DETSAS-SASKJOHNSON3-20", .60, .66), {"SAS", "DET"})
        self.assertEqual((r["player"], r["line"], r["team"], r["day"], r["p"]), ("Keldon Johnson", 20, "SAS", "2026-11-17", 0.63))
        self.assertIsNone(J.parse("KXNBAPTS", mk("X: 10+ points", "KXNBAPTS-26NOV17DETSAS-SASX-10", .2, .5), {"SAS"}))   # 30¢ de spread
        games = [{"sport": "nba", "id": "old", "home_id": "24", "away_id": "8", "home": "San Antonio Spurs", "away": "Detroit Pistons", "t": "2026-11-16T19:00:00-06:00"},
                 {"sport": "nba", "id": "new", "home_id": "24", "away_id": "8", "home": "San Antonio Spurs", "away": "Detroit Pistons", "t": "2026-11-17T19:00:00-06:00"}]
        a = J.attach([r], games)
        self.assertEqual(a[0]["gid"], "new"); self.assertEqual(a[0]["side"], "home")                # mismo cruce dos días: manda la fecha

    def test_best_line_and_model(self):
        base = {"gid": "g", "player": "P", "stat": "Puntos", "state": "pre"}
        rows = [{**base, "p": .95, "line": 5}, {**base, "p": .74, "line": 15}, {**base, "p": .40, "line": 25}]
        self.assertEqual([r["line"] for r in J.best_lines(rows)], [15])
        self.assertAlmostEqual(J.p_model({"media": 20, "sd": 5}, 20), 0.5398, places=3)
        hist = pd.DataFrame({"name": ["P"] * 5, "t": pd.date_range("2026-11-01", periods=5, tz="UTC"), "min": [30] * 5, "pts": [10, 12, 14, 16, 18]})
        pr = J.projection(hist, "P", "pts", "2026-11-10T00:00Z")
        self.assertEqual((pr["media"], pr["partidos"]), (14.0, 5))
        self.assertIsNone(J.projection(hist, "P", "pts", "2026-11-03T00:00Z"))                      # solo partidos anteriores


if __name__ == "__main__":
    unittest.main()
