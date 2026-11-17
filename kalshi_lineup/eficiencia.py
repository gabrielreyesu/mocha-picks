"""Eficiencia ofensiva/defensiva y ritmo NBA desde el box score (EFICIENCIA_RESEARCH.md).

  python -m kalshi_lineup.eficiencia        # -> reports/eficiencia_result.json y texto en pantalla
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HALF = 10.0                     # media vida (partidos) del promedio exponencial
ALPHA = 1 - 0.5 ** (1 / HALF)
PRIOR_W = 0.5                   # al cambiar de temporada: 50% de regresión a la media de la liga
VARIANTS = {"A_eff": ["eff_diff"], "B_eff_ritmo": ["eff_diff", "pace_avg"], "C_ofe_def": ["ortg_diff", "drtg_diff"]}


def team_lines(box: dict) -> dict:
    """{team_id: {pts, poss}} de un partido."""
    t = {}
    for p in box.get("players", []):
        x = t.setdefault(str(p["team_id"]), {"pts": 0.0, "fga": 0.0, "fta": 0.0, "oreb": 0.0, "tov": 0.0})
        for k in x:
            v = p.get(k)
            try:
                v = float(v)
            except (TypeError, ValueError):
                v = 0.0
            x[k] += v if np.isfinite(v) else 0.0               # DNP: estadísticas vacías/NaN no deben contaminar el promedio
    return {k: {"pts": v["pts"], "poss": v["fga"] + 0.44 * v["fta"] - v["oreb"] + v["tov"]} for k, v in t.items()}


class EffRater:
    def __init__(self):
        self.o, self.d, self.p, self.season = {}, {}, {}, {}
        self.lg = {"o": 112.0, "p": 99.0}

    def _get(self, t, season):
        if self.season.get(t) != season:                         # regresión a la media al cambiar de temporada
            if t in self.o:
                self.o[t] = PRIOR_W * self.o[t] + (1 - PRIOR_W) * self.lg["o"]
                self.d[t] = PRIOR_W * self.d[t] + (1 - PRIOR_W) * self.lg["o"]
                self.p[t] = PRIOR_W * self.p[t] + (1 - PRIOR_W) * self.lg["p"]
            self.season[t] = season
        return self.o.get(t, self.lg["o"]), self.d.get(t, self.lg["o"]), self.p.get(t, self.lg["p"])

    def process(self, games: pd.DataFrame, boxes: dict) -> pd.DataFrame:
        d = games[["event_id", "date", "home_id", "away_id", "season_year"]].copy()
        d["event_id"] = d["event_id"].astype(str)
        rows = []
        for date, day in d.sort_values("date").groupby("date", sort=True):
            for r in day.itertuples():
                oh, dh, ph = self._get(str(r.home_id), r.season_year)
                oa, da, pa = self._get(str(r.away_id), r.season_year)
                rows.append({"event_id": r.event_id, "eff_diff": (oh - dh) - (oa - da), "pace_avg": (ph + pa) / 2,
                             "ortg_diff": oh - oa, "drtg_diff": dh - da})
            for r in day.itertuples():                             # se incorporan DESPUÉS de todo el día
                b = boxes.get(r.event_id)
                if not b:
                    continue
                tl = team_lines(b)
                h, a = tl.get(str(r.home_id)), tl.get(str(r.away_id))
                if not h or not a or h["poss"] < 60 or a["poss"] < 60:
                    continue
                poss = (h["poss"] + a["poss"]) / 2
                for t, me, op in ((str(r.home_id), h, a), (str(r.away_id), a, h)):
                    o, dd, p = self._get(t, r.season_year)
                    self.o[t] = (1 - ALPHA) * o + ALPHA * 100 * me["pts"] / poss
                    self.d[t] = (1 - ALPHA) * dd + ALPHA * 100 * op["pts"] / poss
                    self.p[t] = (1 - ALPHA) * p + ALPHA * poss
                self.lg["o"] = 0.995 * self.lg["o"] + 0.005 * 100 * (h["pts"] + a["pts"]) / (2 * poss)
                self.lg["p"] = 0.995 * self.lg["p"] + 0.005 * poss
        return pd.DataFrame(rows)


def main():
    from kalshi_nba.data import load_league
    from kalshi_nba.engine import CONFIGS, LEAGUE_FEATURES, NBAEngine
    from .box import load_boxes
    from .evaluate import decide, render, run_variants
    games = load_league("nba", first_season=2016, verbose=False)
    final = games[games["status"] == "STATUS_FINAL"]
    boxes = load_boxes(final["event_id"], cache_dir="data/nba/box", workers=8)
    cov = {"partidos_finales": int(len(final)), "con_boxscore": int(len(boxes))}
    feats = NBAEngine(CONFIGS["nba"]).process(games)
    feats["event_id"] = feats["event_id"].astype(str)
    feats = feats.merge(EffRater().process(games, boxes), on="event_id", how="left")
    miss = feats["eff_diff"].isna()
    print(f"sin variables de eficiencia: {int(miss.sum())} de {len(feats)} (se rellenan con 0 / media)")
    for c in ("eff_diff", "ortg_diff", "drtg_diff"):
        feats[c] = feats[c].fillna(0.0)
    feats["pace_avg"] = feats["pace_avg"].fillna(feats["pace_avg"].mean())
    oos = run_variants(feats, LEAGUE_FEATURES["nba"], first_test=2019, min_train=2000, variants=VARIANTS)
    res = decide(oos, feats, variants=VARIANTS)
    txt = render(res, cov, title="NBA — EFICIENCIA Y RITMO (BOX SCORE)")
    Path("reports").mkdir(exist_ok=True)
    Path("reports/eficiencia_result.json").write_text(json.dumps({**res, "cobertura": cov}, indent=1, ensure_ascii=False, default=str))
    print(txt)


if __name__ == "__main__":
    main()
