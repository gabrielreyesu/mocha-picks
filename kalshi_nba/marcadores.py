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
    return {"id": str(ev.get("id")), "state": state, "detail": st.get("shortDetail") or "",
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
        return None                                            # prórroga/penaltis: el 1X2 se liquida a 90 min (desconocido aquí)
    res = g["home"] if sc["hs"] > sc["as"] else (g["away"] if sc["as"] > sc["hs"] else "Empate")
    return g["pick"] == res
