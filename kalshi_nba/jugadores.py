"""Picks y combinadas de JUGADORES (sección «Jugadores»).

Fuente de la probabilidad: el precio de Kalshi de cada mercado de jugador («Jugador: 20+ puntos»), punto medio entre
compra y venta con distancia ≤ 10¢. Es el mercado: lo más fiable que tenemos (la lección del proyecto).
Nuestra PROYECCIÓN (NBA: promedio de sus últimos partidos con minutos y desviación) se muestra al lado como dato, y se
registra para probarla en sombra; NO cambia la probabilidad publicada hasta pasar su prueba (JUGADORES_RESEARCH.md).
Resultados: NBA con el box score de ESPN (puntos, rebotes, asistencias); se registran en predictions/jugadores_resultados.csv.
  python -m kalshi_nba.jugadores        # -> predictions/jugadores.json
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("predictions/jugadores.json")
RES = Path("predictions/jugadores_resultados.csv")
SERIES = {  # serie de Kalshi -> (deporte, estadística, campo del box score NBA)
    "KXNBAPTS": ("nba", "Puntos", "pts"), "KXNBAREB": ("nba", "Rebotes", "reb"), "KXNBAAST": ("nba", "Asistencias", "ast"),
    "KXNBA3PT": ("nba", "Triples", None),
    "KXNFLPASSYDS": ("nfl", "Yardas de pase", None), "KXNFLRSHYDS": ("nfl", "Yardas de carrera", None),
    "KXNFLRECYDS": ("nfl", "Yardas de recepción", None), "KXNFLANYTD": ("nfl", "Anota touchdown", None),
}
SOCCER_SERIES = ["KXEPLANYGOAL", "KXLALIGAGOAL", "KXSERIEAGOAL", "KXBUNDESLIGAGOAL", "KXLIGUE1GOAL", "KXUCLGOAL", "KXLIGAMXGOAL"]
MAX_SPREAD, LO, HI = 0.10, 0.55, 0.92


def _f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def fetch_series(series: str, getter=None) -> list:
    if getter is None:
        from kalshi_lineup.kalshi_history import get as getter
    out, cur = [], None
    for _ in range(20):
        j = getter("/markets", {"series_ticker": series, "status": "open", "limit": 1000, **({"cursor": cur} if cur else {})}) or {}
        out += j.get("markets", [])
        cur = j.get("cursor")
        if not cur or not j.get("markets"):
            break
    return out


def parse(series: str, m: dict, abbrs: set) -> dict | None:
    sport, stat, _ = SERIES.get(series, ("soccer", "Marca gol", None))
    title = m.get("title") or ""
    if ":" in title:
        name, rest = title.split(":", 1)
        k = re.search(r"(\d+)\+", rest)
        line = int(k.group(1)) if k else 1
    else:                                                     # p. ej. goleador: «¿Marcará X?» / subtítulo con el nombre
        name, line = (m.get("yes_sub_title") or title).strip(), 1
    bid, ask = _f(m.get("yes_bid_dollars")), _f(m.get("yes_ask_dollars"))
    if bid is None or ask is None or ask <= 0 or ask - bid > MAX_SPREAD or bid <= 0:
        return None
    ev = m.get("event_ticker", "")
    code = ev.split("-", 1)[1] if "-" in ev else ""
    pair = re.sub(r"^\d{2}[A-Z]{3}\d{2}", "", code)
    md = re.match(r"^(\d{2})([A-Z]{3})(\d{2})", code)
    day = pd.to_datetime(f"20{md.group(1)}-{md.group(2)}-{md.group(3)}", format="%Y-%b-%d").strftime("%Y-%m-%d") if md else None
    seg = m["ticker"].split("-")
    team = None
    if sport in ("nba", "nfl") and len(seg) >= 3:
        code = seg[2]
        team = next((code[:n] for n in (3, 2) if code[:n] in abbrs and code[:n] in pair), None)
    return {"series": series, "sport": sport, "stat": stat, "player": name.strip(), "line": line, "team": team, "pair": pair,
            "event": ev, "day": day, "ticker": m["ticker"], "bid": bid, "ask": ask, "p": round((bid + ask) / 2, 4),
            "when": m.get("occurrence_datetime") or m.get("expected_expiration_time") or m.get("close_time")}


def attach(rows: list, games: list) -> list:
    """Une cada mercado con su partido de la página (NBA/NFL por abreviaturas y fecha)."""
    from .kalshi import ABBR, NFL_ABBR
    out = []
    for r in rows:
        if r["sport"] not in ("nba", "nfl"):
            continue
        ab = ABBR if r["sport"] == "nba" else NFL_ABBR
        for g in games:
            if g["sport"] != r["sport"]:
                continue
            h, a = ab.get(str(g.get("home_id"))), ab.get(str(g.get("away_id")))
            if not h or not a or r["pair"] not in (a + h, h + a):
                continue
            gday = pd.Timestamp(g["t"]).tz_convert("America/New_York").strftime("%Y-%m-%d")
            if r.get("day") and r["day"] != gday:                 # mismo cruce en días seguidos: manda la fecha del mercado
                continue
            if not r.get("day") and r["when"] and abs(pd.Timestamp(r["when"]) - pd.Timestamp(g["t"])) > pd.Timedelta(hours=36):
                continue
            side = "home" if r["team"] == h else ("away" if r["team"] == a else None)
            out.append({**r, "gid": g["id"], "side": side, "team_name": g["home"] if side == "home" else (g["away"] if side == "away" else None),
                        "logo": g.get("hlogo") if side == "home" else (g.get("alogo") if side == "away" else None),
                        "partido": f"{g['away']} en {g['home']}", "t": g["t"], "state": g.get("state", "pre")})
            break
    return out


# ------------------------------------------------------------------ proyección propia (NBA, solo informativa)
def nba_history(days: int = 60, box_dir: Path = Path("data/nba/box"), now=None) -> pd.DataFrame:
    """Líneas por jugador de los partidos NBA terminados de los últimos `days` días (box score en caché)."""
    from kalshi_nba.data import load_league
    from kalshi_lineup.box import load_boxes
    now = pd.Timestamp(now or pd.Timestamp.now(tz="UTC"))
    g = load_league("nba", first_season=now.year if now.month >= 9 else now.year - 1, with_odds=False, verbose=False)
    g = g[(g["status"] == "STATUS_FINAL") & (pd.to_datetime(g["kickoff_utc"], utc=True) >= now - pd.Timedelta(days=days))]
    boxes = load_boxes(g["event_id"], cache_dir=str(box_dir), workers=8)
    kick = dict(zip(g["event_id"].astype(str), pd.to_datetime(g["kickoff_utc"], utc=True)))
    rows = []
    for e, b in boxes.items():
        for p in b.get("players", []):
            if p.get("dnp") or not (p.get("min") or 0):
                continue
            rows.append({"event_id": e, "t": kick.get(e), "name": p["name"], "min": p.get("min") or 0,
                         **{k: p.get(k) for k in ("pts", "reb", "ast")}})
    return pd.DataFrame(rows)


def projection(hist: pd.DataFrame, name: str, field: str, before, n: int = 10) -> dict | None:
    if hist is None or hist.empty or not field:
        return None
    h = hist[(hist["name"] == name) & (hist["t"] < pd.Timestamp(before))].sort_values("t").tail(n)
    v = pd.to_numeric(h[field], errors="coerce").dropna()
    if len(v) < 4:
        return None
    mu, sd = float(v.mean()), max(float(v.std(ddof=1)), 1.5, 0.25 * float(v.mean()) ** 0.5 * 2)
    return {"media": round(mu, 1), "partidos": int(len(v)), "min": round(float(h["min"].mean()), 1), "sd": round(sd, 2)}


def p_model(proj: dict | None, line: int) -> float | None:
    """P(estadística >= línea) con aproximación normal y corrección de continuidad. Solo informativa (en sombra)."""
    if not proj:
        return None
    z = (line - 0.5 - proj["media"]) / proj["sd"]
    return round(float(0.5 * math.erfc(z / math.sqrt(2))), 4)


# ------------------------------------------------------------------ picks, combinadas y resultados
def best_lines(rows: list) -> list:
    """Por jugador y estadística, la línea más «útil»: probabilidad entre 55% y 92%, la más cercana al 72%."""
    by = {}
    for r in rows:
        if not (LO <= r["p"] <= HI):
            continue
        k = (r["gid"], r["player"], r["stat"])
        if k not in by or abs(r["p"] - 0.72) < abs(by[k]["p"] - 0.72):
            by[k] = r
    return sorted(by.values(), key=lambda r: -r["p"])


def combos(picks: list, specs=((3, 1.6, "Más segura"), (4, 2.5, "Equilibrada"), (5, 4.0, "Ambiciosa"))) -> list:
    """Combinadas de jugadores: jugadores de partidos DISTINTOS (en un mismo partido están correlacionados)."""
    from itertools import combinations
    pool = [p for p in picks if p["state"] == "pre"][:20]
    out, seen = [], set()
    for k, min_odds, name in specs:
        best = None
        for c in combinations(pool, k):
            if len({p["gid"] for p in c}) < k:
                continue
            P = float(np.prod([p["p"] for p in c])); O = float(np.prod([1 / p["p"] for p in c]))
            sig = "|".join(sorted(p["ticker"] for p in c))
            if O < min_odds or sig in seen:
                continue
            if best is None or P > best["P"]:
                best = {"perfil": name, "P": round(P, 4), "O": round(O, 3), "legs": [p["ticker"] for p in c], "sig": sig}
        if best:
            seen.add(best.pop("sig")); out.append(best)
    return out


def resolve(rows: list, box_dir: Path = Path("data/nba/box")) -> list:
    """Aciertos NBA (puntos/rebotes/asistencias) con el box score de los partidos ya terminados."""
    from kalshi_lineup.box import load_boxes
    done = [r for r in rows if r["sport"] == "nba" and r["state"] == "post" and SERIES[r["series"]][2]]
    boxes = load_boxes({r["gid"] for r in done}, cache_dir=str(box_dir), workers=6) if done else {}
    out = []
    for r in done:
        b = boxes.get(str(r["gid"]))
        if not b:
            continue
        pl = [p for p in b.get("players", []) if p.get("name") == r["player"]]
        if not pl:
            continue
        v = _f(pl[0].get(SERIES[r["series"]][2]))
        if v is None:
            continue
        out.append({**r, "valor": v, "acierto": int(v >= r["line"])})
    return out


def build(games: list, now=None, getter=None, hist: pd.DataFrame | None = None) -> dict:
    from .kalshi import ABBR, NFL_ABBR
    abbrs = set(ABBR.values()) | set(NFL_ABBR.values())
    rows = []
    for s in SERIES:
        try:
            rows += [x for x in (parse(s, m, abbrs) for m in fetch_series(s, getter)) if x]
        except Exception as ex:  # noqa: BLE001 - una serie que falla no detiene el resto
            print("AVISO Kalshi", s, type(ex).__name__)
    rows = attach(rows, games)
    for r in rows:
        if r["sport"] == "nba":
            pr = projection(hist, r["player"], SERIES[r["series"]][2], r["t"])
            r["proy"], r["p_modelo"] = pr, p_model(pr, r["line"])
    picks = best_lines(rows)
    return {"updated": pd.Timestamp(now or pd.Timestamp.now(tz="UTC")).isoformat(), "picks": picks, "combis": combos(picks)}


def record(resolved: list, path: Path = RES) -> int:
    cols = ["fecha", "sport", "gid", "player", "stat", "line", "p", "p_modelo", "valor", "acierto"]
    seen = set()
    if path.exists():
        d = pd.read_csv(path, dtype={"gid": str})
        seen = set(zip(d["gid"], d["player"], d["stat"]))
    new = [{"fecha": str(r["t"])[:10], "sport": r["sport"], "gid": str(r["gid"]), "player": r["player"], "stat": r["stat"],
            "line": r["line"], "p": r["p"], "p_modelo": r.get("p_modelo"), "valor": r["valor"], "acierto": r["acierto"]}
           for r in resolved if (str(r["gid"]), r["player"], r["stat"]) not in seen]
    if new:
        pd.DataFrame(new, columns=cols).to_csv(path, mode="a", header=not path.exists(), index=False)
    return len(new)


def main():
    from . import pagina
    now = pd.Timestamp.now(tz=pagina.TZ)
    finals = pagina._final_picks()
    data = pagina.collect(score_getter=None)                   # incluye estado, logos y escudos de cada partido
    games = [g for g in data["games"] if g["sport"] in ("nba", "nfl")]
    try:
        hist = nba_history(now=now)
    except Exception as ex:  # noqa: BLE001
        print("AVISO historial NBA:", type(ex).__name__); hist = None
    out = build(games, now, hist=hist)
    # resultados de días anteriores: se conservan los picks ya publicados de partidos terminados
    prev = {}
    try:
        prev = {p["ticker"]: p for p in json.loads(OUT.read_text(encoding="utf-8")).get("picks", [])}
    except (OSError, ValueError):
        pass
    state = {str(g["id"]): g.get("state") for g in games}
    keep = [{**p, "state": state.get(str(p["gid"]), p["state"])} for t, p in prev.items()
            if t not in {x["ticker"] for x in out["picks"]} and state.get(str(p["gid"])) in ("in", "post")]
    out["picks"] += keep
    res = resolve(out["picks"])
    hits = {(str(r["gid"]), r["player"], r["stat"]): (r["acierto"], r["valor"]) for r in res}
    for p in out["picks"]:
        h = hits.get((str(p["gid"]), p["player"], p["stat"]))
        p["hit"], p["valor"] = (None, None) if h is None else (bool(h[0]), h[1])
    n = record(res)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":"), default=str) + "\n", encoding="utf-8")
    print(f"jugadores: {len(out['picks'])} picks, {len(out['combis'])} combinadas, {n} resultados nuevos")


if __name__ == "__main__":
    main()
