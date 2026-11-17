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


def analyze(g: dict, fiab: dict | None = None, comp_names: dict | None = None) -> dict:
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
    out["secciones"] = secciones(g, comp_names)
    return out


# ---------------------------------------------------------------------------------------------- análisis extenso
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
VERBO = {"G": "ganó", "E": "empató", "P": "perdió"}


def _when(t: str) -> str:
    import pandas as pd
    from .resumen import TZ
    x = pd.Timestamp(t).tz_convert(TZ)
    return f"el {DIAS[x.weekday()]} {x.day} de {MESES[x.month - 1]} a las {x:%H:%M} (hora de Chicago)"


def _last(name: str, form: list, comp_names: dict) -> str | None:
    if not form:
        return None
    parts = []
    for x in form:
        where = "en casa" if x["ha"] == "L" else ("fuera" if x["ha"] == "V" else "en sede neutral")
        parts.append(f"{VERBO[x['r']]} {x['s']} ante {x['o']} ({where}, {comp_names.get(x['c'], x['c'])})")
    return f"{name}, del más reciente al más antiguo: " + "; ".join(parts) + "."


def _ppg(x: dict) -> float | None:
    n = x.get("n") or 0
    return None if not n else (3 * x.get("w", 0) + x.get("dr", 0)) / n


def _vs_media(v, media, alto="por encima", bajo="por debajo") -> str:
    if v is None or media is None:
        return ""
    d = v - media
    if abs(d) < 0.08 * max(media, 1e-9):
        return " (en la media de la competición)"
    return f" ({alto} de la media de la competición, {n1(media)})" if d > 0 else f" ({bajo} de la media de la competición, {n1(media)})"


def secciones(g: dict, comp_names: dict | None = None) -> list:
    comp_names = comp_names or {}
    us = g["sport"] in ("nba", "nfl")
    st = g.get("st") or {}
    home, away = g["home"], g["away"]
    unit = "puntos" if us else "goles"
    S = []

    # 1) el partido
    txt = f"{home} recibe a {away}" + (f" {_when(g['t'])}" if g.get("t") else "")
    if st.get("venue"):
        txt += f" en {st['venue']}"
    txt += f", por {g['comp']}." if g.get("comp") else "."
    if "sede neutral" in str(g.get("comp", "")):
        txt += " Se juega en campo neutral, así que la ventaja de local cuenta menos."
    if us and st.get("rec") and all(st["rec"]):
        txt += f" Récord de la temporada: {home} {st['rec'][0]}, {away} {st['rec'][1]}."
    if g.get("state") == "post" and g.get("score"):
        txt += f" Resultado final: {home} {int(g['score'][0])} - {int(g['score'][1])} {away}."
    S.append({"t": "El partido", "x": txt})

    # 2) probabilidades y mercado
    fp = g.get("fp")
    if fp and all(v is not None for v in fp):
        if g.get("three"):
            txt = f"El pick combinado ({g.get('src')}) da {home} {pc(fp[0])}, empate {pc(fp[1])} y {away} {pc(fp[2])}."
        else:
            txt = f"El pick combinado ({g.get('src')}) da {home} {pc(fp[0])} y {away} {pc(fp[1])}."
        rows = {n: v for n, v in g.get("rows", []) if v and all(x is not None for x in v)}
        m = next((v for n, v in rows.items() if n.startswith("Modelo")), None)
        mk = rows.get("Casas") or rows.get("Kalshi")
        if m and mk:
            i = max(range(len(m)), key=lambda k: abs(m[k] - mk[k]))
            d = m[i] - mk[i]
            lado = [home, "el empate", away][i] if g.get("three") else [home, away][i]
            if abs(d) >= 0.05:
                txt += (f" Nuestro modelo es {'más' if d > 0 else 'menos'} optimista que el mercado con {lado} "
                        f"({pc(m[i])} frente a {pc(mk[i])}). Cuando hay mercado, el pick le da más peso, porque en las pruebas "
                        f"históricas fue la fuente más fiable.")
            else:
                txt += " Nuestro modelo y el mercado están prácticamente de acuerdo, lo que da más solidez a la estimación."
        k = rows.get("Kalshi")
        if k and g.get("pick"):
            names = [home, "Empate", away] if g.get("three") else [home, away]
            if g["pick"] in names:
                txt += f" En Kalshi, el contrato de «{g['pick']}» cotiza alrededor de {round(100 * k[names.index(g['pick'])])}¢."
        S.append({"t": "Probabilidades y mercado", "x": txt})

    # 3) forma
    form = st.get("form") or {}
    av = st.get("avg") or {}
    parts = [p for p in (_last(home, form.get("h") or [], comp_names), _last(away, form.get("a") or [], comp_names)) if p]
    if parts:
        txt = " ".join(parts)
        if not us and av.get("h") and av.get("a"):
            ph, pa = _ppg(av["h"]), _ppg(av["a"])
            if ph is not None and pa is not None:
                txt += (f" En sus últimos 10 partidos, {home} suma {n1(ph)} puntos por partido y {away} {n1(pa)}"
                        + (f": {home if ph > pa else away} llega claramente mejor." if abs(ph - pa) >= 0.5 else ": momentos parecidos."))
        elif us and av.get("h") and av.get("a"):
            txt += f" En los últimos 10: {home} {av['h'].get('w', 0)}-{av['h'].get('l', 0)} y {away} {av['a'].get('w', 0)}-{av['a'].get('l', 0)}."
        S.append({"t": "Momento de forma", "x": txt})

    # 4) local / visitante
    va = st.get("vavg") or {}
    h, a = va.get("h") or {}, va.get("a") or {}
    if h.get("n", 0) >= 4 or a.get("n", 0) >= 4:
        bits = []
        if h.get("n", 0) >= 4:
            bits.append(f"En casa, {home} ganó {h.get('w', 0)} de sus últimos {h['n']}" + ("" if us else f" (empató {h.get('dr', 0)})")
                        + f", con {n1(h.get('gf'))} {unit} a favor y {n1(h.get('ga'))} en contra por partido.")
        if a.get("n", 0) >= 4:
            bits.append(f"Fuera, {away} ganó {a.get('w', 0)} de sus últimos {a['n']}" + ("" if us else f" (empató {a.get('dr', 0)})")
                        + f", con {n1(a.get('gf'))} {unit} a favor y {n1(a.get('ga'))} en contra.")
        if h.get("n", 0) >= 4 and a.get("n", 0) >= 4 and h.get("gf") is not None and a.get("gf") is not None:
            dif = (h["gf"] - h["ga"]) - (a["gf"] - a["ga"])
            if abs(dif) >= (3 if us else 0.5):
                fav = home if dif > 0 else away
                bits.append(f"Por sede, la balanza se inclina hacia {fav}.")
        S.append({"t": "Local y visitante", "x": " ".join(bits)})

    # 5) ataque y defensa
    lg = st.get("lg") or {}
    media_eq = (lg.get("goals") / 2) if lg.get("goals") else None
    if av.get("h") and av.get("a") and av["h"].get("gf") is not None and av["a"].get("gf") is not None:
        txt = (f"{home} anota {n1(av['h']['gf'])} {unit} por partido{_vs_media(av['h']['gf'], media_eq)} y recibe {n1(av['h']['ga'])}"
               f"{_vs_media(av['h']['ga'], media_eq, 'más que', 'menos que').replace('de la media', 'la media')}. "
               f"{away} anota {n1(av['a']['gf'])}{_vs_media(av['a']['gf'], media_eq)} y recibe {n1(av['a']['ga'])}"
               f"{_vs_media(av['a']['ga'], media_eq, 'más que', 'menos que').replace('de la media', 'la media')}.")
        if not us:
            for x, name in ((av["h"], home), (av["a"], away)):
                if x.get("o25") is not None:
                    txt += (f" En los partidos de {name} hubo más de 2,5 goles el {pc(x['o25'])} de las veces, ambos marcaron el "
                            f"{pc(x.get('btts'))} y dejó la portería a cero el {pc(x.get('cs'))}.")
        kp, ex = g.get("kp") or {}, st.get("exp") or {}
        if us and kp.get("total") is not None:
            txt += f" Nuestro modelo espera {n1(kp['total'])} puntos en total" + (f" (media de la liga {n1(lg.get('pts'))})." if lg.get("pts") else ".")
        elif not us:
            xg = kp.get("xg") if kp.get("xg") is not None else ex.get("goals")
            if xg is not None:
                txt += f" Para este partido se esperan unos {n1(xg)} goles" + (f" (media de la competición {n1(lg['goals'])})." if lg.get("goals") else ".")
        S.append({"t": "Ataque y defensa", "x": txt})

    # 6) cómo juegan (fútbol)
    if not us and av.get("h") and av.get("a"):
        x, y = av["h"], av["a"]
        if x.get("sh_f") is not None and y.get("sh_f") is not None:
            txt = (f"{home} remata {n1(x['sh_f'])} veces por partido ({n1(x.get('sot_f'))} a puerta) y concede {n1(x.get('sh_a'))}; "
                   f"{away} remata {n1(y['sh_f'])} ({n1(y.get('sot_f'))} a puerta) y concede {n1(y.get('sh_a'))}.")
            if x.get("pos") is not None and y.get("pos") is not None:
                txt += f" Posesión media: {home} {round(x['pos'])}%, {away} {round(y['pos'])}%."
            for z, name in ((x, home), (y, away)):
                if z.get("sot_f") and z.get("gf") is not None and z["sot_f"] > 0:
                    eff = z["gf"] / z["sot_f"]
                    if eff >= 0.4:
                        txt += f" {name} es muy eficaz: convierte {pc(eff)} de sus tiros a puerta."
                    elif eff <= 0.2:
                        txt += f" {name} desperdicia mucho: solo convierte {pc(eff)} de sus tiros a puerta."
            ex = st.get("exp") or {}
            if ex.get("corners") is not None:
                txt += (f" Por promedios, se esperan unos {n1(ex['corners'])} córners" + (f" (media {n1(lg.get('corners'))})" if lg.get("corners") else "")
                        + f" y {n1(ex.get('cards'))} tarjetas" + (f" (media {n1(lg.get('cards'))})." if lg.get("cards") else "."))
            S.append({"t": "Cómo juegan", "x": txt})

    # 7) enfrentamientos directos
    h2h = st.get("h2h") or []
    if h2h:
        parts = []
        for x in h2h:
            a1, b1 = (int(v) for v in x["s"].split("-"))
            r = "ganó" if a1 > b1 else ("perdió" if a1 < b1 else "empató")
            where = "en casa" if x["ha"] == "L" else ("fuera" if x["ha"] == "V" else "en sede neutral")
            parts.append(f"{x['d']}: {home} {r} {x['s']} {where} ({comp_names.get(x['c'], x['c'])})")
        S.append({"t": "Enfrentamientos directos", "x": "; ".join(parts) + ". Los enfrentamientos directos aportan poco por sí solos: "
                  "el mercado ya los tiene en cuenta."})
    else:
        S.append({"t": "Enfrentamientos directos", "x": "No hay enfrentamientos recientes entre ambos en nuestros datos."})

    # 8) bajas y descanso
    bits = []
    inj = g.get("inj") or {}
    for k, name in (("home", home), ("away", away)):
        lst = inj.get(k) or []
        bits.append(f"{name}: {', '.join(lst)}." if lst else f"{name}: sin bajas reportadas.")
    if not g.get("inj"):
        bajas = next((v for k, v in g.get("extra", []) if k.startswith("Bajas")), None)
        bits = [f"Bajas (local / visita): {bajas}."] if bajas and bajas != "—" else ["No tenemos parte de bajas para este partido."]
    if g.get("rest") and all(r is not None for r in g["rest"]) and max(g["rest"]) < 7:    # 7 = tope (descanso largo)
        rh, ra = g["rest"]
        bits.append(f"Días de descanso: {home} {int(rh)}, {away} {int(ra)}."
                    + (" Jugar en días seguidos suele restar algo de rendimiento." if min(rh, ra) <= 1 else ""))
    S.append({"t": "Bajas y descanso", "x": " ".join(bits)})

    # 9) otros mercados
    ps = [p for p in g.get("picks") or [] if p.get("mercado") != "Ganador" and p.get("prob") is not None]
    if ps:
        S.append({"t": "Otros mercados", "x": " ".join(f"{p['mercado']}: {p['pick']} ({pc(p['prob'])}, {p['fuente']})." for p in ps)})

    # 10) conclusión
    pick, prob = g.get("pick"), g.get("prob")
    if pick is not None and prob is not None:
        lado = "el empate" if pick == "Empate" else pick
        nivel = ("favorito claro" if prob >= 0.70 else "favorito" if prob >= 0.55 else "ligero favorito" if prob >= 0.45 else "resultado más probable en un partido muy abierto")
        txt = f"{lado[0].upper() + lado[1:]} es {nivel} con {pc(prob)}."
        if prob < 0.55:
            dc = next((p for p in g.get("picks") or [] if p.get("mercado") == "Doble oportunidad"), None)
            if dc:
                txt += f" La opción más segura según nuestras probabilidades es «{dc['pick']}» ({pc(dc['prob'])})."
        fallan = round(10 * (1 - prob))
        txt += (f" Ojo: {pc(prob)} significa que, de cada 10 partidos parecidos, alrededor de {fallan} "
                f"{'no sale' if fallan == 1 else 'no salen'}. Nunca hay certeza.") if fallan >= 1 else " Aun así, nunca hay certeza."
        S.append({"t": "Conclusión", "x": txt})
    return S
