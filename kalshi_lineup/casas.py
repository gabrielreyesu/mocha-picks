"""¿Casas más precisas que otras? (CASAS_RESEARCH.md)   python -m kalshi_lineup.casas  -> reports/casas.json"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

NOT_BOOKS = {"teamrankings", "accuscore", "numberfire", "consensus"}


def _dec(ml):
    return 1 + ml / 100 if ml > 0 else 1 + 100 / abs(ml)


def book_probs(items):
    out = {}
    for i in items or []:
        name, h, a = i.get("provider", ""), i.get("ml_home"), i.get("ml_away")
        if name in NOT_BOOKS or "live" in name.lower() or h is None or a is None or h != h or a != a or abs(h) < 100 or abs(a) < 100:
            continue
        ih, ia = 1 / _dec(h), 1 / _dec(a)
        if 1.0 <= ih + ia <= 1.15:
            out[name] = ih / (ih + ia)
    return out


def table(league):
    from kalshi_nba.data import load_league
    g = load_league(league, first_season=2016, with_odds=False, verbose=False)
    g = g[g["status"] == "STATUS_FINAL"].dropna(subset=["hs", "as_"])
    g = g[g["hs"] != g["as_"]]
    rows = []
    for r in g.itertuples():
        p = Path(f"data/{league}/odds/{r.event_id}.json")
        if not p.exists():
            continue
        bp = book_probs(json.loads(p.read_text()))
        if len(bp) < 2:
            continue
        rows.append({"event_id": r.event_id, "date": pd.Timestamp(r.day), "season": r.season_year, "y": int(r.hs > r.as_),
                     "median": float(np.median(list(bp.values()))), **{f"b:{k}": v for k, v in bp.items()}})
    return pd.DataFrame(rows)


lg_ = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
ll = lambda p, y: -(y * np.log(np.clip(p, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-9, 1)))


def evaluate(d: pd.DataFrame) -> dict:
    from sklearn.linear_model import LogisticRegression
    from kalshi_nba.backtest import paired_bootstrap
    bcols = [c for c in d.columns if c.startswith("b:")]
    out = {"n": int(len(d)), "logloss_mediana": round(float(ll(d["median"], d["y"]).mean()), 5), "casas": []}
    for c in bcols:
        s = d[d[c].notna()]
        if len(s) < 500:
            continue
        bs = paired_bootstrap(ll(s["median"], s["y"]), ll(s[c], s["y"]), s["date"])
        out["casas"].append({"casa": c[2:], "n": int(len(s)), "logloss": round(float(ll(s[c], s["y"]).mean()), 5),
                             "logloss_mediana_mismos": round(float(ll(s["median"], s["y"]).mean()), 5), **bs})
    top = sorted(bcols, key=lambda c: -d[c].notna().sum())[:6]
    X = lambda x: np.column_stack([lg_(x["median"])] + [lg_(x[c].fillna(x["median"])) for c in top])
    X0 = lambda x: lg_(x["median"]).to_numpy().reshape(-1, 1)
    pa, pb, idx = [], [], []
    for s in sorted(d["season"].unique()):
        tr, te = d[d["season"] < s], d[d["season"] == s]
        if len(tr) < 1000 or te.empty:
            continue
        m0 = LogisticRegression(C=1e4, max_iter=1000).fit(X0(tr), tr["y"])
        m1 = LogisticRegression(C=1.0, max_iter=1000).fit(X(tr), tr["y"])
        pa += list(m0.predict_proba(X0(te))[:, 1]); pb += list(m1.predict_proba(X(te))[:, 1]); idx += list(te.index)
    e = d.loc[idx]
    out["ponderada"] = {"casas_usadas": [c[2:] for c in top], "n": int(len(e)),
                        "mediana_recalibrada": round(float(ll(np.array(pa), e["y"]).mean()), 5),
                        "ponderada": round(float(ll(np.array(pb), e["y"]).mean()), 5),
                        "mejora": paired_bootstrap(ll(np.array(pa), e["y"].to_numpy()), ll(np.array(pb), e["y"].to_numpy()), e["date"])}
    return out


def main():
    res = {lg: evaluate(table(lg)) for lg in ("nba", "nfl")}
    Path("reports").mkdir(exist_ok=True)
    Path("reports/casas.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for lg, r in res.items():
        print(lg.upper(), "n", r["n"], "mediana", r["logloss_mediana"])
        for c in sorted(r["casas"], key=lambda x: x["mejora"], reverse=True):
            print(f"   {c['casa']:<30} n={c['n']:<6} {c['mejora']:+.5f} [{c['ic95_inf']:+.5f}; {c['ic95_sup']:+.5f}]")
        print("   ponderada:", r["ponderada"])


if __name__ == "__main__":
    main()
