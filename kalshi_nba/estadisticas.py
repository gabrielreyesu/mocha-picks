"""Estadísticas de equipos para la ventana de cada partido y la página «Estadísticas» (inspirada en Oddster).

Fuente: marcador público de ESPN (sin clave). En fútbol trae, por partido: tiros, tiros a puerta, córners, faltas,
posesión, tarjetas y goleadores. En NBA/NFL: puntos y récord. Con eso se calcula para cada partido de la página:
  * forma (últimos 5), promedios de los últimos 10 (en total y como local/visitante), % de partidos con más de 2,5 goles,
    ambos anotan, porterías a cero; enfrentamientos directos; promedios de la competición;
  * valores esperados del partido (goles, tiros, tiros a puerta, córners, tarjetas / puntos) por promedios simples.
Sin fugas: cada partido usa SOLO partidos terminados antes de su inicio. Son estadísticas descriptivas: NO entran en el
pick (para eso habría que probarlas frente al mercado; ver FACTORES.md).
  python -m kalshi_nba.estadisticas        # escribe predictions/stats.json (la página lo lee)
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SB = "https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard"
CACHE = Path("data/stats")
OUT = Path("predictions/stats.json")
US_PATH = {"nba": "basketball/nba", "nfl": "football/nfl"}
US_DAYS = {"nba": 150, "nfl": 160}
FINAL = {"STATUS_FINAL", "STATUS_FULL_TIME", "STATUS_FINAL_AET", "STATUS_FINAL_PEN"}
DEAD = {"STATUS_CANCELED", "STATUS_POSTPONED", "STATUS_ABANDONED", "STATUS_SUSPENDED", "STATUS_FORFEIT"}
SOCCER_KEYS = {"totalShots": "sh", "shotsOnTarget": "sot", "wonCorners": "cor", "foulsCommitted": "fou", "possessionPct": "pos"}
LAST = 10            # partidos para los promedios
MIN_N = 3            # mínimo de partidos con dato para mostrar un promedio


def soccer_codes():
    from kalshi_intl.data import GROUPS
    from .logos import CLUB_CODES
    L = GROUPS.get("ligas", {})
    clubs = list(dict.fromkeys(CLUB_CODES + list(GROUPS["clubes"]["target"]) + GROUPS["clubes"]["feed"]
                               + list(L.get("target", {})) + L.get("feed", [])))
    nat = list(GROUPS["selecciones"]["target"]) + GROUPS["selecciones"]["feed"]
    return clubs, nat


LEAGUE_NAMES = {"eng.1": "Premier League", "esp.1": "LaLiga", "ita.1": "Serie A", "ger.1": "Bundesliga", "fra.1": "Ligue 1",
                "por.1": "Liga Portugal", "ned.1": "Eredivisie", "bel.1": "Bélgica", "tur.1": "Turquía", "sco.1": "Escocia",
                "aut.1": "Austria", "sui.1": "Suiza", "gre.1": "Grecia", "den.1": "Dinamarca", "nor.1": "Noruega", "swe.1": "Suecia",
                "rou.1": "Rumanía", "isr.1": "Israel", "cyp.1": "Chipre", "fifa.worldq.concacaf": "Eliminatorias CONCACAF",
                "fifa.worldq.afc": "Eliminatorias AFC", "fifa.worldq.caf": "Eliminatorias CAF", "concacaf.gold": "Copa Oro",
                "concacaf.nations.league": "Liga de Naciones CONCACAF", "caf.nations": "Copa África", "afc.asian.cup": "Copa Asia",
                "nba": "NBA", "nfl": "NFL"}


def comp_names() -> dict:
    """Código ESPN -> nombre en español (para la forma y los enfrentamientos directos)."""
    from kalshi_intl.data import GROUPS
    out = dict(LEAGUE_NAMES)
    for g in GROUPS.values():
        out.update(g["target"])
    return out


def _num(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------------------------------------------- lectura
def parse_soccer(e: dict, code: str) -> dict | None:
    c = (e.get("competitions") or [None])[0]
    if not c:
        return None
    side = {t.get("homeAway"): t for t in c.get("competitors", [])}
    if set(side) != {"home", "away"}:
        return None
    st = (e.get("status") or {}).get("type") or {}
    ids = {side[k]["team"]["id"]: k[0] for k in ("home", "away")}
    out = {"id": str(e["id"]), "code": code, "t": e["date"], "status": st.get("name"), "neutral": bool(c.get("neutralSite")),
           "venue": (c.get("venue") or {}).get("fullName")}
    for k in ("home", "away"):
        t = side[k]
        s = {SOCCER_KEYS[x["name"]]: _num(x.get("displayValue")) for x in t.get("statistics", []) if x.get("name") in SOCCER_KEYS}
        out[k[0]] = {"id": str(t["team"]["id"]), "n": t["team"].get("displayName", ""), "g": _num(t.get("score")),
                     "yc": 0, "rc": 0, **s}
    ev = []
    for d in c.get("details", []):
        k = ids.get((d.get("team") or {}).get("id"))
        if not k:
            continue
        if d.get("yellowCard"):
            out[k]["yc"] += 1
        if d.get("redCard"):
            out[k]["rc"] += 1
        if d.get("scoringPlay") or d.get("redCard"):
            who = ((d.get("athletesInvolved") or [{}])[0]).get("shortName") or ""
            ev.append({"k": "g" if d.get("scoringPlay") else "r", "t": k, "m": (d.get("clock") or {}).get("displayValue", ""),
                       "p": who, "pen": bool(d.get("penaltyKick")), "og": bool(d.get("ownGoal"))})
    out["ev"] = ev
    # ligas menores: ESPN publica las estadísticas a 0 (no las mide) -> se tratan como desconocidas
    if not ((out["h"].get("pos") or 0) + (out["a"].get("pos") or 0) > 0 and (out["h"].get("sh") or 0) + (out["a"].get("sh") or 0) > 0):
        for k in "ha":
            for x in SOCCER_KEYS.values():
                out[k][x] = None
    has_stats = out["h"].get("sh") is not None
    out["cards_ok"] = bool(c.get("details")) or (has_stats and (out["h"]["g"] or 0) + (out["a"]["g"] or 0) == 0)
    return out


def parse_us(e: dict, lg: str) -> dict | None:
    c = (e.get("competitions") or [None])[0]
    if not c:
        return None
    side = {t.get("homeAway"): t for t in c.get("competitors", [])}
    if set(side) != {"home", "away"}:
        return None
    st = (e.get("status") or {}).get("type") or {}
    out = {"id": str(e["id"]), "code": lg, "t": e["date"], "status": st.get("name"), "neutral": bool(c.get("neutralSite")),
           "venue": (c.get("venue") or {}).get("fullName"), "ev": []}
    for k in ("home", "away"):
        t = side[k]
        rec = [r.get("summary") for r in t.get("records", []) if r.get("summary")]
        out[k[0]] = {"id": str(t["team"]["id"]), "n": t["team"].get("displayName", ""), "g": _num(t.get("score")),
                     "rec": rec[0] if rec else None}
    return out


def _get(url, params, getter):
    try:
        return getter(url, params)
    except Exception:  # noqa: BLE001 - un fallo deja ese bloque sin datos; nunca rompe la página
        return None


def fetch_soccer(code, ym, getter, cache=CACHE, today=None):
    t = today or date.today()
    p = cache / code / f"{ym}.json"
    prev = (t.year, t.month - 1) if t.month > 1 else (t.year - 1, 12)
    if p.exists() and (int(ym[:4]), int(ym[4:])) < prev:
        return json.loads(p.read_text())
    j = _get(SB.format(path=f"soccer/{code}"), {"dates": ym, "limit": 1000}, getter)
    if j is None:
        return json.loads(p.read_text()) if p.exists() else []
    rows = [x for x in (parse_soccer(e, code) for e in j.get("events", [])) if x]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rows))
    return rows


def fetch_us(lg, day: date, getter, cache=CACHE, today=None):
    t = today or date.today()
    p = cache / lg / f"{day:%Y%m%d}.json"
    if p.exists() and day < t - timedelta(days=2):
        return json.loads(p.read_text())
    j = _get(SB.format(path=US_PATH[lg]), {"dates": f"{day:%Y%m%d}"}, getter)
    if j is None:
        return json.loads(p.read_text()) if p.exists() else []
    rows = [x for x in (parse_us(e, lg) for e in j.get("events", [])) if x]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rows))
    return rows


def _months(n, today):
    y, m = today.year, today.month
    out = []
    for _ in range(n):
        out.append(f"{y}{m:02d}")
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return out[::-1]


def load_events(getter=None, today=None, workers=6, cache=CACHE) -> dict:
    """{'soccer': [...], 'national': [...], 'nba': [...], 'nfl': [...]} con todos los partidos (pasados y próximos)."""
    if getter is None:
        from kalshi_nba.data import _json as getter
    today = today or date.today()
    clubs, nat = soccer_codes()
    jobs = [("soccer", c, ym) for c in clubs for ym in _months(13, today)] + [("national", c, ym) for c in nat for ym in _months(30, today)]
    jobs += [(lg, lg, today + timedelta(days=d)) for lg in US_PATH for d in range(-US_DAYS[lg], 8)]

    def run(j):
        pool, code, x = j
        return pool, (fetch_us(code, x, getter, cache, today) if pool in US_PATH else fetch_soccer(code, x, getter, cache, today))
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(run, jobs))
    out = {"soccer": [], "national": [], "nba": [], "nfl": []}
    for pool, rows in res:
        out[pool] += rows
    for k, v in out.items():                                  # un partido puede salir en dos meses/días: sin duplicados
        seen = {}
        for r in v:
            seen[r["id"]] = r
        out[k] = sorted(seen.values(), key=lambda r: r["t"])
    return out


# ------------------------------------------------------------------------------------------------------- cálculo
def team_rows(events: list) -> pd.DataFrame:
    """Una fila por equipo y partido TERMINADO (perspectiva del equipo)."""
    rows = []
    for e in events:
        if e.get("status") not in FINAL or e["h"]["g"] is None or e["a"]["g"] is None:
            continue
        for me, op, ha in (("h", "a", "L"), ("a", "h", "V")):
            m, o = e[me], e[op]
            rows.append({"eid": e["id"], "t": pd.Timestamp(e["t"]), "code": e["code"], "team": m["id"], "name": m["n"],
                         "opp": o["n"], "ha": "N" if e.get("neutral") else ha, "gf": m["g"], "ga": o["g"],
                         "sh_f": m.get("sh"), "sh_a": o.get("sh"), "sot_f": m.get("sot"), "sot_a": o.get("sot"),
                         "cor_f": m.get("cor"), "cor_a": o.get("cor"), "pos": m.get("pos"),
                         "car_f": (m.get("yc", 0) + m.get("rc", 0)) if e.get("cards_ok", True) else None,
                         "car_a": (o.get("yc", 0) + o.get("rc", 0)) if e.get("cards_ok", True) else None})
    d = pd.DataFrame(rows)
    if d.empty:
        return pd.DataFrame(columns=["eid", "t", "code", "team", "name", "opp", "ha", "gf", "ga"])
    return d.sort_values("t").reset_index(drop=True)


def _mean(s, nd=2):
    s = pd.to_numeric(s, errors="coerce").dropna()
    return round(float(s.mean()), nd) if len(s) >= MIN_N else None


def averages(d: pd.DataFrame, soccer=True) -> dict | None:
    if len(d) == 0:
        return None
    tot = d["gf"] + d["ga"]
    out = {"n": int(len(d)), "gf": _mean(d["gf"]), "ga": _mean(d["ga"]),
           "w": int((d["gf"] > d["ga"]).sum()), "dr": int((d["gf"] == d["ga"]).sum()), "l": int((d["gf"] < d["ga"]).sum())}
    if soccer:
        out.update({"o15": _mean(tot > 1.5), "o25": _mean(tot > 2.5), "btts": _mean((d["gf"] > 0) & (d["ga"] > 0)),
                    "cs": _mean(d["ga"] == 0), "fts": _mean(d["gf"] == 0)})
        for k in ("sh_f", "sh_a", "sot_f", "sot_a", "cor_f", "cor_a", "car_f", "car_a", "pos"):
            out[k] = _mean(d[k], 1) if k in d else None
    else:
        out["tot"] = _mean(tot, 1)
    return out


def _form(d: pd.DataFrame, us=False) -> list:
    out = []
    for r in d.tail(5).iloc[::-1].itertuples():
        res = "G" if r.gf > r.ga else ("P" if r.gf < r.ga else "E")
        out.append({"d": r.t.strftime("%Y-%m-%d"), "o": r.opp, "ha": r.ha, "s": f"{r.gf:.0f}-{r.ga:.0f}", "r": res, "c": r.code})
    return out


def _exp(h: dict | None, a: dict | None, hv: dict | None, av: dict | None, f: str, ag: str):
    """Esperado del partido = (ataque local + defensa visitante)/2 + (ataque visitante + defensa local)/2.
    Usa los promedios como local/visitante si hay al menos 4 partidos; si no, los de todos los partidos."""
    H = hv if hv and hv["n"] >= 4 and hv.get(f) is not None and hv.get(ag) is not None else h
    A = av if av and av["n"] >= 4 and av.get(f) is not None and av.get(ag) is not None else a
    if not H or not A or any(x.get(k) is None for x in (H, A) for k in (f, ag)):
        return None
    return round((H[f] + A[ag]) / 2 + (A[f] + H[ag]) / 2, 2)


def league_avg(rows: pd.DataFrame, codes, kick, soccer=True) -> dict | None:
    """Promedios por partido de la competición en los 365 días previos (solo partidos anteriores al inicio)."""
    d = rows[rows["code"].isin(codes) & (rows["t"] < kick) & (rows["t"] >= kick - pd.Timedelta(days=365)) & (rows["ha"] != "V")]
    if len(d) < 20:
        return None
    tot = d["gf"] + d["ga"]
    out = {"n": int(len(d)), "goals": _mean(tot), "pts": _mean(tot, 1)}
    if soccer:
        out.update({"o15": _mean(tot > 1.5), "o25": _mean(tot > 2.5), "btts": _mean((d["gf"] > 0) & (d["ga"] > 0))})
        for k, (a, b) in {"shots": ("sh_f", "sh_a"), "sot": ("sot_f", "sot_a"), "corners": ("cor_f", "cor_a"), "cards": ("car_f", "car_a")}.items():
            out[k] = _mean(d[a] + d[b], 1) if a in d else None
    return out


def panel(rows: pd.DataFrame, hid: str, aid: str, kick, codes, soccer=True) -> dict:
    """Todo lo que muestra la ventana del partido, con datos anteriores al inicio."""
    kick = pd.Timestamp(kick)
    past = rows[rows["t"] < kick]
    th, ta = past[past["team"] == hid], past[past["team"] == aid]
    h, a = averages(th.tail(LAST), soccer), averages(ta.tail(LAST), soccer)
    hv, av = averages(th[th["ha"] == "L"].tail(LAST), soccer), averages(ta[ta["ha"] == "V"].tail(LAST), soccer)
    h2h = past[(past["team"] == hid) & (past["eid"].isin(ta["eid"]))].tail(5).iloc[::-1]
    last = lambda t: {"eid": str(t.iloc[-1]["eid"]), "code": t.iloc[-1]["code"]} if len(t) else None
    out = {"last": {"h": last(th), "a": last(ta)}, "form": {"h": _form(th), "a": _form(ta)}, "avg": {"h": h, "a": a}, "vavg": {"h": hv, "a": av},
           "h2h": [{"d": r.t.strftime("%Y-%m-%d"), "s": f"{r.gf:.0f}-{r.ga:.0f}", "ha": r.ha, "c": r.code} for r in h2h.itertuples()],
           "lg": league_avg(rows, codes, kick, soccer)}
    if soccer:
        out["exp"] = {k: _exp(h, a, hv, av, f, ag) for k, (f, ag) in
                      {"goals": ("gf", "ga"), "shots": ("sh_f", "sh_a"), "sot": ("sot_f", "sot_a"),
                       "corners": ("cor_f", "cor_a"), "cards": ("car_f", "car_a")}.items()}
    else:
        out["exp"] = {"pts": _exp(h, a, hv, av, "gf", "ga")}
    return out


def _resolve(events: list, g: dict, pool: str):
    """(id local, id visitante, evento ESPN) de un partido de la página."""
    from kalshi_soccer.kalshi import _same
    from .logos import ALIASES
    by_id = {e["id"]: e for e in events}
    e = by_id.get(str(g.get("id")))
    if e and (pool != "soccer" or g["sport"] != "liga" or g.get("espn")):
        return e["h"]["id"], e["a"]["id"], e
    names = {}
    for x in events:
        for k in "ha":
            names.setdefault(x[k]["n"], x[k]["id"])

    def find(n):
        n = ALIASES.get(n, n)
        if n in names:
            return names[n]
        hits = {i for m, i in names.items() if _same(m, n)}
        return hits.pop() if len(hits) == 1 else None
    hid, aid = find(g["home"]), find(g["away"])
    if not hid or not aid:
        return None, None, None
    t = pd.Timestamp(g["t"])
    ev = [x for x in events if x["h"]["id"] == hid and x["a"]["id"] == aid and abs(pd.Timestamp(x["t"]) - t) <= pd.Timedelta(hours=36)]
    return hid, aid, (ev[0] if ev else None)


POOL = {"nba": "nba", "nfl": "nfl", "liga": "soccer", "club": "soccer", "intl": "national"}


def build(games: list, events: dict) -> dict:
    rows = {k: team_rows(v) for k, v in events.items()}
    clubs, nat = soccer_codes()
    out = {}
    for g in games:
        pool = POOL.get(g["sport"])
        if not pool or not events.get(pool):
            continue
        hid, aid, ev = _resolve(events[pool], g, pool)
        if not hid:
            continue
        soccer = pool in ("soccer", "national")
        code = (ev or {}).get("code") or g.get("code")
        codes = nat if pool == "national" else ([code] if code else clubs)
        p = panel(rows[pool], hid, aid, g["t"], codes, soccer)
        p["venue"] = (ev or {}).get("venue")
        p["eid"] = (ev or {}).get("id")
        if pool in US_PATH and ev:
            p["rec"] = [ev["h"].get("rec"), ev["a"].get("rec")]
        out[f"{g['sport']}:{g['id']}"] = p
    return out


def main():
    from . import pagina
    now = pd.Timestamp.now(tz=pagina.TZ)
    finals = pagina._final_picks()
    games = pagina.games_us("nba", now, finals) + pagina.games_us("nfl", now, finals) + pagina.games_ligas(now) + pagina.games_intl(now, finals)
    t0 = time.time()
    events = load_events()
    stats = build(games, events)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"updated": now.isoformat(), "games": stats}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"estadísticas: {len(stats)}/{len(games)} partidos con datos ({time.time() - t0:.0f}s); "
          f"eventos { {k: len(v) for k, v in events.items()} }")


if __name__ == "__main__":
    main()
