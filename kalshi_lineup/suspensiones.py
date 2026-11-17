"""Suspensiones en fútbol frente al mercado (SUSPENSIONES_RESEARCH.md).

  python -m kalshi_lineup.suspensiones        # -> reports/suspensiones.json

Para cada partido de liga cuenta las bajas probables por sanción de cada equipo usando SOLO partidos anteriores:
roja en su partido anterior de liga, o un jugador que llegó a la 5.ª (o 10.ª) amarilla de la temporada en ese partido.
"""
from __future__ import annotations

import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

SB = "https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard"
LEAGUES = ["eng.1", "esp.1", "ita.1", "ger.1", "fra.1"]
CACHE = Path("data/susp")
FINAL = {"STATUS_FULL_TIME", "STATUS_FINAL", "STATUS_FINAL_AET", "STATUS_FINAL_PEN"}


def parse(e: dict, code: str) -> dict | None:
    c = (e.get("competitions") or [None])[0]
    if not c:
        return None
    side = {t.get("homeAway"): t for t in c.get("competitors", [])}
    if set(side) != {"home", "away"}:
        return None
    ids = {side[k]["team"]["id"]: k[0] for k in ("home", "away")}
    sc = lambda t: float(t["score"]) if str(t.get("score", "")).isdigit() else None
    cards = []
    for d in c.get("details", []):
        k = ids.get((d.get("team") or {}).get("id"))
        a = (d.get("athletesInvolved") or [{}])[0]
        if k and a.get("id") and (d.get("yellowCard") or d.get("redCard")):
            cards.append({"s": k, "p": str(a["id"]), "y": int(bool(d.get("yellowCard"))), "r": int(bool(d.get("redCard")))})
    return {"id": str(e["id"]), "code": code, "t": e["date"], "status": (e.get("status") or {}).get("type", {}).get("name"),
            "h": str(side["home"]["team"]["id"]), "a": str(side["away"]["team"]["id"]), "hs": sc(side["home"]), "as": sc(side["away"]),
            "cards": cards}


def fetch(code, ym, getter):
    p = CACHE / code / f"{ym}.json"
    if p.exists():
        return json.loads(p.read_text())
    try:
        j = getter(SB.format(code=code), {"dates": ym, "limit": 1000}) or {}
    except Exception:  # noqa: BLE001
        return []
    rows = [x for x in (parse(e, code) for e in j.get("events", [])) if x]
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(rows))
    return rows


def months(y0=2021, m0=7, end=None):
    end = end or pd.Timestamp.now()
    y, m = y0, m0
    while (y, m) <= (end.year, end.month - 1 if end.month > 1 else 12):   # solo meses cerrados (caché estable)
        yield f"{y}{m:02d}"
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)


def susp_features(rows: list) -> pd.DataFrame:
    """Bajas probables por sanción de local y visitante antes de cada partido (solo datos anteriores)."""
    rows = sorted([r for r in rows if r["status"] in FINAL], key=lambda r: r["t"])
    yellow = defaultdict(int)          # (temporada, liga, jugador) -> amarillas
    pending = defaultdict(set)         # (liga, equipo) -> jugadores sancionados para su PRÓXIMO partido
    out = []
    for r in rows:
        t = pd.Timestamp(r["t"]); season = t.year if t.month >= 7 else t.year - 1
        n = {k: len(pending[(r["code"], r[k])]) for k in ("h", "a")}
        out.append({"event_id": r["id"], "code": r["code"], "date": t.tz_convert(None).normalize(), "susp_h": n["h"], "susp_a": n["a"],
                    "hs": r["hs"], "as_": r["as"], "status": r["status"]})
        for k in ("h", "a"):
            pending[(r["code"], r[k])] = set()                       # la sanción se cumple en este partido
        for c in r["cards"]:
            team = r[c["s"]]
            if c["r"]:
                pending[(r["code"], team)].add(c["p"])
            if c["y"]:
                key = (season, r["code"], c["p"])
                yellow[key] += 1
                if yellow[key] in (5, 10, 15):
                    pending[(r["code"], team)].add(c["p"])
    return pd.DataFrame(out)


def _X(d, with_s):
    P = d[["mkt_H", "mkt_D", "mkt_A"]].to_numpy(float)
    X = np.column_stack([np.log(P[:, 0] / P[:, 1]), np.log(P[:, 2] / P[:, 1])])
    return np.column_stack([X, (d["susp_h"] - d["susp_a"]).to_numpy(float)]) if with_s else X


def walk(d, with_s, warm=0.4):
    from sklearn.linear_model import LogisticRegression
    d = d.sort_values("date").reset_index(drop=True)
    days = np.sort(d["date"].unique())
    P = np.full((len(d), 3), np.nan)
    y = d["y"].to_numpy()
    for i, day in enumerate(days[int(len(days) * warm):]):
        tr, te = d["date"] < day, d["date"] == day
        if i % 7 and i:                                  # reentrena cada 7 fechas (aprox. semanal)
            P[te.to_numpy()] = m.predict_proba(_X(d[te], with_s)); continue
        m = LogisticRegression(C=10.0, max_iter=500).fit(_X(d[tr], with_s), y[tr.to_numpy()])
        P[te.to_numpy()] = m.predict_proba(_X(d[te], with_s))
    return d.assign(q_H=P[:, 0], q_D=P[:, 1], q_A=P[:, 2])


def main():
    from kalshi_nba.backtest import paired_bootstrap
    from kalshi_nba.data import _json as getter
    from kalshi_intl.odds import fetch as odds
    jobs = [(c, ym) for c in LEAGUES for ym in months()]
    with ThreadPoolExecutor(6) as ex:
        rows = [r for rs in ex.map(lambda j: fetch(j[0], j[1], getter), jobs) for r in rs]
    f = susp_features(rows)
    f = f[f["date"] >= pd.Timestamp("2021-08-01")]
    with ThreadPoolExecutor(8) as ex:
        mk = list(ex.map(lambda t: odds(t[0], t[1], Path("data/intl/odds")), zip(f["code"], f["event_id"])))
    f = pd.concat([f.reset_index(drop=True), pd.DataFrame(mk)], axis=1).dropna(subset=["mkt_H", "mkt_D", "mkt_A"])
    f = f[f["status"].isin({"STATUS_FULL_TIME", "STATUS_FINAL"})].copy()       # ligas: siempre 90'
    f["y"] = np.where(f["hs"] > f["as_"], 0, np.where(f["hs"] == f["as_"], 1, 2))
    ll = lambda d, pre: -np.log(np.clip(d[[f"{pre}_H", f"{pre}_D", f"{pre}_A"]].to_numpy(float)[np.arange(len(d)), d["y"].to_numpy()], 1e-12, 1))
    a, b = walk(f, False), walk(f, True)
    m = a.dropna(subset=["q_H"]).index
    A, B = a.loc[m], b.loc[m]
    res = {"n_partidos": int(len(f)), "n_evaluados": int(len(m)),
           "con_bajas": {"local_1+": int((f["susp_h"] > 0).sum()), "visita_1+": int((f["susp_a"] > 0).sum()),
                         "media_por_equipo": round(float((f["susp_h"].mean() + f["susp_a"].mean()) / 2), 3)},
           "casas_recalibradas": round(float(ll(A, "q").mean()), 5), "casas_+_suspensiones": round(float(ll(B, "q").mean()), 5),
           "mejora_frente_a_casas": paired_bootstrap(ll(A, "q"), ll(B, "q"), A["date"]),
           "casas_crudas": round(float(ll(A, "mkt").mean()), 5)}
    # efecto descriptivo: ¿cuánto pesa una baja según el modelo con todo el periodo?
    from sklearn.linear_model import LogisticRegression
    full = LogisticRegression(C=10.0, max_iter=500).fit(_X(f, True), f["y"])
    res["coeficiente_susp_diff"] = [round(float(c[2]), 4) for c in full.coef_]
    Path("reports").mkdir(exist_ok=True)
    Path("reports/suspensiones.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
