"""Cuotas de casas desde The Odds API (the-odds-api.com) para partidos SIN cuotas de ESPN (sobre todo copas nacionales).

Requiere la variable ODDS_API_KEY (secreto de GitHub Actions). Sin clave no hace nada. El plan gratuito da 500 créditos
al mes: cada consulta de una competición (mercados 1X2 y totales, región eu) cuesta 2. Por eso solo se consultan las
competiciones con partidos sin cuotas en los próximos días, con un tope por corrida, y se respeta el saldo que informa la API.
Probabilidades: mediana de las casas, quitando el margen de cada una (normalización proporcional), como las de ESPN.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import requests

BASE = "https://api.the-odds-api.com/v4"
# código ESPN -> clave de The Odds API (solo se usan las que la API declare activas)
SPORT = {"eng.fa": "soccer_fa_cup", "eng.league_cup": "soccer_england_efl_cup", "esp.copa_del_rey": "soccer_spain_copa_del_rey",
         "ita.coppa_italia": "soccer_italy_coppa_italia", "ger.dfb_pokal": "soccer_germany_dfb_pokal",
         "fra.coupe_de_france": "soccer_france_coupe_de_france", "usa.1": "soccer_usa_mls",
         "conmebol.sudamericana": "soccer_conmebol_copa_sudamericana", "conmebol.libertadores": "soccer_conmebol_copa_libertadores",
         "eng.2": "soccer_efl_champ", "esp.2": "soccer_spain_segunda_division", "ita.2": "soccer_italy_serie_b",
         "ger.2": "soccer_germany_bundesliga2", "fra.2": "soccer_france_ligue_two", "por.1": "soccer_portugal_primeira_liga",
         "ned.1": "soccer_netherlands_eredivisie", "bel.1": "soccer_belgium_first_div", "tur.1": "soccer_turkey_super_league",
         "sco.1": "soccer_spl", "mex.1": "soccer_mexico_ligamx", "bra.1": "soccer_brazil_campeonato",
         "arg.1": "soccer_argentina_primera_division", "ksa.1": "soccer_saudi_arabia_pro_league"}
# prioridad: primero donde más falta (copas y competiciones sin validar), luego el resto
PRIORITY = ["eng.fa", "eng.league_cup", "esp.copa_del_rey", "ita.coppa_italia", "ger.dfb_pokal", "fra.coupe_de_france",
            "usa.1", "conmebol.sudamericana"]
MAX_CALLS, MIN_LEFT = 14, 25          # 14 consultas/día solo de 1X2 (1 crédito cada una) ≈ 420 créditos/mes (plan gratis: 500)


def _devig(prices: list) -> list | None:
    try:
        inv = [1 / float(x) for x in prices]
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    s = sum(inv)
    return [v / s for v in inv] if s > 0 and all(v > 0 for v in inv) else None


def parse_event(ev: dict) -> dict | None:
    """Un evento de la API -> {home, away, t, mkt_H, mkt_D, mkt_A, mkt_over, n_books} (mediana entre casas)."""
    home, away = ev.get("home_team"), ev.get("away_team")
    if not home or not away:
        return None
    x3, ov = [], []
    for bk in ev.get("bookmakers", []):
        for m in bk.get("markets", []):
            o = {x.get("name"): x for x in m.get("outcomes", [])}
            if m.get("key") == "h2h" and {home, away, "Draw"} <= set(o):
                p = _devig([o[home]["price"], o["Draw"]["price"], o[away]["price"]])
                if p:
                    x3.append(p)
            elif m.get("key") == "totals":
                ou = [x for x in m.get("outcomes", []) if float(x.get("point", 0) or 0) == 2.5]
                d = {x.get("name"): x.get("price") for x in ou}
                p = _devig([d.get("Over"), d.get("Under")]) if {"Over", "Under"} <= set(d) else None
                if p:
                    ov.append(p[0])
    if not x3:
        return None
    m = np.median(np.array(x3), axis=0); m = m / m.sum()
    return {"home": home, "away": away, "t": ev.get("commence_time"), "mkt_H": float(m[0]), "mkt_D": float(m[1]),
            "mkt_A": float(m[2]), "mkt_over": float(np.median(ov)) if ov else np.nan, "n_books": len(x3)}


def _match(evs, home, away, kick):
    """Mismo partido: los dos nombres coinciden; si no, uno coincide, la hora es casi la misma (±3 h) y es el único."""
    from kalshi_soccer.kalshi import _same
    near = [e for e in evs if abs(pd.Timestamp(e["t"]) - kick) <= pd.Timedelta(hours=12)]
    both = [e for e in near if _same(e["home"], home) and _same(e["away"], away)]
    if len(both) == 1:
        return both[0]
    one = [e for e in near if (_same(e["home"], home) or _same(e["away"], away)) and abs(pd.Timestamp(e["t"]) - kick) <= pd.Timedelta(hours=3)]
    return one[0] if len(one) == 1 else None


def fill(d: pd.DataFrame, key: str | None = None, session=None, days: int = 3) -> pd.DataFrame:
    """Completa mkt_* de los partidos sin cuotas (las cuotas de ESPN, si existen, no se tocan)."""
    key = key if key is not None else (os.environ.get("ODDS_API_KEY") or "").strip()
    if not key or d.empty:
        return d
    s = session or requests.Session()
    d = d.copy()
    now = pd.Timestamp.now(tz="UTC")
    kick = pd.to_datetime(d["kickoff_utc"], utc=True)
    need = d[d["mkt_H"].isna() & d["code"].isin(SPORT) & (kick <= now + pd.Timedelta(days=days))]
    if need.empty:
        return d
    try:
        active = {x["key"] for x in s.get(f"{BASE}/sports", params={"apiKey": key}, timeout=30).json() if x.get("active")}  # gratis
    except Exception as ex:  # noqa: BLE001
        print("AVISO The Odds API:", type(ex).__name__); return d
    # primero las competiciones con MÁS partidos sin cuotas (más partidos arreglados por crédito)
    codes = sorted(need["code"].unique(), key=lambda c: -int((need["code"] == c).sum()))
    inactive = [c for c in codes if SPORT[c] not in active]
    if inactive:
        print("The Odds API: sin mercado ahora para", inactive)
    calls = filled = 0
    unmatched = 0
    for code in codes:
        if calls >= MAX_CALLS or SPORT[code] not in active:
            continue
        r = s.get(f"{BASE}/sports/{SPORT[code]}/odds", params={"apiKey": key, "regions": "eu", "markets": "h2h",
                                                               "oddsFormat": "decimal"}, timeout=30)
        calls += 1
        if r.status_code != 200:
            print(f"AVISO The Odds API {code}: HTTP {r.status_code}"); continue
        evs = [e for e in (parse_event(x) for x in r.json()) if e]
        for i in need[need["code"] == code].index:
            hit = _match(evs, d.at[i, "home"], d.at[i, "away"], kick[i])
            if hit:
                for c in ("mkt_H", "mkt_D", "mkt_A", "n_books"):
                    d.at[i, c] = hit[c]
                if pd.notna(hit.get("mkt_over")):
                    d.at[i, "mkt_over"] = hit["mkt_over"]
                filled += 1
            else:
                unmatched += 1
        left = r.headers.get("x-requests-remaining")
        if left is not None and float(left) < MIN_LEFT:
            print(f"The Odds API: quedan {left} créditos; se detiene."); break
    print(f"The Odds API: {calls} consultas, {filled} partidos con cuotas nuevas, {unmatched} sin emparejar")
    return d
