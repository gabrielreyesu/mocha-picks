"""Validación pre-registrada de las nuevas ligas y copas nacionales (NUEVAS_LIGAS.md) y lista de las que se publican.

  python -m kalshi_intl.ligas        # walk-forward por competición -> reports/nuevas_ligas.json y tabla en pantalla

Regla (las tres a la vez): >= 300 partidos fuera de muestra; mejor log loss que las frecuencias de la MISMA competición
(IC 95% por fecha > 0); ECE de la probabilidad del resultado elegido <= 0,05. En copas, solo partidos con ambos equipos
con al menos 10 partidos previos.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

MIN_N, MAX_ECE, MIN_PREV = 300, 0.05, 10
REPORT = Path("reports/nuevas_ligas.json")
# Resultado de la validación (NUEVAS_LIGAS.md, segunda prueba con el 1X2 a 90' corregido; modelo v2). Las demás
# competiciones del grupo se muestran, pero su pick sale SOLO de las casas/Kalshi (nunca del modelo solo).
LIGAS_OK = {"arg.1", "bel.1", "bra.1", "eng.2", "esp.2", "fra.2", "ger.2", "ita.2", "ksa.1", "mex.1", "ned.1", "por.1",
            "sco.1", "tur.1", "usa.1"}
COPAS_OK = {"eng.fa", "eng.league_cup", "esp.copa_del_rey", "ita.coppa_italia", "ger.dfb_pokal", "fra.coupe_de_france"}
# Cuarta prueba: Libertadores y Sudamericana pasan con el modelo RECALIBRADO (conmebol_calibration.json)
CONMEBOL_OK = {"conmebol.libertadores", "conmebol.sudamericana"}
PUBLICAR: set = LIGAS_OK | COPAS_OK | CONMEBOL_OK
CONMEBOL_CAL = Path(__file__).with_name("conmebol_calibration.json")


def recalibrate(code: str, probs):
    """Aplica la recalibración validada a una competición que la necesita; si no aplica, devuelve probs igual."""
    try:
        cfg = json.loads(CONMEBOL_CAL.read_text())
    except (OSError, ValueError):
        return probs
    if code not in cfg.get("codes", []):
        return probs
    return [float(v) for v in apply_cal(np.array([probs], float), cfg["param"])[0]]


def is_cup(code: str) -> bool:
    from .data import GROUPS
    return code in GROUPS["ligas"]["target"] and code not in GROUPS["ligas"].get("league_targets", [])


def publishable(code: str, n_home, n_away) -> bool:
    """¿Se publica el pick del modelo? Competición validada (las copas pasaron con TODOS los partidos, subconjunto b)."""
    return code in PUBLICAR


def market_only(k3, books):
    """Pick sin modelo: casas sin margen; si no hay, Kalshi. Devuelve (probabilidades, fuente) o (None, motivo)."""
    import math
    ok = lambda v: v is not None and len(v) == 3 and all(x is not None and math.isfinite(x) and x > 0 for x in v)
    for v, src in ((books, "casas"), (k3, "Kalshi")):
        if ok(v):
            t = sum(v)
            return [x / t for x in v], src
    return None, "sin cuotas (modelo en validación)"


def ece_top(P: np.ndarray, y: np.ndarray, bins=10) -> float:
    p = P.max(1); hit = (P.argmax(1) == y).astype(float)
    edges = np.linspace(0, 1, bins + 1); e = 0.0
    for a, b in zip(edges[:-1], edges[1:]):
        m = (p > a) & (p <= b)
        if m.any():
            e += m.mean() * abs(hit[m].mean() - p[m].mean())
    return float(e)


def evaluate(r: pd.DataFrame, f: pd.DataFrame) -> list:
    """r: salida de walk_forward (partidos objetivo fuera de muestra); f: todos los partidos procesados (para la referencia)."""
    from kalshi_nba.backtest import paired_bootstrap
    y = r["res"].map({"H": 0, "D": 1, "A": 2}).to_numpy()
    r = r.assign(y=y)
    fin = f[f["final"]].copy()
    fin["res"] = np.where(fin["hs"] > fin["as_"], "H", np.where(fin["hs"] == fin["as_"], "D", "A"))
    fin.loc[fin["status"].isin({"STATUS_FINAL_AET", "STATUS_FINAL_PEN"}), "res"] = "D"      # 1X2 a 90 minutos
    out = []
    for code, d in r.groupby("code"):
        if is_cup(code):
            d = d[np.minimum(d["n_home"], d["n_away"]) >= MIN_PREV]
        d = d[d["temporada"] >= "2021/22"]
        if d.empty:
            continue
        base = np.zeros((len(d), 3))
        # referencia: frecuencias H/D/A de la competición en temporadas ANTERIORES a la evaluada
        prev = fin[fin["code"] == code]
        for t in d["temporada"].unique():
            start = pd.Timestamp(f"{t[:4]}-07-01")
            h = prev[prev["date"] < start]["res"]
            fr = np.array([(h == c).mean() for c in "HDA"]) if len(h) >= 100 else np.array([0.45, 0.27, 0.28])
            base[(d["temporada"] == t).to_numpy()] = fr
        P = d[["p_H", "p_D", "p_A"]].to_numpy(float)
        yy = d["y"].to_numpy()
        llm = -np.log(np.clip(P[np.arange(len(d)), yy], 1e-12, 1))
        llb = -np.log(np.clip(base[np.arange(len(d)), yy], 1e-12, 1))
        bs = paired_bootstrap(llb, llm, d["date"])                      # positivo = el modelo mejora a la referencia
        e = ece_top(P, yy)
        ok = len(d) >= MIN_N and bs["ic95_inf"] > 0 and e <= MAX_ECE
        out.append({"code": code, "n": int(len(d)), "logloss_modelo": round(float(llm.mean()), 4), "logloss_ref": round(float(llb.mean()), 4),
                    "mejora": bs["mejora"], "ic95_inf": bs["ic95_inf"], "ic95_sup": bs["ic95_sup"], "ece": round(e, 4),
                    "acierto": round(float((P.argmax(1) == yy).mean()), 4), "copa": is_cup(code), "publicar": bool(ok)})
    return sorted(out, key=lambda x: (not x["publicar"], x["code"]))


def main(pickle=None):
    from .data import load_group
    from .model import CONFIGS, GROUP_FEATURES, IntlEngine, walk_forward
    g = pd.read_pickle(pickle) if pickle else load_group("ligas")
    f = IntlEngine(CONFIGS["ligas"]).process(g)
    r = walk_forward(f, first_year=2020, features=GROUP_FEATURES["ligas"], et_as_draw=True)  # v2
    res = evaluate(r, f)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(pd.DataFrame(res).to_string(index=False))
    print("PUBLICAR =", sorted(x["code"] for x in res if x["publicar"]))


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)


# ------------------------------------------------------------------ recalibración de copas (tercera prueba, NUEVAS_LIGAS.md)
CUP_CAL = Path(__file__).with_name("cup_calibration.json")


def apply_cal(P, prm) -> np.ndarray:
    """p_c ∝ exp(a_c + T·log p_c), a_H = 0. prm = [T, a_D, a_A]."""
    P = np.clip(np.asarray(P, float), 1e-9, 1)
    z = prm[0] * np.log(P) + np.array([0.0, prm[1], prm[2]])
    z = np.exp(z - z.max(1, keepdims=True))
    return z / z.sum(1, keepdims=True)


def fit_cal(P, y) -> list:
    from scipy.optimize import minimize
    P, y = np.asarray(P, float), np.asarray(y, int)
    f = lambda w: -np.log(apply_cal(P, w)[np.arange(len(y)), y]).mean()
    return [float(v) for v in minimize(f, [1.0, 0.0, 0.0], method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-7}).x]


def load_cal():
    try:
        return json.loads(CUP_CAL.read_text())["param"]
    except (OSError, ValueError, KeyError):
        return None
