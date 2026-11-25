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
