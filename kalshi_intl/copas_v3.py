"""Tercera prueba de copas (NUEVAS_LIGAS.md): v2 + recalibración ajustada solo con temporadas anteriores.
NO SE USA: con el 1X2 a 90' corregido, v2 ya pasa sin recalibrar. Se conserva como registro.

  python -m kalshi_intl.copas_v3      # -> reports/copas_v3.json y kalshi_intl/cup_calibration.json (si pasa)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .copas_v2 import EXTRA_FEED, rule

EXCLUIDAS = {"ita.coppa_italia"}            # empeora en v2 (IC 95% < 0)


def main():
    from .data import GROUPS, load_group
    from .ligas import CUP_CAL, MIN_PREV, apply_cal, fit_cal
    from .model import CONFIGS, FEATS_V2, NATIONAL_CUPS, IntlEngine, walk_forward
    g = load_group("ligas", verbose=False)
    f = IntlEngine(CONFIGS["ligas"]).process(g)
    r = walk_forward(f, first_year=2020, features=FEATS_V2, et_as_draw=True)
    fin = f[f["final"]].copy()
    fin["res"] = np.where(fin["hs"] > fin["as_"], "H", np.where(fin["hs"] == fin["as_"], "D", "A"))
    fin.loc[fin["status"].isin({"STATUS_FINAL_AET", "STATUS_FINAL_PEN"}), "res"] = "D"
    cups = r[r["code"].isin(NATIONAL_CUPS - EXCLUIDAS)].copy().reset_index(drop=True)
    cups["y"] = cups["res"].map({"H": 0, "D": 1, "A": 2})
    seasons = sorted(cups["temporada"].unique())
    out_rows = []
    for s in seasons:
        if s < "2021/22":
            continue
        tr, te = cups[cups["temporada"] < s], cups[cups["temporada"] == s].copy()
        if len(tr) < 200:
            continue
        prm = fit_cal(tr[["p_H", "p_D", "p_A"]].to_numpy(), tr["y"].to_numpy())
        P = apply_cal(te[["p_H", "p_D", "p_A"]].to_numpy(), prm)
        te[["p_H", "p_D", "p_A"]] = P
        te["cal"] = [prm] * len(te)
        out_rows.append(te)
    ev = pd.concat(out_rows, ignore_index=True)
    a = ev[np.minimum(ev["n_home"], ev["n_away"]) >= MIN_PREV]
    res = {"copas_a_con_historial": rule(a, fin), "copas_b_todos": rule(ev, fin),
           "por_copa_b": {c: rule(d, fin) for c, d in ev.groupby("code")}}
    prm_all = fit_cal(cups[["p_H", "p_D", "p_A"]].to_numpy(), cups["y"].to_numpy())      # para producción: todas las temporadas
    res["param_produccion"] = prm_all
    Path("reports").mkdir(exist_ok=True)
    Path("reports/copas_v3.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in ("copas_a_con_historial", "copas_b_todos"):
        print(k, res[k])
    for c, v in res["por_copa_b"].items():
        print("  ", c, v)
    print("param:", prm_all)
    if False:                                     # no se usa en producción (ver docstring)
        CUP_CAL.write_text(json.dumps({"param": prm_all, "subconjunto": "b" if res["copas_b_todos"]["pasa"] else "a",
                                       "excluidas": sorted(EXCLUIDAS), "nota": "NUEVAS_LIGAS.md, tercera prueba"}, indent=1) + "\n")
        print("PASA -> escrito", CUP_CAL)


if __name__ == "__main__":
    main()
