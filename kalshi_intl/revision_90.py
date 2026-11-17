"""Revisión del sesgo del 1X2 a 90' (CORRECCION_90MIN.md) en los grupos clubes y selecciones.
  python -m kalshi_intl.revision_90     # -> reports/revision_90.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ET = {"STATUS_FINAL_AET", "STATUS_FINAL_PEN"}


def metrics(d):
    from kalshi_nba.backtest import paired_bootstrap
    from .ligas import ece_top
    if d.empty:
        return {"n": 0}
    y = d["res"].map({"H": 0, "D": 1, "A": 2}).to_numpy()
    P = d[["p_H", "p_D", "p_A"]].to_numpy(float); B = d[["base_H", "base_D", "base_A"]].to_numpy(float)
    lm = -np.log(np.clip(P[np.arange(len(d)), y], 1e-12, 1)); lb = -np.log(np.clip(B[np.arange(len(d)), y], 1e-12, 1))
    bs = paired_bootstrap(lb, lm, d["date"]) if len(d) >= 30 else {}
    return {"n": int(len(d)), "logloss": round(float(lm.mean()), 4), "logloss_base": round(float(lb.mean()), 4), **bs,
            "ece": round(ece_top(P, y), 4), "acierto": round(float((P.argmax(1) == y).mean()), 4),
            "prob_empate_media": round(float(P[:, 1].mean()), 4), "empates_reales": round(float((y == 1).mean()), 4)}


def main():
    from .data import load_group
    from .model import CONFIGS, GROUP_FEATURES, IntlEngine, walk_forward
    out = {}
    for grp in ("clubes", "selecciones"):
        f = IntlEngine(CONFIGS[grp]).process(load_group(grp, verbose=False))
        a = walk_forward(f, features=GROUP_FEATURES[grp])
        b = walk_forward(f, features=GROUP_FEATURES[grp], et_as_draw=True)
        aff = b[b["status"].isin(ET)]
        out[grp] = {"A_sin_prorrogas": metrics(a), "B_corregida": metrics(b), "solo_afectados_B": metrics(aff),
                    "afectados": int(len(aff)), "por_competicion_afectados": aff["code"].value_counts().to_dict()}
        print(grp, json.dumps(out[grp], ensure_ascii=False))
    Path("reports").mkdir(exist_ok=True)
    Path("reports/revision_90.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
