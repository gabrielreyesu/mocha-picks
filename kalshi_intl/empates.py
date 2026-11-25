"""Ajuste del empate por liga (EMPATES_RESEARCH.md, issue #71).   python -m kalshi_intl.empates -> reports/empates.json"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

LAM, MIN_N = 50.0, 300
DEV = ("2021/22", "2023/24")
BIG5 = ["eng.1", "esp.1", "ita.1", "ger.1", "fra.1"]


def shift(P: np.ndarray, delta) -> np.ndarray:
    Q = np.asarray(P, float).copy()
    Q[:, 1] *= np.exp(delta)
    return Q / Q.sum(1, keepdims=True)


def _ll(P, y):
    P = np.asarray(P, float); P = P / P.sum(1, keepdims=True)
    return -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))


def fit_delta(P: np.ndarray, y: np.ndarray, lam=LAM, min_n=MIN_N) -> float:
    if len(y) < min_n:
        return 0.0
    f = lambda d: _ll(shift(P, d), y).sum() + lam * d * d
    return float(minimize_scalar(f, bounds=(-1, 1), method="bounded").x)


def adjust(d: pd.DataFrame, cols=("p_H", "p_D", "p_A")) -> np.ndarray:
    """Probabilidades ajustadas, temporada a temporada, con δ estimado solo con temporadas anteriores de la misma liga."""
    out = d[list(cols)].to_numpy(float).copy()
    for code, x in d.groupby("code"):
        for s in sorted(x["temporada"].unique()):
            tr, te = x[x["temporada"] < s], x[x["temporada"] == s]
            delta = fit_delta(tr[list(cols)].to_numpy(float), tr["y"].to_numpy())
            out[d.index.get_indexer(te.index)] = shift(te[list(cols)].to_numpy(float), delta)
    return out


def main():
    from kalshi_nba.backtest import paired_bootstrap
    from kalshi_intl.data import GROUPS, load_group
    from kalshi_intl.ligas import ece_top
    from kalshi_intl.model import CONFIGS, GROUP_FEATURES, IntlEngine, walk_forward
    from kalshi_intl.odds import fetch as odds
    g = load_group("ligas", verbose=False)
    f = IntlEngine(CONFIGS["ligas"]).process(g)
    f["eval"] = f["code"].isin(set(BIG5) | set(GROUPS["ligas"]["league_targets"]))
    r = walk_forward(f, first_year=2020, features=GROUP_FEATURES["ligas"], eval_col="eval", et_as_draw=True)
    r = r.reset_index(drop=True)
    r["y"] = r["res"].map({"H": 0, "D": 1, "A": 2})
    r = r.dropna(subset=["y"]).reset_index(drop=True); r["y"] = r["y"].astype(int)
    adj = adjust(r)
    r[["a_H", "a_D", "a_A"]] = adj
    P = lambda d, c: d[[f"{c}_H", f"{c}_D", f"{c}_A"]].to_numpy(float)
    ev = r[r["temporada"] >= DEV[0]]
    dev, conf = ev[ev["temporada"] <= DEV[1]], ev[ev["temporada"] > DEV[1]]
    res = {"n_dev": int(len(dev)), "n_conf": int(len(conf))}
    for name, x in (("desarrollo", dev), ("confirmacion", conf)):
        y = x["y"].to_numpy()
        res[name] = {"mejora": paired_bootstrap(_ll(P(x, "p"), y), _ll(P(x, "a"), y), x["date"]),
                     "ll_base": round(float(_ll(P(x, "p"), y).mean()), 5), "ll_ajuste": round(float(_ll(P(x, "a"), y).mean()), 5),
                     "ece_base": round(ece_top(P(x, "p"), y), 4), "ece_ajuste": round(ece_top(P(x, "a"), y), 4)}
    # deltas finales por liga (con todo hasta la confirmación) y empate real frente a previsto
    res["por_liga"] = {c: {"n": int(len(x)), "empate_real": round(float((x["y"] == 1).mean()), 4),
                           "empate_modelo": round(float(x["p_D"].mean()), 4),
                           "delta": round(fit_delta(P(x, "p"), x["y"].to_numpy()), 3)} for c, x in ev.groupby("code")}
    c = res["confirmacion"]
    res["veredicto"] = "PASA_SOLO_SOMBRA" if c["mejora"]["ic95_inf"] > 0 and c["ece_ajuste"] <= c["ece_base"] + 0.005 else "NO_PASA"
    # descriptivo: casas de las 5 grandes
    b = r[r["code"].isin(BIG5)].reset_index(drop=True)
    with ThreadPoolExecutor(8) as ex:
        mk = list(ex.map(lambda t: odds(t[0], str(t[1]), Path("data/intl/odds")), zip(b["code"], b["event_id"])))
    b = pd.concat([b, pd.DataFrame(mk)], axis=1).dropna(subset=["mkt_H", "mkt_D", "mkt_A"]).reset_index(drop=True)
    b[["m_H", "m_D", "m_A"]] = b[["mkt_H", "mkt_D", "mkt_A"]].to_numpy(float)
    b[["ma_H", "ma_D", "ma_A"]] = adjust(b, ("m_H", "m_D", "m_A"))
    bc = b[b["temporada"] > DEV[1]]; yb = bc["y"].to_numpy()
    res["casas_descriptivo"] = {"n": int(len(bc)), "mejora": paired_bootstrap(_ll(P(bc, "m"), yb), _ll(P(bc, "ma"), yb), bc["date"])}
    Path("reports").mkdir(exist_ok=True)
    Path("reports/empates.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
