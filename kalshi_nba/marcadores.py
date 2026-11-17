"""Marcadores y estado (programado / en juego / finalizado) de los partidos recientes, desde el marcador público de ESPN.

Solo se consulta lo necesario para la página: partidos de los últimos días que ya empezaron. Si ESPN falla, la página
sigue funcionando sin marcadores (nunca se inventa un resultado).
"""
from __future__ import annotations

import pandas as pd

SB = "https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard"
PATH = {"nba": "basketball/nba", "nfl": "football/nfl"}
LIGA_CODE = {"Premier League": "eng.1", "La Liga": "esp.1", "Serie A": "ita.1", "Bundesliga": "ger.1", "Ligue 1": "fra.1"}
FINAL = {"STATUS_FINAL", "STATUS_FULL_TIME", "STATUS_FINAL_AET", "STATUS_FINAL_PEN"}


def _parse(ev: dict) -> dict | None:
    c = (ev.get("competitions") or [{}])[0]
    side = {t.get("homeAway"): t for t in c.get("competitors", [])}
    if set(side) != {"home", "away"}:
        return None
    st = (ev.get("status") or {}).get("type") or {}
    num = lambda t: float(t["score"]) if str(t.get("score", "")).replace(".", "").isdigit() else None
    state = "post" if st.get("name") in FINAL or st.get("state") == "post" else ("in" if st.get("state") == "in" else "pre")
    ids = {(side[k].get("team") or {}).get("id"): k[0] for k in ("home", "away")}
    evs = []
    for d in c.get("details", []):                              # goles y expulsiones (fútbol)
        k = ids.get((d.get("team") or {}).get("id"))
        if k and (d.get("scoringPlay") or d.get("redCard")):
            evs.append({"k": "g" if d.get("scoringPlay") else "r", "t": k, "m": (d.get("clock") or {}).get("displayValue", ""),
                        "p": ((d.get("athletesInvolved") or [{}])[0]).get("shortName") or "",
                        "pen": bool(d.get("penaltyKick")), "og": bool(d.get("ownGoal"))})
    return {"id": str(ev.get("id")), "state": state, "ev": evs, "detail": st.get("shortDetail") or "",
            "hs": num(side["home"]), "as": num(side["away"]), "regular": st.get("name") in ("STATUS_FINAL", "STATUS_FULL_TIME"),
            "home": (side["home"].get("team") or {}).get("displayName", ""), "away": (side["away"].get("team") or {}).get("displayName", "")}


def fetch(games: list, now, getter=None, days_back=3) -> dict:
    """games: dicts de la página (sport, t, id, code, home, away). Devuelve {clave: marcador} con clave = sport:id."""
    if getter is None:
        from kalshi_nba.data import _json as getter
    from kalshi_soccer.kalshi import _same
    lo = pd.Timestamp(now) - pd.Timedelta(days=days_back)
    need = [g for g in games if lo <= pd.Timestamp(g["t"]) <= pd.Timestamp(now)]
    queries = {}
    for g in need:
        day = pd.Timestamp(g["t"]).tz_convert("America/New_York").strftime("%Y%m%d")
        if g["sport"] in PATH:
            path = PATH[g["sport"]]
        elif g.get("code"):
            path = f"soccer/{g['code']}"
        else:
            continue
        queries.setdefault((path, day), []).append(g)
    out = {}
    for (path, day), gs in queries.items():
        try:
            j = getter(SB.format(path=path), {"dates": day, "limit": 300}) or {}
        except Exception:  # noqa: BLE001 - sin marcador si ESPN falla
            continue
        evs = [e for e in (_parse(x) for x in j.get("events", [])) if e]
        by_id = {e["id"]: e for e in evs}
        for g in gs:
            e = by_id.get(str(g["id"]))
            if e is None and g["sport"] == "liga":            # ligas: registro con otros IDs -> nombres de ambos equipos
                hits = [x for x in evs if _same(x["home"], g["home"]) and _same(x["away"], g["away"])]
                e = hits[0] if len(hits) == 1 else None
            if e:
                out[f"{g['sport']}:{g['id']}"] = e
    return out


def hit(g: dict, sc: dict) -> bool | None:
    """¿Acertó el pick principal? Solo con partido finalizado y, en fútbol, resultado a 90 minutos."""
    if not sc or sc["state"] != "post" or sc["hs"] is None or sc["as"] is None or not g.get("pick"):
        return None
    if g["three"] and not sc["regular"]:
        res = "Empate"                                         # prórroga/penales: a los 90' iban empatados (así se liquida el 1X2)
    else:
        res = g["home"] if sc["hs"] > sc["as"] else (g["away"] if sc["as"] > sc["hs"] else "Empate")
    return g["pick"] == res


def _num_in(s: str):
    import re
    m = re.search(r"(\d+(?:[.,]\d+)?)", s)
    return float(m.group(1).replace(",", ".")) if m else None


def pick_hit(g: dict, p: dict, sc: dict) -> bool | None:
    """¿Acertó una jugada de cualquier mercado? None si el partido no terminó o no se puede saber.
    Fútbol: todo se liquida a 90 minutos. Con prórroga/penales, a los 90' iba empate (ganador, doble oportunidad), pero
    los goles exactos de los 90' no se conocen -> goles y ambos anotan quedan sin decidir. NBA/NFL: incluye la prórroga."""
    if not sc or sc.get("state") != "post" or sc.get("hs") is None or sc.get("as") is None or not p or not p.get("pick"):
        return None
    hs, as_ = sc["hs"], sc["as"]
    home, away, choice, mk = g["home"], g["away"], p["pick"], p.get("mercado", "")
    et = bool(g.get("three")) and not sc.get("regular", True)
    res = "D" if et else ("H" if hs > as_ else ("A" if as_ > hs else "D"))
    name = {"H": home, "A": away, "D": "Empate"}[res]
    if mk == "Ganador":
        return choice == name
    if mk.startswith("Doble oportunidad"):
        if choice == f"{home} o empate":
            return res in ("H", "D")
        if choice == f"{away} o empate":
            return res in ("A", "D")
        if choice.startswith(f"{home} o {away}"):
            return res != "D"
        return None
    if mk.startswith("Goles") or mk.startswith("Total de puntos") or mk.startswith("Puntos"):
        if et:
            return None
        line = _num_in(choice)
        if line is None:
            return None
        return (hs + as_ > line) if choice.startswith("Más") else (hs + as_ < line)
    if mk.startswith("Ambos anotan"):
        if et:
            return None
        both = hs > 0 and as_ > 0
        return both if choice.startswith("Sí") else not both
    if mk.startswith("Hándicap"):
        line = _num_in(choice.split(" por ")[-1] if " por " in choice else choice)
        if line is None:
            return None
        team = home if choice.startswith(home) else (away if choice.startswith(away) else None)
        if team is None:
            return None
        margin = (hs - as_) if team == home else (as_ - hs)
        return margin > line if "gana por más de" in choice else margin > -line
    return None
