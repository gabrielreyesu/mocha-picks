"""Análisis en texto de cada partido: por qué sale el pick y qué dicen los datos del juego.

Todo sale de datos que la página ya tiene (mercados, modelo, forma, promedios, enfrentamientos, bajas, descanso y la
fiabilidad histórica del pick). No se inventa nada: si falta un dato, esa frase no aparece. El texto describe; no es
una recomendación de apuesta.
"""
from __future__ import annotations

import json
from pathlib import Path

FIAB = Path(__file__).with_name("fiabilidad.json")
SRC_NAME = {"Modelo": "nuestro modelo", "Casas": "las casas", "Kalshi": "Kalshi", "Polymarket": "Polymarket"}


def pc(v) -> str:
    return "—" if v is None else f"{round(100 * v)}%"


def n1(v) -> str:
    return "—" if v is None else f"{v:.1f}".replace(".", ",")


def _fiab() -> dict:
    try:
        return json.loads(FIAB.read_text()).get("deportes", {})
    except (OSError, ValueError):
        return {}


def _record(form: list) -> tuple[int, int, int]:
    return (sum(x["r"] == "G" for x in form), sum(x["r"] == "E" for x in form), sum(x["r"] == "P" for x in form))


def _form_txt(name: str, form: list, soccer: bool) -> str | None:
    if not form:
        return None
    g, e, p = _record(form)
    parts = [f"{g} {'victoria' if g == 1 else 'victorias'}"]
    if soccer:
        parts.append(f"{e} {'empate' if e == 1 else 'empates'}")
    parts.append(f"{p} {'derrota' if p == 1 else 'derrotas'}")
    racha = ""
    first = form[0]["r"]
    k = next((i for i, x in enumerate(form) if x["r"] != first), len(form))
    if k >= 3:
        racha = f" (viene de {k} {'victorias' if first == 'G' else 'derrotas' if first == 'P' else 'empates'} seguidas)"
    return f"{name}: {', '.join(parts)} en sus últimos {len(form)}{racha}."


def analyze(g: dict, fiab: dict | None = None) -> dict:
    fiab = _fiab() if fiab is None else fiab
    us = g["sport"] in ("nba", "nfl")
    soccer = not us
    st = g.get("st") or {}
    pick, prob = g.get("pick"), g.get("prob")
    home, away = g["home"], g["away"]
    out = {"titular": "", "puntos": [], "contra": [], "datos": []}
    if pick is None:
        out["titular"] = f"Sin pick: {g.get('src') or 'faltan datos'}."
    else:
        idx = ([home, "Empate", away] if g.get("three") else [home, away]).index(pick) if pick in (home, away, "Empate") else None
        # 1) fuentes: ¿coinciden?
        srcs = [(SRC_NAME.get(n, n), v[idx]) for n, v in g.get("rows", []) if idx is not None and v and v[idx] is not None]
        fav = [n for n, v in g.get("rows", []) if v and all(x is not None for x in v) and max(range(len(v)), key=lambda i: v[i]) == idx]
        con = [SRC_NAME.get(n, n) for n, v in g.get("rows", []) if v and all(x is not None for x in v)]
        lado = "el empate" if pick == "Empate" else pick
        out["titular"] = f"Pick: {lado} ({pc(prob)}). Fuente del pick: {g.get('src')}."
        if srcs:
            lista = ", ".join(f"{n} {pc(v)}" for n, v in srcs)
            if len(fav) == len(con) and len(con) > 1:
                out["puntos"].append(f"{'Las dos' if len(con) == 2 else f'Las {len(con)}'} fuentes ven a {lado} como lo más probable: {lista}.")
            elif len(srcs) == 1:
                out["puntos"].append(f"Probabilidad de {lado} según {srcs[0][0]}: {pc(srcs[0][1])} (no hay otras fuentes para este partido).")
            elif con:
                otros = [SRC_NAME.get(n, n) for n, v in g.get("rows", []) if v and all(x is not None for x in v) and n not in fav]
                out["puntos"].append(f"Probabilidad de {lado} según cada fuente: {lista}.")
                if otros:
                    out["contra"].append(f"No todas coinciden: {', '.join(otros)} {'ve' if len(otros) == 1 else 'ven'} otro resultado como el más probable.")
        # 2) fiabilidad histórica del tramo
        dep = {"nba": "NBA", "nfl": "NFL"}.get(g["sport"])
        if dep and prob is not None and dep in fiab:
            lo = int(prob * 10) * 10
            tr = next((t for t in fiab[dep].get("tramos", []) if t["tramo"].startswith(f"{lo}")), None)
            if tr and tr.get("n", 0) >= 30:
                out["puntos"].append(f"Históricamente, los picks de {dep} entre {tr['tramo']} acertaron el {pc(tr['acierto'])} "
                                     f"de las veces ({tr['n']} partidos fuera de muestra).")
        if prob is not None and prob < 0.5:
            out["contra"].append(f"Es el resultado más probable, pero con {pc(prob)} es más fácil que NO ocurra: partido muy abierto.")
    # 3) forma
    form = st.get("form") or {}
    for k, name in (("h", home), ("a", away)):
        t = _form_txt(name, form.get(k) or [], soccer)
        if t:
            out["datos"].append(t)
    if pick in (home, away) and form.get("h") and form.get("a"):
        me, op = ("h", "a") if pick == home else ("a", "h")
        gm, go = _record(form[me])[0], _record(form[op])[0]
        if gm - go >= 2:
            out["puntos"].append(f"{pick} llega en mejor forma ({gm} victorias en sus últimos {len(form[me])} frente a {go} del rival).")
        elif go - gm >= 2:
            out["contra"].append(f"El rival llega en mejor forma ({go} victorias en sus últimos {len(form[op])} frente a {gm}).")
    # 4) promedios por sede (local en casa, visitante fuera)
    va = st.get("vavg") or {}
    h, a = va.get("h") or {}, va.get("a") or {}
    unit = "pts" if us else "goles"
    rec = lambda x: f"{x.get('w', 0)}-{x.get('l', 0)}" if us else f"{x.get('w', 0)}G {x.get('dr', 0)}E {x.get('l', 0)}P"
    for x, name, where in ((h, home, "local"), (a, away, "visitante")):
        if x.get("n", 0) >= 4 and x.get("gf") is not None:
            out["datos"].append(f"{name} como {where} (últimos {x['n']}): {rec(x)}; anota {n1(x['gf'])} y recibe {n1(x['ga'])} {unit} por partido.")
    # 5) enfrentamientos directos
    h2h = st.get("h2h") or []
    if h2h:
        res = []
        for x in h2h:
            a1, b1 = (int(v) for v in x["s"].split("-"))
            res.append("G" if a1 > b1 else ("P" if a1 < b1 else "E"))
        w, d, l = res.count("G"), res.count("E"), res.count("P")
        out["datos"].append(f"Enfrentamientos recientes ({len(h2h)}): {home} {w} {'victoria' if w == 1 else 'victorias'}"
                            f"{'' if us else f', {d} empates'} y {l} {'derrota' if l == 1 else 'derrotas'}.")
    # 6) goles / puntos esperados
    kp, ex, lg = g.get("kp") or {}, st.get("exp") or {}, st.get("lg") or {}
    if soccer:
        xg = kp.get("xg") if kp.get("xg") is not None else ex.get("goals")
        if xg is not None:
            comp = f" (la media de la competición es {n1(lg['goals'])})" if lg.get("goals") else ""
            out["datos"].append(f"Se esperan unos {n1(xg)} goles{comp}"
                                + (f"; probabilidad de más de 2,5: {pc(kp['o25'])}" if kp.get("o25") is not None else "") + ".")
        if kp.get("btts") is not None:
            out["datos"].append(f"Ambos anotan: {pc(kp['btts'])}.")
        if ex.get("corners") is not None:
            out["datos"].append(f"Por promedios: unos {n1(ex['corners'])} córners y {n1(ex.get('cards'))} tarjetas.")
    else:
        if kp.get("margin") is not None:
            fav = home if kp["margin"] >= 0 else away
            out["datos"].append(f"Nuestro modelo espera que {fav} gane por {n1(abs(kp['margin']))} pts, con un total de {n1(kp.get('total'))} pts.")
        if g.get("rest") and all(r is not None for r in g["rest"]):
            rh, ra = g["rest"]
            if rh != ra:
                mas, menos = (home, away) if rh > ra else (away, home)
                out["datos"].append(f"Descanso: {home} {int(rh)} {'día' if rh == 1 else 'días'}, {away} {int(ra)}; {mas} llega más descansado.")
            if min(rh, ra) <= 1:
                quien = home if rh <= 1 else away
                (out["contra"] if quien == pick else out["puntos"]).append(f"{quien} juega en días seguidos (back-to-back).")
    # 7) bajas
    inj = g.get("inj") or {}
    for k, name in (("home", home), ("away", away)):
        lst = inj.get(k) or []
        if lst:
            txt = f"{name} tiene {len(lst)} {'baja o duda' if len(lst) == 1 else 'bajas o dudas'}: {', '.join(lst[:4])}{'…' if len(lst) > 4 else '.'}"
            (out["contra"] if name == pick else out["datos"]).append(txt)
    # 8) resultado (partidos terminados)
    if g.get("hit") is not None and g.get("score"):
        out["titular"] += " ✅ Se cumplió." if g["hit"] else " ❌ No se cumplió."
    # 9) avisos
    for k, v in g.get("extra", []):
        if k == "Aviso":
            out["contra"].append(v)
    for t in g.get("nostake") or []:
        out["contra"].append(f"{t} ya no se juega nada en la clasificación (puede rotar).")
    return out
