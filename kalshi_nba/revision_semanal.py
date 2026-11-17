"""Revisión semanal del proyecto: qué pruebas en sombra están listas, cómo van los aciertos y si algo se rompió.

  python -m kalshi_nba.revision_semanal          # imprime el informe (Markdown) y lo guarda en reports/revision_semanal.md
Solo lee archivos del repositorio; no cambia nada. Las «alertas» son lo que hay que mirar o decidir.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

P = Path("predictions")
TARGET = 200
SHADOWS = [("nba_lineup_shadow_scoreboard.json", "Alineaciones NBA"), ("nfl_qb_shadow_scoreboard.json", "QB titular NFL"),
           ("soccer_xi_shadow_scoreboard.json", "Onces de fútbol (copas europeas)")]


def _j(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8").replace("NaN", "null"))
    except (OSError, ValueError):
        return None


def report(now=None) -> tuple[str, list]:
    now = pd.Timestamp(now or pd.Timestamp.now(tz="UTC"))
    L, alerts = [f"# Revisión semanal Mocha Picks — {now:%d/%m/%Y}", ""], []
    L.append("## Pruebas en sombra")
    for f, name in SHADOWS:
        b = _j(P / f) or {}
        r = b.get("resultado") or {}
        n, ci = int(r.get("n") or 0), r.get("mejora_logloss") or {}
        upd = b.get("updated_utc")
        L.append(f"- **{name}:** {n}/{TARGET} partidos; mejora {ci.get('mejora')} [{ci.get('ic95_inf')}; {ci.get('ic95_sup')}]; última foto {upd}")
        if n >= TARGET:
            ok = (ci.get("ic95_inf") or -1) > 0
            alerts.append(f"{name} llegó a {n} partidos: {'MEJORA confirmada (IC 95% > 0) → pedir autorización para activarla' if ok else 'no confirma mejora → dejar como descartada o seguir'}")
        if upd and now - pd.Timestamp(upd) > pd.Timedelta(days=10) and "Onces" not in name:
            alerts.append(f"{name}: sin fotos nuevas desde {upd[:10]} (¿workflow parado?)")
    L += ["", "## Acierto por mercado (jugadas resueltas)"]
    pr = P / "picks_resultados.csv"
    if pr.exists():
        d = pd.read_csv(pr)
        d["grupo"] = d["mercado"].str.replace(r" \(línea segura\)| seguro", "", regex=True)
        for m, x in d.groupby("grupo"):
            gap = x["acierto"].mean() - x["prob"].mean()
            L.append(f"- {m}: {len(x)} jugadas, dijimos {x['prob'].mean():.1%}, acertó {x['acierto'].mean():.1%} ({gap:+.1%})")
            if len(x) >= 100 and abs(gap) > 0.07:
                alerts.append(f"Mercado «{m}»: con {len(x)} jugadas, acierto {x['acierto'].mean():.1%} frente a {x['prob'].mean():.1%} dicho → revisar calibración")
        last7 = d[pd.to_datetime(d["fecha"]) >= (now.tz_convert(None) - pd.Timedelta(days=7)).normalize()]
        L.append(f"- Últimos 7 días: {len(last7)} jugadas, acierto {last7['acierto'].mean():.1%}" if len(last7) else "- Últimos 7 días: sin jugadas resueltas")
        if not len(last7):
            alerts.append("No se registró ninguna jugada resuelta en 7 días (¿bots parados?)")
    else:
        L.append("- Aún sin registro.")
    jr = P / "jugadores_resultados.csv"
    if jr.exists():
        j = pd.read_csv(jr)
        L += ["", f"## Picks de jugadores: {len(j)} resueltos, acierto {j['acierto'].mean():.1%} (Kalshi decía {j['p'].mean():.1%})"]
        if len(j.dropna(subset=['p_modelo'])) >= 300:
            alerts.append("Picks de jugadores: ya hay 300 resueltos con proyección → toca la prueba de JUGADORES_RESEARCH.md")
    reg = P / "intl_registry.csv"
    if reg.exists():
        r = pd.read_csv(reg)
        if "s_H" in r:
            done = r[r["s_H"].notna() & (pd.to_datetime(r["kickoff_utc"], utc=True) < now)]
            L += ["", f"## Sombra de tiros (fútbol): {len(done)} partidos ya jugados con sombra (objetivo 300)"]
            if len(done) >= 300:
                alerts.append("Sombra de tiros: ya hay 300 partidos jugados → evaluarla (TIROS_RESEARCH.md) y pedir autorización si mejora")
    L += ["", "## Combinadas"]
    from .combinadas import summary
    s = summary(P)
    if s["por_perfil"]:
        for x in s["por_perfil"]:
            L.append(f"- {x['perfil']}: {x['aciertos']}/{x['n']} acertadas ({x['acierto']:.0%}) con probabilidad media {x['prob_media']:.0%}, cuota media {x['cuota_media']}")
    else:
        L.append("- Aún sin combinadas resueltas.")
    L += ["", "## Pick final (todas las fuentes)"]
    fs = _j(P / "final_shadow_scoreboard.json") or {}
    for x in fs.get("by_sport", []):
        L.append(f"- {x.get('sport')}: {x.get('n')} partidos, acierto {x.get('acierto_final')}, log loss {x.get('logloss_final')}")
    L += ["", "## Meta: brecha del modelo propio frente al mercado (positivo = el modelo aún es peor)"]
    for x in fs.get("by_sport", []):
        if x.get("brecha") is not None:
            L.append(f"- {x.get('sport')}: {x.get('brecha'):+.4f} [{x.get('brecha_ic95_inf')}; {x.get('brecha_ic95_sup')}] en {x.get('brecha_n')} partidos "
                     f"(modelo {x.get('logloss_modelo_con_mercado'):.4f} vs mercado {x.get('logloss_mercado'):.4f})")
            if (x.get("brecha_n") or 0) >= 200 and (x.get("brecha_ic95_sup") or 1) < 0:
                alerts.append(f"{x.get('sport')}: el modelo propio ya supera al mercado con {x.get('brecha_n')} partidos (IC 95% < 0) → hito de la meta")
    poly = P / "nba_polymarket_snapshots.csv"
    if poly.exists():
        n = pd.read_csv(poly, usecols=["event_id"])["event_id"].nunique()
        L.append(f"- Polymarket registrado en {n} partidos de NBA (se prueba en el combinador al llegar a ~200 con resultado).")
        if n >= 250:
            alerts.append(f"Polymarket ya tiene {n} partidos NBA registrados → toca probarlo en el combinador")
    L += ["", "## Alertas"] + ([f"- ⚠️ {a}" for a in alerts] or ["- Ninguna: todo en marcha."])
    txt = "\n".join(L) + "\n"
    Path("reports").mkdir(exist_ok=True)
    Path("reports/revision_semanal.md").write_text(txt, encoding="utf-8")
    return txt, alerts


if __name__ == "__main__":
    print(report()[0])
