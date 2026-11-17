import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd

from kalshi_nba.prepartido import due


class TestPrepartido(unittest.TestCase):
    def test_due_only_when_game_soon_and_photo_old(self):
        now = pd.Timestamp("2026-11-20T18:00Z")
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            pd.DataFrame({"event_id": ["1"], "kickoff_utc": ["2026-11-20T19:00Z"]}).to_csv(d / "nba_registry.csv", index=False)
            pd.DataFrame({"event_id": ["2"], "kickoff_utc": ["2026-11-21T19:00Z"]}).to_csv(d / "nfl_registry.csv", index=False)
            pd.DataFrame({"snapshot_utc": ["2026-11-20T17:00Z"]}).to_csv(d / "nba_kalshi_snapshots.csv", index=False)
            self.assertEqual(due(now, d), ["nba"])                    # NFL no tiene partido pronto
            pd.DataFrame({"snapshot_utc": ["2026-11-20T17:50Z"]}).to_csv(d / "nba_kalshi_snapshots.csv", index=False)
            self.assertEqual(due(now, d), [])                         # foto reciente: no hace falta


if __name__ == "__main__":
    unittest.main()
