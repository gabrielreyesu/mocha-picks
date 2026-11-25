import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import numpy as np
import pandas as pd

from kalshi_intl import odds_api


class R:
    def __init__(self, j, h=None): self._j, self.status_code, self.headers = j, 200, h or {}
    def json(self): return self._j


class S:
    def __init__(self, events): self.events, self.calls = events, []
    def get(self, url, params=None, timeout=None):
        self.calls.append(url)
        if url.endswith("/sports"):
            return R([{"key": "soccer_fa_cup", "active": True}])
        return R(self.events, {"x-requests-remaining": "400"})


def ev(h, a, t, prices):
    bk = lambda p: {"markets": [{"key": "h2h", "outcomes": [{"name": h, "price": p[0]}, {"name": "Draw", "price": p[1]}, {"name": a, "price": p[2]}]},
                                {"key": "totals", "outcomes": [{"name": "Over", "price": 1.9, "point": 2.5}, {"name": "Under", "price": 1.9, "point": 2.5}]}]}
    return {"home_team": h, "away_team": a, "commence_time": t, "bookmakers": [bk(p) for p in prices]}


class TestOddsApi(unittest.TestCase):
    def test_fill_only_missing_and_devig(self):
        t = (pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=1)).floor("h")
        d = pd.DataFrame([{"code": "eng.fa", "home": "Arsenal", "away": "Chelsea", "kickoff_utc": t.isoformat(), "mkt_H": np.nan, "mkt_D": np.nan, "mkt_A": np.nan, "mkt_over": np.nan, "n_books": np.nan},
                          {"code": "eng.fa", "home": "Leeds United", "away": "Hull City", "kickoff_utc": t.isoformat(), "mkt_H": .5, "mkt_D": .3, "mkt_A": .2, "mkt_over": np.nan, "n_books": 3}])
        s = S([ev("Arsenal", "Chelsea", t.isoformat(), [(2.0, 3.5, 4.0), (2.1, 3.4, 3.8)])])
        out = odds_api.fill(d, key="x", session=s)
        self.assertAlmostEqual(out.loc[0, ["mkt_H", "mkt_D", "mkt_A"]].sum(), 1.0)
        self.assertGreater(out.loc[0, "mkt_H"], out.loc[0, "mkt_A"]); self.assertEqual(out.loc[0, "n_books"], 2)
        self.assertAlmostEqual(out.loc[0, "mkt_over"], 0.5)
        self.assertEqual(out.loc[1, "mkt_H"], .5)                      # ya tenía cuotas de ESPN: no se toca
        self.assertEqual(len(s.calls), 2)

    def test_no_key_no_calls(self):
        d = pd.DataFrame([{"code": "eng.fa", "mkt_H": np.nan}])
        self.assertIs(odds_api.fill(d, key=""), d)


if __name__ == "__main__":
    unittest.main()


class TestMatchAndCarry(unittest.TestCase):
    def test_match_one_name_same_time(self):
        t = pd.Timestamp("2026-11-28T15:00Z")
        evs = [{"home": "Sheffield Wednesday", "away": "Hull City", "t": t.isoformat()},
               {"home": "Leeds United", "away": "Burnley", "t": t.isoformat()}]
        self.assertEqual(odds_api._match(evs, "Sheffield Wed", "Hull City", t)["away"], "Hull City")      # coinciden ambos (alias)
        self.assertEqual(odds_api._match(evs, "Leeds United", "Burnley FC Sub", t)["home"], "Leeds United")  # uno coincide y misma hora
        self.assertIsNone(odds_api._match(evs, "Otro", "Equipo", t))

    def test_carry_market_from_previous_snapshot(self):
        import tempfile
        from pathlib import Path
        from kalshi_intl import cli
        now = pd.Timestamp.now(tz="UTC")
        with tempfile.TemporaryDirectory() as tmp:
            old = cli.SNAP; cli.SNAP = Path(tmp) / "s.csv"
            try:
                pd.DataFrame([{"event_id": "9", "snapshot_utc": (now - pd.Timedelta(hours=5)).isoformat(), "mkt_H": .5, "mkt_D": .3, "mkt_A": .2, "n_books": 4}]).to_csv(cli.SNAP, index=False)
                d = pd.DataFrame([{"event_id": "9", "mkt_H": np.nan, "mkt_D": np.nan, "mkt_A": np.nan, "mkt_over": np.nan, "n_books": np.nan},
                                  {"event_id": "8", "mkt_H": np.nan, "mkt_D": np.nan, "mkt_A": np.nan, "mkt_over": np.nan, "n_books": np.nan}])
                out = cli._carry_market(d)
            finally:
                cli.SNAP = old
        self.assertEqual(out.loc[0, "mkt_H"], .5); self.assertTrue(np.isnan(out.loc[1, "mkt_H"]))
