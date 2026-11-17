"""Tiros y tiros a puerta en el modelo de fútbol (TIROS_RESEARCH.md).   python -m kalshi_intl.tiros  -> reports/tiros.json"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HALF = 8.0
ALPHA = 1 - 0.5 ** (1 / HALF)
BIG5 = ["eng.1", "esp.1", "ita.1", "ger.1", "fra.1"]
VARIANTS = {"A_tp": ["sot_diff"], "B_tp_tiros": ["sot_diff", "sh_diff"], "C_tp_cuota": ["sot_diff", "sot_share_diff"]}
DEV = ("2021/22", "2023/24")


def load_stats(codes, first=(2018, 7)):
    from kalshi_nba.data import _json as getter
    from kalshi_nba.estadisticas import fetch_soccer
    now = pd.Timestamp.now()
    yms, (y, m) = [], first
    while (y, m) <= (now.year, now.month):
        yms.append(f"{y}{m:02d}"); y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda j: fetch_soccer(j[0], j[1], getter), [(c, ym) for c in codes for ym in yms]))
    ev = {}
    for rows in res:
        for r in rows:
            ev[r["id"]] = r
    return ev


def shot_features(f: pd.DataFrame, ev: dict) -> pd.DataFrame:
    """Variables de tiros por partido de f (event_id, date, home_id, away_id), solo con días anteriores."""
    st = {}                                                # equipo -> [sotf, sota, shf, sha, temporada]
    lg = {"sot": 4.3, "sh": 12.5}
    out = []

    def get(t, season):
        x = st.get(t)
        if x is None:
            x = st[t] = [lg["sot"], lg["sot"], lg["sh"], lg["sh"], season]
        if x[4] != season:
            x[:4] = [0.5 * x[0] + 0.5 * lg["sot"], 0.5 * x[1] + 0.5 * lg["sot"], 0.5 * x[2] + 0.5 * lg["sh"], 0.5 * x[3] + 0.5 * lg["sh"]]
            x[4] = season
        return x
    for date, day in f.sort_values("date").groupby("date", sort=True):
        season = date.year if date.month >= 7 else date.year - 1
        for r in day.itertuples():
            h, a = get(r.home_id, season), get(r.away_id, season)
            share = lambda x: x[0] / max(x[0] + x[1], 1e-6)
            out.append({"event_id": r.event_id, "sot_diff": (h[0] - h[1]) - (a[0] - a[1]), "sh_diff": (h[2] - h[3]) - (a[2] - a[3]),
                        "sot_share_diff": share(h) - share(a)})
        for r in day.itertuples():
            e = ev.get(str(r.event_id))
            if not e or not r.final:
                continue
            H, A = e["h"], e["a"]
            if H.get("sot") is None or A.get("sot") is None or H.get("sh") is None or A.get("sh") is None:
                continue
            for t, me, op in ((r.home_id, H, A), (r.away_id, A, H)):
                x = get(t, season)
                for i, v in enumerate((me["sot"], op["sot"], me["sh"], op["sh"])):
                    x[i] = (1 - ALPHA) * x[i] + ALPHA * v
            lg["sot"] = 0.998 * lg["sot"] + 0.002 * (H["sot"] + A["sot"]) / 2
            lg["sh"] = 0.998 * lg["sh"] + 0.002 * (H["sh"] + A["sh"]) / 2
    return pd.DataFrame(out)


def _ll(P, y):
    P = np.asarray(P, float)
    return -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))


def main():
    from kalshi_nba.backtest import paired_bootstrap
    from kalshi_intl.data import GROUPS, load_group
    from kalshi_intl.ligas import ece_top
    from kalshi_intl.model import CONFIGS, GROUP_FEATURES, IntlEngine, walk_forward
    from kalshi_intl.odds import fetch as odds
    G = GROUPS["ligas"]
    g = load_group("ligas", verbose=False)
    f = IntlEngine(CONFIGS["ligas"]).process(g)
    ev = load_stats(sorted(set(f["code"])))
    sf = shot_features(f, ev)
    f = f.merge(sf, on="event_id", how="left")
    cov = float(f.loc[f["final"], "event_id"].astype(str).map(lambda e: ev.get(e, {}).get("h", {}).get("sot") is not None).mean())
    lg_codes = set(BIG5) | set(G["league_targets"])
    f["eval"] = f["code"].isin(lg_codes)
    base_feats = GROUP_FEATURES["ligas"]
    r0 = walk_forward(f, first_year=2020, features=base_feats, eval_col="eval", et_as_draw=True)
    keep = ["event_id", "date", "code", "temporada", "res", "p_H", "p_D", "p_A"]
    oos = r0[keep].rename(columns={c: f"b_{c}" for c in ("p_H", "p_D", "p_A")})
    for name, extra in VARIANTS.items():
        r = walk_forward(f, first_year=2020, features=base_feats + extra, eval_col="eval", et_as_draw=True)
        oos = oos.merge(r[["event_id", "p_H", "p_D", "p_A"]].rename(columns={c: f"{name}_{c}" for c in ("p_H", "p_D", "p_A")}), on="event_id")
    oos = oos[oos["temporada"] >= DEV[0]].reset_index(drop=True)
    oos["y"] = oos["res"].map({"H": 0, "D": 1, "A": 2})
    y = oos["y"].to_numpy()
    P = lambda d, pre: d[[f"{pre}_p_H", f"{pre}_p_D", f"{pre}_p_A"]].to_numpy(float)
    dev, conf = oos[oos["temporada"] <= DEV[1]], oos[oos["temporada"] > DEV[1]]
    res = {"cobertura_tiros": round(cov, 3), "n_dev": int(len(dev)), "n_conf": int(len(conf)), "desarrollo": {}}
    for name in VARIANTS:
        yd = dev["y"].to_numpy()
        res["desarrollo"][name] = paired_bootstrap(_ll(P(dev, "b"), yd), _ll(P(dev, name), yd), dev["date"])
    chosen = max(VARIANTS, key=lambda n: res["desarrollo"][n]["mejora"])
    yc = conf["y"].to_numpy()
    res["elegida"] = chosen
    res["confirmacion"] = {"mejora": paired_bootstrap(_ll(P(conf, "b"), yc), _ll(P(conf, chosen), yc), conf["date"]),
                           "ece_base": round(ece_top(P(conf, "b"), yc), 4), "ece_variante": round(ece_top(P(conf, chosen), yc), 4),
                           "ll_base": round(float(_ll(P(conf, "b"), yc).mean()), 5), "ll_variante": round(float(_ll(P(conf, chosen), yc).mean()), 5)}
    c = res["confirmacion"]
    res["veredicto"] = "SUPERA_CRITERIO_SOLO_SOMBRA" if c["mejora"]["ic95_inf"] > 0 and c["ece_variante"] <= c["ece_base"] + 0.005 else "NO_SUPERA_CRITERIO"
    # frente al mercado: 5 grandes ligas con cuotas de casas
    b5 = oos[oos["code"].isin(BIG5)].copy()
    with ThreadPoolExecutor(8) as ex:
        mk = list(ex.map(lambda t: odds(t[0], t[1], Path("data/intl/odds")), zip(b5["code"], b5["event_id"].astype(str))))
    b5 = pd.concat([b5.reset_index(drop=True), pd.DataFrame(mk)], axis=1).dropna(subset=["mkt_H", "mkt_D", "mkt_A"])
    b5 = b5.merge(f[["event_id"] + VARIANTS[chosen]], on="event_id")
    from sklearn.linear_model import LogisticRegression
    yb = b5["y"].to_numpy()
    lgt = lambda d: np.column_stack([np.log(d["mkt_H"] / d["mkt_D"]), np.log(d["mkt_A"] / d["mkt_D"])])
    pa, pb, idx = [], [], []
    for s in sorted(b5["temporada"].unique()):
        tr, te = b5[b5["temporada"] < s], b5[b5["temporada"] == s]
        if len(tr) < 1000:
            continue
        m0 = LogisticRegression(C=10, max_iter=1000).fit(lgt(tr), tr["y"])
        X1 = lambda d: np.column_stack([lgt(d)] + [d[c].to_numpy(float) for c in VARIANTS[chosen]])
        m1 = LogisticRegression(C=10, max_iter=1000).fit(X1(tr), tr["y"])
        pa.append(m0.predict_proba(lgt(te))); pb.append(m1.predict_proba(X1(te))); idx += list(te.index)
    if idx:
        e = b5.loc[idx]; ye = e["y"].to_numpy()
        A, B = np.vstack(pa), np.vstack(pb)
        res["frente_al_mercado"] = {"n": int(len(e)), "casas_recal": round(float(_ll(A, ye).mean()), 5), "casas_mas_tiros": round(float(_ll(B, ye).mean()), 5),
                                    "mejora": paired_bootstrap(_ll(A, ye), _ll(B, ye), e["date"])}
    M = b5[["mkt_H", "mkt_D", "mkt_A"]].to_numpy(float); M = M / M.sum(1, keepdims=True)
    res["brecha_5_grandes"] = {"n": int(len(b5)), "casas": round(float(_ll(M, yb).mean()), 5),
                               "modelo_base": round(float(_ll(P(b5, "b"), yb).mean()), 5),
                               "modelo_con_tiros": round(float(_ll(P(b5, chosen), yb).mean()), 5)}
    Path("reports").mkdir(exist_ok=True)
    Path("reports/tiros.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
