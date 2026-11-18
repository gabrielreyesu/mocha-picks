"""Combinadas del día (1 a 5, de 3 a 6 jugadas) con registro auditable de su resultado.

* Se calculan con los picks de partidos que aún no empezaron, igual que en la página.
* Cada día (hora de Chicago) se recalculan en cada corrida hasta que empieza el PRIMER partido de ese día: desde ese
  momento quedan CONGELADAS (no se puede cambiar una combinada después de ver resultados).
* Cuando todas las jugadas de una combinada tienen resultado, se escribe su resultado.
Archivo: predictions/combinadas.jsonl (una línea por versión del día o por resultado; solo se añaden líneas).
No es una recomendación de apuesta.
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

import pandas as pd

FILE_NAME = "combinadas.jsonl"
MARKETS = ("Ganador", "Doble oportunidad", "Goles", "Ambos anotan", "Hándicap", "Total de puntos", "Puntos")
SPECS = [
    {"n": "Más segura", "k": (3,), "min_odds": 1.6, "obj": "p"},
    {"n": "Equilibrada", "k": (4,), "min_odds": 2.5, "obj": "p"},
    {"n": "Con valor", "k": (3, 4), "min_odds": 1.5, "obj": "ev", "real": True, "min_p": 0.2},
    {"n": "Ambiciosa", "k": (5,), "min_odds": 4.0, "obj": "p"},
    {"n": "Máxima", "k": (6,), "min_odds": 6.0, "obj": "p"},
]
POOL = 22


def legs(games: list) -> list:
    out = []
    for g in games:
        if g.get("state") != "pre":
            continue
        for p in g.get("picks") or []:
            pr = p.get("prob")
            if pr is None or pr < 0.55 or not str(p.get("mercado", "")).startswith(MARKETS):
                continue
            src = str(p.get("fuente", ""))
            if "validación" in src:
                continue
            if g["sport"] in ("nba", "nfl") and src == "modelo":   # en NBA/NFL el modelo solo es peor que el mercado
                continue
            price = p.get("precio")
            real = price is not None and 0.02 < price < 0.99
            out.append({"mkt": ("casas" in src or "Kalshi" in src), "sport": g["sport"], "id": str(g["id"]), "partido": f"{g['home']} vs {g['away']}", "comp": g.get("comp"),
                        "t": g["t"], "mercado": p["mercado"], "pick": p["pick"], "prob": float(pr),
                        "odds": round(1 / price if real else 1 / pr, 4), "real": bool(real)})
    return sorted(out, key=lambda l: -l["prob"])


def build(cands: list) -> list:
    tickets, seen = [], set()
    for sp in SPECS:
        pool = [l for l in cands if l["real"] and l.get("mkt") and l["prob"] * l["odds"] > 1.02] if sp.get("real") else cands
        pool = pool[:POOL]
        best = None
        for k in sp["k"]:
            for c in combinations(pool, k):
                if len({(l["sport"], l["id"]) for l in c}) < k:           # partidos distintos
                    continue
                P = O = 1.0
                for l in c:
                    P *= l["prob"]; O *= l["odds"]
                if O < sp["min_odds"] or P < sp.get("min_p", 0):
                    continue
                sig = "|".join(sorted(f"{l['sport']}{l['id']}{l['mercado']}{l['pick']}" for l in c))
                if sig in seen:
                    continue
                score = P * O if sp["obj"] == "ev" else P
                if best is None or score > best["score"]:
                    best = {"perfil": sp["n"], "legs": list(c), "P": round(P, 4), "O": round(O, 4), "score": score, "sig": sig}
        if best:
            seen.add(best["sig"])
            best.pop("score"); best.pop("sig")
            tickets.append(best)
    return tickets


def _day(t: str, tz: str) -> str:
    return pd.Timestamp(t).tz_convert(tz).strftime("%Y-%m-%d")


def load(path: Path) -> list:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue                                              # línea dañada: se ignora
    return out


def latest(rows: list) -> dict:
    """{fecha: última versión de las combinadas de ese día}."""
    d = {}
    for r in rows:
        if r.get("tipo") == "combinadas" and (r["fecha"] not in d or r["creado"] > d[r["fecha"]]["creado"]):
            d[r["fecha"]] = r
    return d


def update(games: list, now, folder: Path, tz: str, write: bool = True) -> dict:
    """Recalcula los días no congelados, resuelve los terminados y devuelve {fecha: {creado, congelada, tickets}}."""
    path = folder / FILE_NAME
    rows = load(path)
    cur = latest(rows)
    done = {r["fecha"] for r in rows if r.get("tipo") == "resultado"}
    now = pd.Timestamp(now)
    by_day: dict = {}
    for g in games:
        by_day.setdefault(_day(g["t"], tz), []).append(g)
    new = []
    for day, gs in sorted(by_day.items()):
        first = min(pd.Timestamp(g["t"]) for g in gs)
        frozen = now >= first
        if frozen:
            continue
        tk = build(legs(gs))
        old = cur.get(day)
        sig = lambda ts: [[(l["sport"], l["id"], l["mercado"], l["pick"]) for l in t["legs"]] for t in ts]
        if tk and (old is None or sig(old["tickets"]) != sig(tk)):            # solo si cambian las jugadas
            row = {"tipo": "combinadas", "fecha": day, "creado": now.isoformat(), "tickets": tk}
            new.append(row); cur[day] = row
    # resultados: con los aciertos por jugada que ya calculó la página
    hits = {(g["sport"], str(g["id"]), p.get("mercado"), p.get("pick")): p.get("hit") for g in games for p in g.get("picks") or []}
    for day, r in cur.items():
        if day in done:
            continue
        res = []
        for t in r["tickets"]:
            hs = [hits.get((l["sport"], l["id"], l["mercado"], l["pick"])) for l in t["legs"]]
            if any(h is False for h in hs):
                res.append(False)
            elif all(h is True for h in hs):
                res.append(True)
            else:
                res = None
                break
        if res is not None and r["tickets"]:
            new.append({"tipo": "resultado", "fecha": day, "creado": now.isoformat(),
                        "tickets": [{"perfil": t["perfil"], "P": t["P"], "O": t["O"], "n": len(t["legs"]), "acierto": h}
                                    for t, h in zip(r["tickets"], res)]})
    if new and write:
        folder.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            for x in new:
                fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    out = {}
    for day, r in cur.items():
        if day not in by_day:
            continue
        first = min(pd.Timestamp(g["t"]) for g in by_day[day])
        tks = []
        for t in r["tickets"]:
            ls = [{**l, "hit": hits.get((l["sport"], l["id"], l["mercado"], l["pick"]))} for l in t["legs"]]
            st = False if any(l["hit"] is False for l in ls) else (True if all(l["hit"] is True for l in ls) else None)
            tks.append({**t, "legs": ls, "acierto": st})
        out[day] = {"creado": r["creado"], "congelada": bool(now >= first), "tickets": tks}
    return out


def summary(folder: Path) -> dict:
    """Resumen para Progreso: acierto real frente a la probabilidad prevista, por perfil."""
    rows = [r for r in load(folder / FILE_NAME) if r.get("tipo") == "resultado"]
    last = {}
    for r in rows:
        if r["fecha"] not in last or r["creado"] > last[r["fecha"]]["creado"]:
            last[r["fecha"]] = r
    by = {}
    for r in last.values():
        for t in r["tickets"]:
            b = by.setdefault(t["perfil"], {"n": 0, "aciertos": 0, "prob_media": 0.0, "cuota_media": 0.0})
            b["n"] += 1; b["aciertos"] += int(bool(t["acierto"])); b["prob_media"] += t["P"]; b["cuota_media"] += t["O"]
    for b in by.values():
        b["prob_media"] = round(b["prob_media"] / b["n"], 4); b["cuota_media"] = round(b["cuota_media"] / b["n"], 2)
        b["acierto"] = round(b["aciertos"] / b["n"], 4)
    order = [s["n"] for s in SPECS]
    return {"dias": len(last), "por_perfil": [{"perfil": k, **by[k]} for k in order if k in by]}


# ------------------------------------------------------------------ registro de aciertos por mercado
PICKS_FILE = "picks_resultados.csv"
PICK_COLS = ["fecha", "sport", "id", "mercado", "pick", "prob", "fuente", "acierto"]


def record_picks(games: list, folder: Path, tz: str) -> int:
    """Añade una fila por jugada resuelta (una sola vez por partido y mercado). La probabilidad es la publicada antes
    del partido (los picks de partidos empezados ya no se recalculan)."""
    path = folder / PICKS_FILE
    seen = set()
    if path.exists():
        d = pd.read_csv(path, dtype={"id": str}, usecols=["sport", "id", "mercado"])
        seen = set(zip(d["sport"], d["id"], d["mercado"]))
    rows = []
    for g in games:
        for p in g.get("picks") or []:
            if p.get("hit") is None or p.get("prob") is None or (g["sport"], str(g["id"]), p["mercado"]) in seen:
                continue
            rows.append({"fecha": _day(g["t"], tz), "sport": g["sport"], "id": str(g["id"]), "mercado": p["mercado"], "pick": p["pick"],
                         "prob": round(float(p["prob"]), 4), "fuente": p.get("fuente"), "acierto": int(bool(p["hit"]))})
    if rows:
        folder.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows, columns=PICK_COLS).to_csv(path, mode="a", header=not path.exists(), index=False)
    return len(rows)


def picks_summary(folder: Path) -> list:
    path = folder / PICKS_FILE
    if not path.exists():
        return []
    d = pd.read_csv(path)
    d["grupo"] = d["mercado"].str.replace(r" \(línea segura\)| seguro", "", regex=True)
    out = []
    for m, x in d.groupby("grupo"):
        out.append({"mercado": m, "n": int(len(x)), "prob_media": round(float(x["prob"].mean()), 4), "acierto": round(float(x["acierto"].mean()), 4)})
    return sorted(out, key=lambda r: -r["n"])


def comp_summary(folder: Path, min_n: int = 10) -> list:
    """Acierto del pick de GANADOR por competición (para saber en qué ligas confiar más)."""
    path = folder / PICKS_FILE
    if not path.exists():
        return []
    d = pd.read_csv(path, dtype={"id": str})
    d = d[d["mercado"] == "Ganador"]
    comp = {}
    for f, idc, cc in (("intl_registry.csv", "event_id", "competicion"), ("registry.csv", "match_id", "competition")):
        p = folder / f
        if p.exists():
            r = pd.read_csv(p, dtype={idc: str}, usecols=[idc, cc])
            comp.update(dict(zip(r[idc].astype(str), r[cc])))
    d["comp"] = [("NBA" if s == "nba" else "NFL" if s == "nfl" else comp.get(i, "Otras")) for s, i in zip(d["sport"], d["id"])]
    out = [{"comp": c, "n": int(len(x)), "prob_media": round(float(x["prob"].mean()), 4), "acierto": round(float(x["acierto"].mean()), 4)}
           for c, x in d.groupby("comp") if len(x) >= min_n]
    return sorted(out, key=lambda r: -r["n"])
