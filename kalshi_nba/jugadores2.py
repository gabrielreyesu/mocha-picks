"""Modelo de jugadores NBA con minutos, rival y bajas (JUGADORES2_RESEARCH.md, issue #82).

python -m kalshi_nba.jugadores2  -> reports/jugadores2.json
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import nbinom

STATS = ("pts", "reb", "ast")
STAT_NAME = {"Puntos": "pts", "Rebotes": "reb", "Asistencias": "ast"}
D_MIN, D_RATE, D_OPP = 0.5 ** (1 / 5), 0.5 ** (1 / 10), 0.5 ** (1 / 15)
PRIOR_MIN = 150.0
MIN_GAMES = 4
CUTOFF = pd.Timestamp("2026-11-17", tz="UTC")       # primer día con picks de Kalshi: entrenamiento estrictamente antes


def player_games(first_season: int = 2022, box_dir: str = "data/nba/box") -> pd.DataFrame:
    """Una fila por jugador listado en el box score (jugó o no), con la hora del partido y el rival."""
    from kalshi_lineup.box import load_boxes
    from kalshi_nba.data import load_league
    g = load_league("nba", first_season=first_season, with_odds=False, verbose=False)
    # Por la hora y no por el estado: el estado en caché de días recientes puede seguir como «programado».
    # Si un partido no se jugó, su box score no trae jugadores con minutos y no aporta nada.
    dead = {"STATUS_CANCELED", "STATUS_POSTPONED"}
    g = g[~g["status"].isin(dead) & (pd.to_datetime(g["kickoff_utc"], utc=True) < pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=4))]
    boxes = load_boxes(g["event_id"].astype(str), cache_dir=box_dir, workers=8)
    kick = dict(zip(g["event_id"].astype(str), pd.to_datetime(g["kickoff_utc"], utc=True)))
    rows = []
    for e, b in boxes.items():
        teams = sorted({p.get("team_id") for p in b.get("players", []) if p.get("team_id")})
        if len(teams) != 2 or e not in kick:
            continue
        for p in b["players"]:
            opp = teams[1] if p["team_id"] == teams[0] else teams[0]
            rows.append({"event_id": e, "t": kick[e], "team_id": p["team_id"], "opp_id": opp, "pid": p.get("pid"), "name": p.get("name"),
                         "played": bool(not p.get("dnp") and (p.get("min") or 0) > 0), "out": bool(p.get("dnp") and p.get("avail") is False),
                         "min": float(p.get("min") or 0), **{s: (float(p[s]) if p.get(s) is not None else np.nan) for s in STATS}})
    return pd.DataFrame(rows).sort_values(["t", "event_id"]).reset_index(drop=True)


def pregame(pg: pd.DataFrame) -> pd.DataFrame:
    """Proyección ANTES de cada partido para cada jugador listado (solo usa partidos anteriores)."""
    mins, nmin = defaultdict(float), defaultdict(float)          # promedio exponencial de minutos (suma ponderada y pesos)
    S = defaultdict(lambda: defaultdict(float)); M = defaultdict(float)
    ppg = defaultdict(float)                                      # puntos recientes por partido (para las bajas)
    ngames = defaultdict(int)
    allow = defaultdict(lambda: defaultdict(float)); wallow = defaultdict(float)
    L = {"rate": {s: 0.0 for s in STATS}, "min": 0.0, "team_game": {s: 0.0 for s in STATS}, "n_tg": 0}
    out = []
    for e, gm in pg.groupby("event_id", sort=False):
        lg_rate = {s: (L["rate"][s] / L["min"] if L["min"] > 0 else {"pts": 0.47, "reb": 0.18, "ast": 0.11}[s]) for s in STATS}
        lg_tg = {s: (L["team_game"][s] / L["n_tg"] if L["n_tg"] else {"pts": 113.0, "reb": 44.0, "ast": 26.0}[s]) for s in STATS}
        team_tot = gm.groupby("team_id")["pid"].apply(lambda x: sum(ppg[p] for p in x)).to_dict()
        team_out = gm[gm["out"]].groupby("team_id")["pid"].apply(lambda x: sum(ppg[p] for p in x)).to_dict()
        for r in gm.itertuples():
            row = {"event_id": e, "t": r.t, "pid": r.pid, "name": r.name, "played": r.played, "n": ngames[r.pid],
                   "min_pre": mins[r.pid] / nmin[r.pid] if nmin[r.pid] else np.nan,
                   "out_share": team_out.get(r.team_id, 0.0) / team_tot[r.team_id] if team_tot.get(r.team_id) else 0.0}
            for s in STATS:
                rate = (S[r.pid][s] + PRIOR_MIN * lg_rate[s]) / (M[r.pid] + PRIOR_MIN)
                opp = (allow[r.opp_id][s] / wallow[r.opp_id]) / lg_tg[s] if wallow[r.opp_id] else 1.0
                row[f"mu_{s}"] = row["min_pre"] * rate * opp
                row[s] = getattr(r, s)
            out.append(row)
        # actualizar con el resultado del partido
        for r in gm[gm["played"]].itertuples():
            mins[r.pid] = D_MIN * mins[r.pid] + r.min; nmin[r.pid] = D_MIN * nmin[r.pid] + 1
            M[r.pid] = D_RATE * M[r.pid] + r.min
            for s in STATS:
                v = getattr(r, s)
                if not np.isnan(v):
                    S[r.pid][s] = D_RATE * S[r.pid][s] + v
                    L["rate"][s] += v
            ppg[r.pid] = D_RATE * ppg[r.pid] + (1 - D_RATE) * (r.pts if not np.isnan(r.pts) else 0.0)
            ngames[r.pid] += 1
            L["min"] += r.min
        for team, tg in gm[gm["played"]].groupby("team_id"):
            opp = tg["opp_id"].iloc[0]
            for s in STATS:
                allow[opp][s] = D_OPP * allow[opp][s] + tg[s].sum()
                L["team_game"][s] += tg[s].sum()
            wallow[opp] = D_OPP * wallow[opp] + 1
            L["n_tg"] += 1
    return pd.DataFrame(out)


def fit(pre: pd.DataFrame) -> dict:
    """Dispersión de la binomial negativa por estadística y β de las bajas (solo con datos de entrenamiento)."""
    tr = pre[pre["played"] & (pre["n"] >= MIN_GAMES) & (pre["t"] < CUTOFF)]
    par = {}
    for s in STATS:
        d = tr.dropna(subset=[s, f"mu_{s}"]); mu, x = d[f"mu_{s}"].to_numpy(), d[s].to_numpy()
        alpha = max(float(((x - mu) ** 2 - mu).sum() / (mu ** 2).sum()), 1e-3)
        o = d["out_share"].to_numpy(); k = o > 0
        beta = float((o[k] * (x[k] - mu[k])).sum() / (o[k] ** 2 * mu[k]).sum()) if k.sum() > 100 else 0.0
        par[s] = {"alpha": round(alpha, 4), "beta": round(beta, 3), "n": int(len(d))}
    return par


def p_over(mu: float, line: float, alpha: float) -> float:
    """P(X >= línea) con binomial negativa de media mu y varianza mu + alpha·mu²."""
    n = 1 / alpha
    return float(nbinom.sf(np.ceil(line) - 1, n, n / (n + max(mu, 1e-3))))


def _ll(p, y):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def _ece(p, y, bins=10):
    p = np.asarray(p, float); idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum(abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).sum() for b in range(bins) if (idx == b).any()) / len(p))


def main():
    from sklearn.linear_model import LogisticRegression
    from kalshi_nba.backtest import paired_bootstrap
    pre = pregame(player_games())
    par = fit(pre)
    k = pd.read_csv("predictions/jugadores_resultados.csv", dtype={"gid": str})
    k = k[(k["sport"] == "nba") & k["stat"].isin(STAT_NAME)].copy()
    k["s"] = k["stat"].map(STAT_NAME)
    key = pre.assign(event_id=pre["event_id"].astype(str)).set_index(["event_id", "name"])
    key = key[~key.index.duplicated()]
    pa, pb, ok = [], [], []
    for r in k.itertuples():
        x = key.loc[(r.gid, r.player)] if (r.gid, r.player) in key.index else None
        if x is None or x["n"] < MIN_GAMES or not np.isfinite(x[f"mu_{r.s}"]):
            pa.append(np.nan); pb.append(np.nan); ok.append(False); continue
        mu = x[f"mu_{r.s}"]
        pa.append(p_over(mu, r.line, par[r.s]["alpha"]))
        pb.append(p_over(mu * (1 + par[r.s]["beta"] * x["out_share"]), r.line, par[r.s]["alpha"]))
        ok.append(True)
    k["pA"], k["pB"] = pa, pb
    cov = float(np.mean(ok))
    e = k[np.array(ok) & k["p_modelo"].notna()].sort_values("fecha").reset_index(drop=True)
    y = e["acierto"].to_numpy(); dates = e["fecha"]
    met = lambda p: {"logloss": round(float(_ll(p, y).mean()), 4), "brier": round(float(((p - y) ** 2).mean()), 4),
                     "ece": round(_ece(p, y), 4), "acierto": round(float(((p >= 0.5) == y).mean()), 4)}
    res = {"parametros": par, "cobertura": round(cov, 3), "n": int(len(e)), "fechas": int(dates.nunique()),
           "kalshi": met(e["p"].to_numpy()), "proyeccion_antigua": met(e["p_modelo"].to_numpy()),
           "modelo_A": met(e["pA"].to_numpy()), "modelo_B_descriptivo": met(e["pB"].to_numpy()),
           "A_frente_a_antigua": paired_bootstrap(_ll(e["p_modelo"], y), _ll(e["pA"], y), dates),
           "brecha_A_frente_a_kalshi": paired_bootstrap(_ll(e["p"], y), _ll(e["pA"], y), dates),
           "brecha_antigua_frente_a_kalshi": paired_bootstrap(_ll(e["p"], y), _ll(e["p_modelo"], y), dates)}
    # combinación walk-forward por fecha (40% de calentamiento), como JUGADORES_RESEARCH.md
    days = sorted(e["fecha"].unique()); start = days[int(np.ceil(0.4 * len(days)))]
    lr, lc, idx = [], [], []
    for d in [x for x in days if x >= start]:
        tr, te = e[e["fecha"] < d], e[e["fecha"] == d]
        X0 = lambda z: _logit(z["p"]).reshape(-1, 1)
        X1 = lambda z: np.column_stack([_logit(z["p"]), _logit(z["pA"])])
        lr.append(LogisticRegression(C=1e3, max_iter=1000).fit(X0(tr), tr["acierto"]).predict_proba(X0(te))[:, 1])
        lc.append(LogisticRegression(C=1e3, max_iter=1000).fit(X1(tr), tr["acierto"]).predict_proba(X1(te))[:, 1])
        idx += list(te.index)
    w = e.loc[idx]; yw = w["acierto"].to_numpy(); R, C = np.concatenate(lr), np.concatenate(lc)
    res["combinacion"] = {"n": int(len(w)), "fechas": int(w["fecha"].nunique()), "kalshi_recal": round(float(_ll(R, yw).mean()), 4),
                          "kalshi_mas_A": round(float(_ll(C, yw).mean()), 4), "mejora": paired_bootstrap(_ll(R, yw), _ll(C, yw), w["fecha"])}
    res["veredicto"] = {"A_sustituye_a_la_antigua": res["A_frente_a_antigua"]["ic95_inf"] > 0,
                        "combinacion_aporta": res["combinacion"]["mejora"]["ic95_inf"] > 0}
    Path("reports").mkdir(exist_ok=True)
    Path("reports/jugadores2.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
