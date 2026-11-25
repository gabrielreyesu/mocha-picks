import pandas as pd

from kalshi_intl.tiros_grupos import history_flag


def test_history_flag_only_counts_previous_days():
    f = pd.DataFrame({"event_id": ["1", "2", "3"], "date": pd.to_datetime(["2024-09-01", "2024-09-01", "2024-09-08"]),
                      "home_id": ["A", "C", "A"], "away_id": ["B", "D", "C"], "final": [True, True, True]})
    ev = {"1": {"h": {"sot": 3}, "a": {"sot": 2}}, "2": {"h": {"sot": None}, "a": {"sot": None}}}
    fl = history_flag(f, ev)
    assert list(fl) == [0, 0, 0]          # día 1: nadie tiene historia; día 8: C nunca tuvo tiros
    f.loc[2, "away_id"] = "B"
    assert list(history_flag(f, ev)) == [0, 0, 1]
