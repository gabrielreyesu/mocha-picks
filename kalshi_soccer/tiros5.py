"""Tiros en el modelo de las 5 grandes ligas (TIROS5_RESEARCH.md, issue #78).   python -m kalshi_soccer.tiros5"""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .engine import LEAGUES

HALF = 8.0
ALPHA = 1 - 0.5 ** (1 / HALF)
EXTRA = ["sot_diff", "sh_diff"]
DEV = ("2122", "2324")
SHOTS = {"HST": "h_sot", "AST": "a_sot", "HS": "h_sh", "AS": "a_sh"}


def load_shots(cache_dir: str = "data/raw") -> pd.DataFrame:
    """Tiros por partido desde los CSV ya descargados por load_history."""
    parts = []
    for league, code in LEAGUES.items():
        for p in sorted(Path(cache_dir).glob(f"*_{code}.csv")):
            raw = pd.read_csv(io.BytesIO(p.read_bytes()), on_bad_lines="skip", encoding_errors="replace")
            if not set(SHOTS) <= set(raw.columns):
                continue
            d = raw[["Date", "HomeTeam", "AwayTeam"] + list(SHOTS)].rename(columns={"Date": "date", "HomeTeam": "home", "AwayTeam": "away", **SHOTS})
            d["date"] = pd.to_datetime(d["date"], dayfirst=True, format="mixed", errors="coerce")
            d["competition"] = league
            parts.append(d.dropna(subset=["date", "home", "away"]))
    return pd.concat(parts, ignore_index=True).drop_duplicates(["date", "competition", "home", "away"])


def shot_features(feats: pd.DataFrame, shots: pd.DataFrame) -> pd.DataFrame:
    """sot_diff y sh_diff pre-partido (solo días anteriores), igual que kalshi_intl.tiros (variante B)."""
    d = feats[["date", "competition", "season", "home", "away"]].merge(shots, on=["date", "competition", "home", "away"], how="left")
    st, lg, out = {}, {}, []

    def get(key, season, L):
        x = st.get(key)
        if x is None:
            x = st[key] = [L["sot"], L["sot"], L["sh"], L["sh"], season]
        if x[4] != season:
            x[:4] = [0.5 * x[0] + 0.5 * L["sot"], 0.5 * x[1] + 0.5 * L["sot"], 0.5 * x[2] + 0.5 * L["sh"], 0.5 * x[3] + 0.5 * L["sh"]]
            x[4] = season
        return x
    for date, day in d.groupby("date", sort=True):
        for r in day.itertuples():
            L = lg.setdefault(r.competition, {"sot": 4.3, "sh": 12.5})
            h, a = get((r.competition, r.home), r.season, L), get((r.competition, r.away), r.season, L)
            out.append({"idx": r.Index, "sot_diff": (h[0] - h[1]) - (a[0] - a[1]), "sh_diff": (h[2] - h[3]) - (a[2] - a[3])})
        for r in day.itertuples():
            if any(pd.isna(getattr(r, c)) for c in SHOTS.values()):
                continue
            L = lg[r.competition]
            for team, me, op in ((r.home, (r.h_sot, r.h_sh), (r.a_sot, r.a_sh)), (r.away, (r.a_sot, r.a_sh), (r.h_sot, r.h_sh))):
                x = get((r.competition, team), r.season, L)
                for i, v in enumerate((me[0], op[0], me[1], op[1])):
                    x[i] = (1 - ALPHA) * x[i] + ALPHA * float(v)
            L["sot"] = 0.998 * L["sot"] + 0.002 * (r.h_sot + r.a_sot) / 2
            L["sh"] = 0.998 * L["sh"] + 0.002 * (r.h_sh + r.a_sh) / 2
    o = pd.DataFrame(out).set_index("idx").sort_index()
    return o.set_axis(feats.index)


def _ll(P, y):
    P = np.asarray(P, float); P = P / P.sum(1, keepdims=True)
    return -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))


def main():
    from sklearn.linear_model import LogisticRegression
    from kalshi_nba.backtest import paired_bootstrap
    from kalshi_intl.ligas import ece_top
    from .data import load_history
    from .engine import SoccerEngine
    from .models import CLASSES, NUM_1X2, Soccer1X2
    hist = load_history(start_year=2015)
    feats = SoccerEngine().process(hist).reset_index(drop=True)
    shots = load_shots()
    cov = float(feats[["date", "competition", "home", "away"]].merge(shots, how="left")["h_sot"].notna().mean())
    feats[EXTRA] = shot_features(feats, shots)
    sc = feats[feats["target"].notna()].copy()
    sc["y"] = sc["target"].map({c: i for i, c in enumerate(CLASSES)})        # orden A, D, H
    rows = []
    for s in [x for x in sorted(sc["season"].unique()) if x >= DEV[0]]:
        tr, te = sc[sc["season"] < s], sc[sc["season"] == s]
        b, v = Soccer1X2().fit(tr), Soccer1X2(num_cols=NUM_1X2 + EXTRA).fit(tr)
        rec = te[["date", "season", "y"] + [f"mkt_{c}" for c in CLASSES] + EXTRA].copy()
        rec[["b_A", "b_D", "b_H"]] = b.predict_proba(te); rec[["v_A", "v_D", "v_H"]] = v.predict_proba(te)
        rows.append(rec)
    r = pd.concat(rows)
    P = lambda d, p: d[[f"{p}_A", f"{p}_D", f"{p}_H"]].to_numpy(float)
    res = {"cobertura_tiros": round(cov, 3)}
    for name, x in (("desarrollo", r[r["season"] <= DEV[1]]), ("confirmacion", r[r["season"] > DEV[1]])):
        y = x["y"].to_numpy()
        res[name] = {"n": int(len(x)), "mejora": paired_bootstrap(_ll(P(x, "b"), y), _ll(P(x, "v"), y), x["date"]),
                     "ll_base": round(float(_ll(P(x, "b"), y).mean()), 5), "ll_tiros": round(float(_ll(P(x, "v"), y).mean()), 5),
                     "ece_base": round(ece_top(P(x, "b"), y), 4), "ece_tiros": round(ece_top(P(x, "v"), y), 4),
                     "acierto_base": round(float((P(x, "b").argmax(1) == y).mean()), 4),
                     "acierto_tiros": round(float((P(x, "v").argmax(1) == y).mean()), 4)}
    c = res["confirmacion"]
    pasa = c["mejora"]["ic95_inf"] > 0 and c["ece_tiros"] <= c["ece_base"] + 0.005
    # frente a las casas (cuotas del CSV, sin margen)
    m = sc.dropna(subset=[f"mkt_{c}" for c in CLASSES]).copy()
    lgt = lambda d: np.column_stack([np.log(d["mkt_H"] / d["mkt_D"]), np.log(d["mkt_A"] / d["mkt_D"])])
    pa, pb, idx = [], [], []
    for s in sorted(m["season"].unique()):
        if s <= DEV[1]:
            continue
        tr, te = m[m["season"] < s], m[m["season"] == s]
        X1 = lambda d: np.column_stack([lgt(d), d[EXTRA].to_numpy(float)])
        m0 = LogisticRegression(C=10, max_iter=2000).fit(lgt(tr), tr["y"])
        m1 = LogisticRegression(C=10, max_iter=2000).fit(X1(tr), tr["y"])
        pa.append(m0.predict_proba(lgt(te))); pb.append(m1.predict_proba(X1(te))); idx += list(te.index)
    e = m.loc[idx]; ye = e["y"].to_numpy(); A, B = np.vstack(pa), np.vstack(pb)
    res["frente_a_casas"] = {"n": int(len(e)), "casas_recal": round(float(_ll(A, ye).mean()), 5), "casas_mas_tiros": round(float(_ll(B, ye).mean()), 5),
                             "mejora": paired_bootstrap(_ll(A, ye), _ll(B, ye), e["date"])}
    cc = r[r["season"] > DEV[1]].dropna(subset=["mkt_A", "mkt_D", "mkt_H"]); yc = cc["y"].to_numpy()
    res["brecha_confirmacion"] = {"n": int(len(cc)), "casas": round(float(_ll(P(cc, "mkt"), yc).mean()), 5),
                                  "modelo": round(float(_ll(P(cc, "b"), yc).mean()), 5), "modelo_con_tiros": round(float(_ll(P(cc, "v"), yc).mean()), 5)}
    res["veredicto"] = {"frente_al_modelo": "PASA_SOLO_SOMBRA" if pasa else "NO_PASA",
                        "frente_a_casas": "APORTA" if res["frente_a_casas"]["mejora"]["ic95_inf"] > 0 else "NO_APORTA"}
    Path("reports").mkdir(exist_ok=True)
    Path("reports/tiros5.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
