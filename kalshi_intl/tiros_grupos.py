"""Tiros en copas europeas (clubes) y selecciones (TIROS_COPAS_RESEARCH.md, issue #80).
python -m kalshi_intl.tiros_grupos  -> reports/tiros_grupos.json"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from .tiros import DEV, VARIANTS, _ll, load_stats, shot_features

EXTRA = VARIANTS["B_tp_tiros"]
GRUPOS = ("clubes", "selecciones")


def history_flag(f: pd.DataFrame, ev: dict) -> pd.Series:
    """1 si los dos equipos tienen al menos un partido ANTERIOR con tiros."""
    seen, out = set(), {}
    for date, day in f.sort_values("date").groupby("date", sort=True):
        for r in day.itertuples():
            out[r.event_id] = int(r.home_id in seen and r.away_id in seen)
        for r in day.itertuples():
            e = ev.get(str(r.event_id))
            if r.final and e and e["h"].get("sot") is not None and e["a"].get("sot") is not None:
                seen.update((r.home_id, r.away_id))
    return f["event_id"].map(out)


def run_group(grp: str) -> dict:
    from sklearn.linear_model import LogisticRegression
    from kalshi_nba.backtest import paired_bootstrap
    from kalshi_intl.data import load_group
    from kalshi_intl.ligas import ece_top
    from kalshi_intl.model import CONFIGS, GROUP_FEATURES, IntlEngine, walk_forward
    from kalshi_intl.odds import fetch as odds
    g = load_group(grp, verbose=False)
    f = IntlEngine(CONFIGS[grp]).process(g)
    ev = load_stats(sorted(set(f["code"])))
    f = f.merge(shot_features(f, ev), on="event_id", how="left")
    f[EXTRA] = f[EXTRA].fillna(0.0)
    f["con_tiros"] = history_flag(f, ev)
    base = GROUP_FEATURES[grp]
    keep = ["event_id", "date", "code", "temporada", "res", "p_H", "p_D", "p_A"]
    r0 = walk_forward(f, first_year=2020, features=base, et_as_draw=True)[keep]
    r1 = walk_forward(f, first_year=2020, features=base + EXTRA, et_as_draw=True)[["event_id", "p_H", "p_D", "p_A"]]
    r = r0.rename(columns={c: f"b_{c}" for c in ("p_H", "p_D", "p_A")}).merge(
        r1.rename(columns={c: f"v_{c}" for c in ("p_H", "p_D", "p_A")}), on="event_id")
    r = r[r["temporada"] >= DEV[0]].merge(f[["event_id", "con_tiros"] + EXTRA], on="event_id").reset_index(drop=True)
    r["y"] = r["res"].map({"H": 0, "D": 1, "A": 2})
    P = lambda d, p: d[[f"{p}_p_H", f"{p}_p_D", f"{p}_p_A"]].to_numpy(float)
    dev, conf = r[r["temporada"] <= DEV[1]], r[r["temporada"] > DEV[1]]
    res = {"n_dev": int(len(dev)), "n_conf": int(len(conf)), "cobertura_conf": round(float(conf["con_tiros"].mean()), 3) if len(conf) else 0.0}
    if res["cobertura_conf"] < 0.5 or len(conf) < 100:
        res["veredicto"] = "SIN_DATOS_SUFICIENTES"
        return res
    for name, x in (("desarrollo", dev), ("confirmacion", conf)):
        y = x["y"].to_numpy()
        res[name] = {"mejora": paired_bootstrap(_ll(P(x, "b"), y), _ll(P(x, "v"), y), x["date"]),
                     "ll_base": round(float(_ll(P(x, "b"), y).mean()), 5), "ll_tiros": round(float(_ll(P(x, "v"), y).mean()), 5),
                     "ece_base": round(ece_top(P(x, "b"), y), 4), "ece_tiros": round(ece_top(P(x, "v"), y), 4),
                     "acierto_base": round(float((P(x, "b").argmax(1) == y).mean()), 4),
                     "acierto_tiros": round(float((P(x, "v").argmax(1) == y).mean()), 4)}
    c = res["confirmacion"]
    res["veredicto"] = "PASA_SOLO_SOMBRA" if c["mejora"]["ic95_inf"] > 0 and c["ece_tiros"] <= c["ece_base"] + 0.005 else "NO_PASA"
    # descriptivo: casas
    with ThreadPoolExecutor(8) as ex:
        mk = list(ex.map(lambda t: odds(t[0], str(t[1]), Path("data/intl/odds")), zip(r["code"], r["event_id"])))
    b = pd.concat([r, pd.DataFrame(mk)], axis=1).dropna(subset=["mkt_H", "mkt_D", "mkt_A"]).reset_index(drop=True)
    lgt = lambda d: np.column_stack([np.log(d["mkt_H"] / d["mkt_D"]), np.log(d["mkt_A"] / d["mkt_D"])])
    X1 = lambda d: np.column_stack([lgt(d), d[EXTRA].to_numpy(float)])
    pa, pb, idx = [], [], []
    for s in sorted(b["temporada"].unique()):
        tr, te = b[b["temporada"] < s], b[b["temporada"] == s]
        if s <= DEV[1] or len(tr) < 300:
            continue
        m0 = LogisticRegression(C=10, max_iter=2000).fit(lgt(tr), tr["y"])
        m1 = LogisticRegression(C=10, max_iter=2000).fit(X1(tr), tr["y"])
        pa.append(m0.predict_proba(lgt(te))); pb.append(m1.predict_proba(X1(te))); idx += list(te.index)
    if idx:
        e = b.loc[idx]; ye = e["y"].to_numpy(); A, B = np.vstack(pa), np.vstack(pb)
        M = e[["mkt_H", "mkt_D", "mkt_A"]].to_numpy(float); M = M / M.sum(1, keepdims=True)
        res["casas_descriptivo"] = {"n": int(len(e)), "mejora": paired_bootstrap(_ll(A, ye), _ll(B, ye), e["date"]),
                                    "brecha": {"casas": round(float(_ll(M, ye).mean()), 5), "modelo": round(float(_ll(P(e, "b"), ye).mean()), 5),
                                               "modelo_con_tiros": round(float(_ll(P(e, "v"), ye).mean()), 5)}}
    return res


def main():
    res = {grp: run_group(grp) for grp in GRUPOS}
    Path("reports").mkdir(exist_ok=True)
    Path("reports/tiros_grupos.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
