import pandas as pd

from kalshi_soccer.tiros5 import shot_features


def test_shot_features_only_use_previous_days():
    feats = pd.DataFrame({"date": pd.to_datetime(["2024-08-10", "2024-08-17", "2024-08-17"]), "competition": "EPL",
                          "season": "2425", "home": ["A", "A", "C"], "away": ["B", "C", "B"]})
    shots = pd.DataFrame({"date": feats["date"], "competition": "EPL", "home": feats["home"], "away": feats["away"],
                          "h_sot": [10, 0, 0], "a_sot": [0, 0, 0], "h_sh": [20, 0, 0], "a_sh": [0, 0, 0]})
    f = shot_features(feats, shots)
    assert f.loc[0, "sot_diff"] == 0                    # primer partido: nadie tiene historia
    assert f.loc[1, "sot_diff"] > 0                     # A dominó el día anterior
    shots.loc[1, "h_sot"] = 99                          # cambiar el propio partido no altera su variable
    assert shot_features(feats, shots).loc[1, "sot_diff"] == f.loc[1, "sot_diff"]


def test_record_shadow_is_prospective_and_append_only(tmp_path):
    from kalshi_soccer.tiros5 import record_shadow
    p = tmp_path / "s.csv"
    sh = pd.DataFrame({"match_id": ["1", "2"], "s_A": [.3, .3], "s_D": [.3, .3], "s_H": [.4, .4]})
    kick = {"1": "2026-12-01T15:00:00+00:00", "2": "2026-11-01T15:00:00+00:00"}       # el 2 ya empezó
    now = pd.Timestamp("2026-11-25", tz="UTC")
    assert record_shadow(sh, kick, path=p, now=now) == 1
    assert record_shadow(sh, kick, path=p, now=now) == 0
    assert list(pd.read_csv(p, dtype={"match_id": str})["match_id"]) == ["1"]
