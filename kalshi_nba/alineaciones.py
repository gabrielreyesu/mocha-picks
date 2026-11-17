"""Alineaciones para la ventana de cada partido (pestaña «Alineaciones», como en Oddster).

* Fútbol: once OFICIAL con formación cuando ESPN lo publica (~1 h antes); si no, once PROBABLE = el de su último partido.
* NBA: titulares del último partido de cada equipo, marcando los que hoy están de baja; con el partido jugado, los reales.
* NFL: de momento sin alineación (nuestro box score solo tiene los quarterbacks sin nombre); las bajas están en General.
Solo información de ESPN publicada antes de cada partido. Es informativo: no cambia el pick (las alineaciones se
evalúan aparte en las pruebas en sombra).
  python -m kalshi_nba.alineaciones        # -> predictions/lineups.json
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

SUM = "https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/summary"
CACHE = Path("data/lineups")
OUT = Path("predictions/lineups.json")
FINAL = {"STATUS_FULL_TIME", "STATUS_FINAL", "STATUS_FINAL_AET", "STATUS_FINAL_PEN"}


def parse_rosters(j: dict) -> dict:
    """{'h'|'a': {formation, xi:[{n, num, pos, place}], bench:[...]}} ; vacío si no hay alineación."""
    out = {}
    for t in (j or {}).get("rosters", []):
        k = "h" if t.get("homeAway") == "home" else "a"
        xi, bench = [], []
        for x in t.get("roster", []):
            a = x.get("athlete") or {}
            row = {"n": a.get("shortName") or a.get("displayName", ""), "num": x.get("jersey"),
                   "pos": (x.get("position") or {}).get("abbreviation", ""), "place": int(x.get("formationPlace") or 0)}
            (xi if x.get("starter") else bench).append(row)
        if xi:
            out[k] = {"formation": t.get("formation"), "xi": sorted(xi, key=lambda r: r["place"] or 99), "bench": bench[:12]}
    return out


def _status(j):
    return (((((j or {}).get("header") or {}).get("competitions") or [{}])[0].get("status") or {}).get("type") or {}).get("name")


def summary(code, eid, getter, cache=CACHE, use_cache=True):
    p = cache / f"{code}_{eid}.json"
    if use_cache and p.exists():
        return json.loads(p.read_text())
    try:
        j = getter(SUM.format(code=code), {"event": str(eid)})
    except Exception:  # noqa: BLE001
        return None
    if not j:
        return None
    out = {"status": _status(j), "rosters": parse_rosters(j)}
    if out["status"] in FINAL:                                     # partido cerrado: ya no cambia -> caché
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(out))
    return out


def soccer(g: dict, st: dict, getter) -> dict | None:
    code, eid = g.get("code"), (st or {}).get("eid")
    side = {}
    if code and eid:
        cur = summary(code, eid, getter, use_cache=True)
        if cur and cur["rosters"]:
            side = {k: {**v, "tipo": "oficial"} for k, v in cur["rosters"].items()}
    for k in ("h", "a"):
        if k in side:
            continue
        last = ((st or {}).get("last") or {}).get(k)
        if last:
            prev = summary(last["code"], last["eid"], getter)
            team = (prev or {}).get("rosters") or {}
            # en su último partido pudo ser local o visitante: se toma el lado del mismo equipo por nombre de la forma
            mine = _pick_side(team, g, k, st)
            if mine:
                side[k] = {**mine, "tipo": "probable", "bench": []}
    return side or None


def _pick_side(rosters: dict, g: dict, k: str, st: dict):
    """El último partido del equipo: si jugó de local allí, su lado es 'h'; se deduce de la forma (ha del más reciente)."""
    f = (((st or {}).get("form") or {}).get(k) or [{}])[0]
    where = "h" if f.get("ha") in ("L", "N") else "a"
    return rosters.get(where)


def us(g: dict, st: dict, box_dir: Path) -> dict | None:
    """NBA: titulares del último partido de cada equipo (box score en caché), marcando los que hoy están de baja."""
    if g["sport"] != "nba":
        return None                                        # NFL: ESPN no da titulares en nuestro box (solo QB sin nombre)
    out = {}
    inj = g.get("inj") or {}
    for k, key, tid in (("h", "home", g.get("home_id")), ("a", "away", g.get("away_id"))):
        last = ((st or {}).get("last") or {}).get(k)
        p = box_dir / f"{last['eid']}.json" if last else None
        if not p or not p.exists() or not tid:
            continue
        b = json.loads(p.read_text())
        bajas = {x.split(" (")[0] for x in inj.get(key, [])}
        xi = [x for x in b.get("players", []) if x.get("starter") and str(x.get("team_id")) == str(tid)]
        if xi:
            out[k] = {"tipo": "probable", "xi": [{"n": x["name"], "pos": "", "baja": x["name"] in bajas} for x in xi],
                      "nota": "Titulares de su último partido" + (" (en rojo, los que hoy están de baja)" if bajas & {x["name"] for x in xi} else "")}
    return out or None


def build(games: list, stats: dict, getter=None, box_root=Path("data")) -> dict:
    if getter is None:
        from kalshi_nba.data import _json as getter
    now = pd.Timestamp.now(tz="UTC")
    todo = [g for g in games if now - pd.Timedelta(days=2) <= pd.Timestamp(g["t"]) <= now + pd.Timedelta(days=3)]

    def one(g):
        st = stats.get(f"{g['sport']}:{g['id']}") or {}
        try:
            if g["sport"] in ("nba", "nfl"):
                return g, us(g, st, box_root / g["sport"] / "box")
            return g, soccer(g, st, getter)
        except Exception:  # noqa: BLE001 - una alineación que falla no rompe nada
            return g, None
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(one, todo))
    return {f"{g['sport']}:{g['id']}": r for g, r in res if r}


def main():
    from . import pagina
    now = pd.Timestamp.now(tz=pagina.TZ)
    finals = pagina._final_picks()
    games = pagina.games_us("nba", now, finals) + pagina.games_us("nfl", now, finals) + pagina.games_ligas(now) + pagina.games_intl(now, finals)
    try:
        stats = json.loads(Path("predictions/stats.json").read_text(encoding="utf-8")).get("games", {})
    except (OSError, ValueError):
        stats = {}
    out = build(games, stats)
    OUT.write_text(json.dumps({"updated": now.isoformat(), "games": out}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    n_of = sum(1 for v in out.values() for s in v.values() if s.get("tipo") == "oficial")
    print(f"alineaciones: {len(out)} partidos ({n_of} onces oficiales)")


if __name__ == "__main__":
    main()
