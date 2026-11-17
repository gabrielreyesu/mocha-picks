"""Segunda prueba de copas nacionales (NUEVAS_LIGAS.md): variante v2 con categoría, copa y divisiones inferiores.

  python -m kalshi_intl.copas_v2 [ligas_v1.pkl]     # -> reports/copas_v2.json y resumen en pantalla
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

EXTRA_FEED = ["eng.4", "eng.5", "sco.2", "ned.2"]
REPORT = Path("reports/copas_v2.json")


def _ll(d):
    P = d[["p_H", "p_D", "p_A"]].to_numpy(float)
    y = d["res"].map({"H": 0, "D": 1, "A": 2}).to_numpy()
    return -np.log(np.clip(P[np.arange(len(d)), y], 1e-12, 1)), P, y


def _base(d, fin):
    """Frecuencias H/D/A de cada competición en sus temporadas anteriores (la referencia del protocolo)."""
    B = np.zeros((len(d), 3))
    for (code, t), idx in d.groupby(["code", "temporada"]).groups.items():
        h = fin[(fin["code"] == code) & (fin["date"] < pd.Timestamp(f"{t[:4]}-07-01"))]["res"]
        fr = np.array([(h == c).mean() for c in "HDA"]) if len(h) >= 100 else np.array([0.45, 0.27, 0.28])
        B[d.index.get_indexer(idx)] = fr
    y = d["res"].map({"H": 0, "D": 1, "A": 2}).to_numpy()
    return -np.log(np.clip(B[np.arange(len(d)), y], 1e-12, 1))


def rule(d, fin):
    from kalshi_nba.backtest import paired_bootstrap
    from .ligas import MAX_ECE, MIN_N, ece_top
    d = d.reset_index(drop=True)
    llm, P, y = _ll(d)
    bs = paired_bootstrap(_base(d, fin), llm, d["date"])
    e = ece_top(P, y)
    return {"n": int(len(d)), "logloss": round(float(llm.mean()), 4), "mejora": bs["mejora"], "ic95_inf": bs["ic95_inf"],
            "ic95_sup": bs["ic95_sup"], "ece": round(e, 4), "acierto": round(float((P.argmax(1) == y).mean()), 4),
            "pasa": bool(len(d) >= MIN_N and bs["ic95_inf"] > 0 and e <= MAX_ECE)}


def main(v1_pickle=None):
    from kalshi_nba.backtest import paired_bootstrap
    from .data import GROUPS, load_group
    from .ligas import MIN_PREV, evaluate
    from .model import CONFIGS, FEATS, FEATS_V2, NATIONAL_CUPS, IntlEngine, walk_forward
    g1 = pd.read_pickle(v1_pickle) if v1_pickle else load_group("ligas")
    G = GROUPS["ligas"]
    g2 = load_group("ligas")                       # ya incluye EXTRA_FEED (v2 adoptada)
    g1 = g1 if v1_pickle else g2[~g2["code"].isin(EXTRA_FEED)]
    f1 = IntlEngine(CONFIGS["ligas"]).process(g1)
    f2 = IntlEngine(CONFIGS["ligas"]).process(g2)
    r1 = walk_forward(f1, first_year=2020, features=FEATS, et_as_draw=True)
    r2 = walk_forward(f2, first_year=2020, features=FEATS_V2, et_as_draw=True)
    r1, r2 = r1[r1["temporada"] >= "2021/22"], r2[r2["temporada"] >= "2021/22"]
    fin = f2[f2["final"]].copy()
    fin["res"] = np.where(fin["hs"] > fin["as_"], "H", np.where(fin["hs"] == fin["as_"], "D", "A"))
    fin.loc[fin["status"].isin({"STATUS_FINAL_AET", "STATUS_FINAL_PEN"}), "res"] = "D"
    out = {}
    cups2 = r2[r2["code"].isin(NATIONAL_CUPS)]
    a = cups2[np.minimum(cups2["n_home"], cups2["n_away"]) >= MIN_PREV]
    out["copas_a_con_historial"] = rule(a, fin)
    out["copas_b_todos"] = rule(cups2, fin)
    c1 = r1[r1["code"].isin(NATIONAL_CUPS)]
    out["copas_v1_a_referencia"] = rule(c1[np.minimum(c1["n_home"], c1["n_away"]) >= MIN_PREV], fin)
    out["por_copa_b"] = {c: rule(d, fin) for c, d in cups2.groupby("code")}
    out["por_copa_a"] = {c: rule(d, fin) for c, d in a.groupby("code")}
    lg = set(G["league_targets"])
    m = r1[r1["code"].isin(lg)][["event_id", "date", "res", "p_H", "p_D", "p_A"]].merge(
        r2[r2["code"].isin(lg)][["event_id", "p_H", "p_D", "p_A"]], on="event_id", suffixes=("", "_2"))
    l1, _, _ = _ll(m)
    l2, _, _ = _ll(m.assign(p_H=m.p_H_2, p_D=m.p_D_2, p_A=m.p_A_2))
    out["ligas_v2_vs_v1"] = {"n": int(len(m)), **paired_bootstrap(l1, l2, m["date"])}
    out["por_competicion_v2"] = evaluate(walk_forward(f2, first_year=2020, features=FEATS_V2, et_as_draw=True), f2)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in ("copas_a_con_historial", "copas_b_todos", "copas_v1_a_referencia", "ligas_v2_vs_v1"):
        print(k, out[k])
    print("por copa (b):"); [print("  ", c, v) for c, v in out["por_copa_b"].items()]
    print("por copa (a):"); [print("  ", c, v) for c, v in out["por_copa_a"].items()]
    print(pd.DataFrame(out["por_competicion_v2"])[["code", "n", "mejora", "ic95_inf", "ece", "publicar"]].to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
