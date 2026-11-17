"""Cuarta prueba (NUEVAS_LIGAS.md): recalibración de Libertadores y Sudamericana sin fugas.
  python -m kalshi_intl.conmebol_cal     # -> reports/conmebol_cal.json y kalshi_intl/conmebol_calibration.json si alguna pasa
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

CODES = ["conmebol.libertadores", "conmebol.sudamericana"]
OUT = Path(__file__).with_name("conmebol_calibration.json")


def main():
    from .copas_v2 import rule
    from .data import load_group
    from .ligas import apply_cal, fit_cal
    from .model import CONFIGS, GROUP_FEATURES, IntlEngine, walk_forward
    f = IntlEngine(CONFIGS["ligas"]).process(load_group("ligas", verbose=False))
    r = walk_forward(f, first_year=2020, features=GROUP_FEATURES["ligas"], et_as_draw=True)
    fin = f[f["final"]].copy()
    fin["res"] = np.where(fin["hs"] > fin["as_"], "H", np.where(fin["hs"] == fin["as_"], "D", "A"))
    fin.loc[fin["status"].isin({"STATUS_FINAL_AET", "STATUS_FINAL_PEN"}), "res"] = "D"
    c = r[r["code"].isin(CODES)].copy().reset_index(drop=True)
    c["y"] = c["res"].map({"H": 0, "D": 1, "A": 2})
    parts = []
    for s in sorted(c["temporada"].unique()):
        if s < "2021/22":
            continue
        tr, te = c[c["temporada"] < s], c[c["temporada"] == s].copy()
        if len(tr) < 200:
            continue
        prm = fit_cal(tr[["p_H", "p_D", "p_A"]].to_numpy(), tr["y"].to_numpy())
        te[["p_H", "p_D", "p_A"]] = apply_cal(te[["p_H", "p_D", "p_A"]].to_numpy(), prm)
        parts.append(te)
    ev = pd.concat(parts, ignore_index=True)
    base = c[c["temporada"] >= "2021/22"]
    res = {"sin_recalibrar": {k: rule(d, fin) for k, d in base.groupby("code")},
           "recalibrado": {k: rule(d, fin) for k, d in ev.groupby("code")},
           "param_produccion": fit_cal(c[["p_H", "p_D", "p_A"]].to_numpy(), c["y"].to_numpy())}
    ok = [k for k, v in res["recalibrado"].items() if v["pasa"]]
    res["pasan"] = ok
    Path("reports").mkdir(exist_ok=True)
    Path("reports/conmebol_cal.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("sin_recalibrar", "recalibrado", "pasan", "param_produccion")}, ensure_ascii=False, indent=1))
    if ok:
        OUT.write_text(json.dumps({"param": res["param_produccion"], "codes": ok, "nota": "NUEVAS_LIGAS.md, cuarta prueba"}, indent=1) + "\n")


if __name__ == "__main__":
    main()
