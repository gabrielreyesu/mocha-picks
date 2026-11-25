import numpy as np
import pandas as pd

from kalshi_intl.empates import adjust, fit_delta, shift


def test_shift_keeps_sum_and_raises_draw():
    P = np.array([[0.4, 0.3, 0.3]])
    Q = shift(P, 0.5)
    assert abs(Q.sum() - 1) < 1e-12 and Q[0, 1] > 0.3


def test_fit_delta_finds_more_draws_and_needs_history():
    rng = np.random.default_rng(0)
    P = np.tile([0.45, 0.25, 0.30], (2000, 1))
    y = rng.choice(3, size=2000, p=[0.38, 0.35, 0.27])
    assert fit_delta(P, y) > 0.1
    assert fit_delta(P[:100], y[:100]) == 0.0


def test_adjust_uses_only_previous_seasons():
    d = pd.DataFrame({"code": "x", "temporada": ["2021/22"] * 400 + ["2022/23"] * 400,
                      "p_H": 0.45, "p_D": 0.25, "p_A": 0.30, "y": [1] * 400 + [0] * 400})
    out = adjust(d)
    assert np.allclose(out[:400], d[["p_H", "p_D", "p_A"]].to_numpy()[:400])     # primera temporada: sin historia
    assert (out[400:, 1] > 0.25).all()                                              # segunda: aprende de la primera
