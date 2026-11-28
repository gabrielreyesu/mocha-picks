import numpy as np
import pandas as pd

from kalshi_nba.jugadores2 import p_over, pregame


def _pg(pts_last):
    rows = []
    for i, pts in enumerate([10, 12, 14, 16, pts_last]):
        t = pd.Timestamp("2026-01-01", tz="UTC") + pd.Timedelta(days=i)
        for pid, team, opp in (("p1", "A", "B"), ("p2", "B", "A")):
            rows.append({"event_id": str(i), "t": t, "team_id": team, "opp_id": opp, "pid": pid, "name": pid, "played": True,
                         "out": False, "min": 30.0, "pts": float(pts), "reb": 5.0, "ast": 3.0})
    return pd.DataFrame(rows)


def test_pregame_does_not_use_the_game_itself():
    a, b = pregame(_pg(16)), pregame(_pg(60))
    last = lambda d: d[(d["event_id"] == "4") & (d["pid"] == "p1")].iloc[0]
    assert np.isclose(last(a)["mu_pts"], last(b)["mu_pts"])          # cambiar el resultado del partido no cambia su previsión
    assert last(a)["n"] == 4 and np.isclose(last(a)["min_pre"], 30.0)
    assert np.isnan(a.iloc[0]["min_pre"])                              # sin historia, sin previsión


def test_p_over_is_monotonic_and_sensible():
    assert p_over(20, 10, 0.05) > p_over(20, 20, 0.05) > p_over(20, 30, 0.05)
    assert 0.4 < p_over(20, 20, 0.05) < 0.6
