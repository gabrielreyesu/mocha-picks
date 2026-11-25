"""Continuidad del once en las 5 grandes ligas (XI_LIGAS_RESEARCH.md, issue #68).

python -m kalshi_lineup.xi_ligas  -> reports/xi_ligas.json
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from .box import load_boxes
from .soccer_xi import SUMMARY_SOCCER, XIRater, parse_soccer_summary

BIG5 = ["eng.1", "esp.1", "ita.1", "ger.1", "fra.1"]
VARIANTS = {"A_continuidad": ["xi_cont"], "B_continuidad_y_ataque": ["xi_cont", "xi_ga"]}
CHOSEN = "A_continuidad"                       # fijada en el protocolo
DEV = ("2021/22", "2023/24")
SINCE = "2020-07-01"


def _ll(P, y):
    P = np.asarray(P, float)
    P = P / P.sum(1, keepdims=True)
    return -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))


def main():
    from sklearn.linear_model import LogisticRegression
    from kalshi_nba.backtest import paired_bootstrap
    from kalshi_intl.data import load_group
    from kalshi_intl.ligas import ece_top
    from kalshi_intl.model import CONFIGS, GROUP_FEATURES, IntlEngine, walk_forward
    from kalshi_intl.odds import fetch as odds

    g = load_group("ligas", verbose=False)
    g["event_id"] = g["event_id"].astype(str)
    fin = g[g["final"] & g["code"].isin(BIG5) & (g["date"] >= pd.Timestamp(SINCE))]
    boxes = {}
    for code, part in fin.groupby("code"):
        boxes.update(load_boxes(part["event_id"], cache_dir=f"data/intl_box/{code}", workers=8,
                                url=SUMMARY_SOCCER.format(code=code), parser=parse_soccer_summary))
    cov = {c: round(float(p["event_id"].isin(boxes).mean()), 3) for c, p in fin.groupby("code")}
    tot = round(float(fin["event_id"].isin(boxes).mean()), 3)
    print("Cobertura de onces:", tot, cov)
    res = {"cobertura": {"total": tot, "por_liga": cov, "partidos": int(len(fin))}}
    if tot < 0.6:
        res["veredicto"] = "SIN_COBERTURA"
        Path("reports/xi_ligas.json").write_text(json.dumps(res, indent=1)); print(res); return

    f = IntlEngine(CONFIGS["ligas"]).process(g)
    f["event_id"] = f["event_id"].astype(str)
    xi = XIRater().process(g[g["code"].isin(BIG5)], boxes)          # solo ligas: los onces de copas no se descargan
    f = f.merge(xi, on="event_id", how="left")
    for c in ("xi_cont", "xi_ga", "xi_ok"):
        f[c] = f[c].fillna(0.0)
    f["eval"] = f["code"].isin(BIG5)
    base = GROUP_FEATURES["ligas"]
    r0 = walk_forward(f, first_year=2021, features=base, eval_col="eval", et_as_draw=True)
    oos = r0[["event_id", "date", "code", "temporada", "res", "p_H", "p_D", "p_A"]].rename(columns={c: f"b_{c}" for c in ("p_H", "p_D", "p_A")})
    for name, extra in VARIANTS.items():
        r = walk_forward(f, first_year=2021, features=base + extra, eval_col="eval", et_as_draw=True)
        oos = oos.merge(r[["event_id", "p_H", "p_D", "p_A"]].rename(columns={c: f"{name}_{c}" for c in ("p_H", "p_D", "p_A")}), on="event_id")
    oos = oos[oos["temporada"] >= DEV[0]].merge(f[["event_id", "xi_cont", "xi_ga", "xi_ok"]], on="event_id").reset_index(drop=True)
    oos["y"] = oos["res"].map({"H": 0, "D": 1, "A": 2})
    P = lambda d, pre: d[[f"{pre}_p_H", f"{pre}_p_D", f"{pre}_p_A"]].to_numpy(float)
    dev, conf = oos[oos["temporada"] <= DEV[1]], oos[oos["temporada"] > DEV[1]]
    res.update(n_dev=int(len(dev)), n_conf=int(len(conf)), once_valido_oos=round(float(oos["xi_ok"].mean()), 3), desarrollo={})
    for name in VARIANTS:
        yd = dev["y"].to_numpy()
        res["desarrollo"][name] = paired_bootstrap(_ll(P(dev, "b"), yd), _ll(P(dev, name), yd), dev["date"])
    yc = conf["y"].to_numpy()
    c1 = {"mejora": paired_bootstrap(_ll(P(conf, "b"), yc), _ll(P(conf, CHOSEN), yc), conf["date"]),
          "ll_base": round(float(_ll(P(conf, "b"), yc).mean()), 5), "ll_variante": round(float(_ll(P(conf, CHOSEN), yc).mean()), 5),
          "ece_base": round(ece_top(P(conf, "b"), yc), 4), "ece_variante": round(ece_top(P(conf, CHOSEN), yc), 4),
          "descriptivo_B": paired_bootstrap(_ll(P(conf, "b"), yc), _ll(P(conf, "B_continuidad_y_ataque"), yc), conf["date"])}
    res["confirmacion_modelo"] = c1
    pasa1 = c1["mejora"]["ic95_inf"] > 0 and c1["ece_variante"] <= c1["ece_base"] + 0.005

    # frente a las casas
    with ThreadPoolExecutor(8) as ex:
        mk = list(ex.map(lambda t: odds(t[0], t[1], Path("data/intl/odds")), zip(oos["code"], oos["event_id"])))
    b = pd.concat([oos, pd.DataFrame(mk)], axis=1).dropna(subset=["mkt_H", "mkt_D", "mkt_A"]).reset_index(drop=True)
    lgt = lambda d: np.column_stack([np.log(d["mkt_H"] / d["mkt_D"]), np.log(d["mkt_A"] / d["mkt_D"])])
    X1 = lambda d: np.column_stack([lgt(d), d["xi_cont"].to_numpy(float)])
    pa, pb, idx = [], [], []
    for s in sorted(b["temporada"].unique()):
        if s <= DEV[1]:
            continue
        tr, te = b[b["temporada"] < s], b[b["temporada"] == s]
        m0 = LogisticRegression(C=10, max_iter=1000).fit(lgt(tr), tr["y"])
        m1 = LogisticRegression(C=10, max_iter=1000).fit(X1(tr), tr["y"])
        pa.append(m0.predict_proba(lgt(te))); pb.append(m1.predict_proba(X1(te))); idx += list(te.index)
    e = b.loc[idx]; ye = e["y"].to_numpy(); A, B = np.vstack(pa), np.vstack(pb)
    c2 = {"n": int(len(e)), "casas_recal": round(float(_ll(A, ye).mean()), 5), "casas_mas_xi": round(float(_ll(B, ye).mean()), 5),
          "mejora": paired_bootstrap(_ll(A, ye), _ll(B, ye), e["date"])}
    # descriptivo: solo partidos con once válido
    ok = (e["xi_ok"] == 1).to_numpy()
    if ok.sum() > 100:
        c2["solo_con_once"] = paired_bootstrap(_ll(A[ok], ye[ok]), _ll(B[ok], ye[ok]), e["date"][ok])
    res["confirmacion_casas"] = c2
    pasa2 = c2["mejora"]["ic95_inf"] > 0
    M = e[["mkt_H", "mkt_D", "mkt_A"]].to_numpy(float)
    res["brecha_confirmacion"] = {"casas": round(float(_ll(M, ye).mean()), 5), "modelo": round(float(_ll(P(e, "b"), ye).mean()), 5),
                                  "modelo_mas_xi": round(float(_ll(P(e, CHOSEN), ye).mean()), 5)}
    res["veredicto"] = {"frente_al_modelo": "PASA_SOLO_SOMBRA" if pasa1 else "NO_PASA",
                        "frente_a_casas": "PASA_SOLO_SOMBRA" if pasa2 else "NO_PASA"}
    Path("reports").mkdir(exist_ok=True)
    Path("reports/xi_ligas.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
