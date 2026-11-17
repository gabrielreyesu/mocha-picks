"""Mocha Picks: página web de predicciones pensada para el teléfono: docs/index.html (un solo archivo, sin dependencias).

Lee los mismos CSV de predictions/ que PREDICCIONES.md y no usa internet. Se publica con GitHub Pages
(Settings → Pages → rama main, carpeta /docs).   Uso:  python -m kalshi_nba.pagina
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .injuries import OUT
from .logos import Logos
from .marcadores import LIGA_CODE, fetch as fetch_scores, hit
from .picks import over25, soccer_picks, us_picks, us_snapshot
from kalshi_external.final_shadow import kalshi3, source_label
from .final_pick import combine3, load_weights
from kalshi_intl.data import GROUPS
from kalshi_intl.ligas import PUBLICAR, market_only, publishable

LEAGUE_TARGETS = set(GROUPS["ligas"].get("league_targets", []))
from .resumen import TZ, _bajas_fut, _lat, _when

P = Path("predictions")
WINDOW_DAYS = 3                 # también se muestran los partidos de los últimos días (con resultado)
SPORT = {"nba": "NBA", "nfl": "NFL", "liga": "Ligas", "club": "Copas", "intl": "Selecciones"}


def _f(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return round(v, 4) if math.isfinite(v) else None


def _latest(path: Path, key="event_id") -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    d = pd.read_csv(path, dtype={key: str})
    return d.sort_values("snapshot_utc").drop_duplicates(key, keep="last").set_index(key) if "snapshot_utc" in d else d


def _final_picks() -> dict:
    f = P / "final_shadow.csv"
    if not f.exists():
        return {}
    d = pd.read_csv(f, dtype={"event_id": str}).sort_values("snapshot_utc").drop_duplicates(["sport", "event_id"], keep="last")
    return {(r.sport, r.event_id): r for r in d.itertuples()}


def _injured(lg: str) -> dict:
    """{team_id: [nombres fuera/dudosos]} de la foto más reciente."""
    path = P / f"{lg}_injuries.csv"
    if not path.exists():
        return {}
    d = pd.read_csv(path, dtype={"team_id": str})
    d = d[(d["day"] == d["day"].max()) & d["status"].str.lower().isin(OUT)]
    return {t: [f"{r.player} ({str(r.status).lower()})" for r in g.itertuples()] for t, g in d.groupby("team_id")}


def _pick(names, probs):
    ok = [(n, p) for n, p in zip(names, probs) if p is not None]
    return max(ok, key=lambda z: z[1]) if ok else (None, None)


def games_us(lg: str, now, finals) -> list:
    reg = P / f"{lg}_registry.csv"
    if not reg.exists():
        return []
    r = pd.read_csv(reg, dtype={"event_id": str, "home_id": str, "away_id": str})
    r = (r.sort_values("created_utc") if "created_utc" in r else r).drop_duplicates("event_id", keep="last")
    r["t"] = _when(r["kickoff_utc"])
    r = r[r["t"] > now - pd.Timedelta(days=WINDOW_DAYS)].sort_values("t")
    s = pd.DataFrame()
    snap = P / f"{lg}_kalshi_snapshots.csv"
    if snap.exists():
        s = pd.read_csv(snap, dtype={"event_id": str})
        s = s[(s["kind"] == "winner") & (s["side"] == "home")].sort_values("snapshot_utc").drop_duplicates("event_id", keep="last").set_index("event_id")
    pm = _latest(P / f"{lg}_polymarket_snapshots.csv")
    inj = _injured(lg)
    lines = us_snapshot(P, lg)
    lines = {e: g for e, g in lines.groupby("event_id")} if len(lines) else {}
    out = []
    for x in r.itertuples():
        kh = _f(s["mid"].get(x.event_id)) if "mid" in s else None
        bh = _f(s["p_book"].get(x.event_id)) if "p_book" in s else None
        ph = _f(pm["pm_home"].get(x.event_id)) if "pm_home" in pm else None
        model = [_f(x.p_home), _f(1 - x.p_home)]
        fin = finals.get((lg, x.event_id))
        if fin is not None and pd.notna(fin.final_H):
            final, src = [_f(fin.final_H), _f(fin.final_A)], source_label(fin.final_source)
        else:
            final, src = model, "modelo"
        pick, prob = _pick([x.home, x.away], final)
        out.append({"sport": lg, "id": x.event_id, "comp": SPORT[lg], "t": x.t.isoformat(), "home": x.home, "away": x.away, "three": False,
                    "pick": pick, "prob": prob, "src": src, "fp": final,
                    "rows": [["Modelo", model], ["Casas", [bh, None if bh is None else 1 - bh]],
                             ["Kalshi", [kh, None if kh is None else 1 - kh]], ["Polymarket", [ph, None if ph is None else 1 - ph]]],
                    "kp": {"margin": _f(x.mu_margin), "total": _f(x.mu_total)},
                    "rest": [_f(getattr(x, "rest_h", None)), _f(getattr(x, "rest_a", None))],
                    "extra": [["Diferencia esperada", f"{x.home if x.mu_margin >= 0 else x.away} por {abs(x.mu_margin):.1f} pts"],
                              ["Total esperado", f"{x.mu_total:.0f} pts"]],
                    "inj": {"home": inj.get(str(getattr(x, "home_id", "")), []), "away": inj.get(str(getattr(x, "away_id", "")), [])},
                    "picks": us_picks(lines.get(x.event_id), x.home, x.away, (pick, prob, src))})
    return out


def _tri(x, cols):
    return [_f(getattr(x, c, None)) for c in cols]


def _norm(v):
    if any(p is None for p in v):
        return v if any(p is not None for p in v) else [None, None, None]
    s = sum(v)
    return [round(p / s, 4) for p in v] if s > 0 else v


def games_ligas(now) -> list:
    reg = P / "registry.csv"
    if not reg.exists():
        return []
    r = pd.read_csv(reg)
    r = r.drop_duplicates("match_id", keep="last") if "match_id" in r else r
    r["t"] = _when(r["kickoff_utc"])
    r = r[r["t"] > now - pd.Timedelta(days=WINDOW_DAYS)].sort_values("t")
    lat = _lat()
    out = []
    for x in r.itertuples():
        model = _tri(x, ["p_H", "p_D", "p_A"])
        kal = []
        for s in "HDA":
            b, a = _f(getattr(x, f"k_bid_{s}", None)), _f(getattr(x, f"k_ask_{s}", None))
            kal.append(None if b is None or a is None else round((b + a) / 2, 4))
        k3 = kalshi3(x)
        final, src = combine3(k3, None, model, load_weights("futbol")) if all(v is not None for v in model) else (model, "modelo")
        final = [round(v, 4) for v in final] if final else model
        pick, prob = _pick([x.home, "Empate", x.away], final)
        out.append({"sport": "liga", "id": str(getattr(x, "match_id", "")), "code": LIGA_CODE.get(x.competition), "comp": x.competition,
                    "t": x.t.isoformat(), "home": x.home, "away": x.away, "three": True,
                    "pick": pick, "prob": prob, "src": src, "fp": final,
                    "rows": [["Modelo", model], ["Kalshi", kal]],
                    "kp": _kp(x, "_cal"),
                    "extra": _soccer_extra(x, cal=True) + [["Bajas local / visita", _bajas_fut(x, lat)]], "inj": None,
                    "picks": soccer_picks(x.home, x.away, final, src,
                                          {1.5: _f(getattr(x, "p_over_1_5_cal", None)), 2.5: _f(getattr(x, "p_over_2_5_cal", None))},
                                          _f(getattr(x, "p_btts_cal", None)), kalshi3=kal)})
    return out


def _kp(x, sfx, book_over=None, goals_ok=True) -> dict:
    """Probabilidades clave de la ventana del partido (goles): modelo calibrado; más de 2,5 combinado con las casas."""
    g = lambda c: _f(getattr(x, c, None))
    o25, src = over25(g(f"p_over_2_5{sfx}"), book_over)
    lh, la = g("lambda_h"), g("lambda_a")
    out = {"o25": None if o25 is None else round(o25, 4), "o25src": src, "xg": None if lh is None or la is None else round(lh + la, 2), "xgh": lh, "xga": la}
    if goals_ok:
        out.update({"o15": g(f"p_over_1_5{sfx}"), "o35": g(f"p_over_3_5{sfx}"), "btts": g(f"p_btts{sfx}")})
    else:                                                     # selecciones: los goles del modelo solos no son fiables
        out.update({"xg": None, "xgh": None, "xga": None})
        if src == "modelo":
            out["o25"] = None
    return out


def _soccer_extra(x, cal):
    g = lambda c: _f(getattr(x, c, None))
    sfx = "_cal" if cal else ""
    pc = lambda v: "—" if v is None else f"{100 * v:.0f}%"
    return [["Más de 1.5 / 2.5 / 3.5 goles", " / ".join(pc(g(f"p_over_{k}{sfx}")) for k in ("1_5", "2_5", "3_5"))],
            ["Ambos anotan", pc(g(f"p_btts{sfx}"))],
            ["Gana por 2+ local / visita", f"{pc(g(f'p_home_m1_5{sfx}'))} / {pc(g(f'p_away_m1_5{sfx}'))}"]]


def _stakes() -> dict:
    f = P / "stakes_upcoming.csv"
    if not f.exists():
        return {}
    d = pd.read_csv(f, dtype={"event_id": str})
    return {r.event_id: [t for t, flag in ((r.home, r.nostake_h), (r.away, r.nostake_a)) if flag == 1] for r in d.itertuples()}


def games_intl(now, finals) -> list:
    reg = P / "intl_registry.csv"
    if not reg.exists():
        return []
    r = pd.read_csv(reg, dtype={"event_id": str})
    r = (r.sort_values("created_utc") if "created_utc" in r else r).drop_duplicates("event_id", keep="last")
    snap = P / "intl_kalshi_snapshots.csv"
    if snap.exists():
        s = _latest(snap)
        for c in [c for c in s.columns if c.startswith(("k_mid_", "k_bid_", "k_ask_", "mkt_", "p_over_1_5", "p_over_3_5", "p_home_m1_5", "p_away_m1_5"))]:
            r[c] = r["event_id"].map(s[c]).combine_first(r[c] if c in r else pd.Series(np.nan, index=r.index))
    r["t"] = _when(r["kickoff_utc"])
    r = r[r["t"] > now - pd.Timedelta(days=WINDOW_DAYS)].sort_values("t")
    lat = _lat()
    stakes = _stakes()
    out = []
    for x in r.itertuples():
        fsport = "intl" if x.grupo == "selecciones" else "club"           # deporte en final_shadow
        valid = x.grupo != "ligas" or publishable(x.code, getattr(x, "partidos_previos_local", None), getattr(x, "partidos_previos_visita", None))
        sport = "liga" if x.grupo == "ligas" and x.code in LEAGUE_TARGETS else fsport
        model, books = _tri(x, ["p_H", "p_D", "p_A"]), _norm(_tri(x, ["mkt_H", "mkt_D", "mkt_A"]))
        fin = finals.get((fsport, x.event_id))
        if not valid:                                # competición aún sin validar: el pick sale solo del mercado
            final, src = market_only(_tri(x, ["k_mid_H", "k_mid_D", "k_mid_A"]), books if all(v is not None for v in books) else None)
            final = [round(v, 4) for v in final] if final else [None, None, None]
        elif fin is not None and pd.notna(fin.final_H):
            final, src = [_f(fin.final_H), _f(fin.final_D), _f(fin.final_A)], source_label(fin.final_source)
        else:
            final, src = model, "modelo"
        pick, prob = _pick([x.home, "Empate", x.away], final)
        extra = (_soccer_extra(x, cal=False) if valid else []) + [["Bajas local / visita", _bajas_fut(x, lat)]]
        if not valid:
            extra.append(["Aviso", "Competición nueva aún sin validar: el pick sale solo de las casas o Kalshi (NUEVAS_LIGAS.md)."])
        if sport == "intl":
            extra.append(["Aviso", "En selecciones, los mercados de goles del modelo son poco fiables."])
        out.append({"sport": sport, "espn": True, "id": x.event_id, "code": x.code, "comp": x.competicion + (" · sede neutral" if x.neutral else ""), "t": x.t.isoformat(),
                    "home": x.home, "away": x.away, "three": True, "pick": pick, "prob": prob, "src": src, "fp": final,
                    "rows": [["Modelo" if valid else "Modelo (en validación)", model], ["Casas", books], ["Kalshi", _tri(x, ["k_mid_H", "k_mid_D", "k_mid_A"])]],
                    "kp": _kp(x, "", book_over=_f(getattr(x, "mkt_over", None)), goals_ok=sport != "intl" and valid),
                    "extra": extra, "inj": None, "nostake": stakes.get(x.event_id, []),
                    "picks": soccer_picks(x.home, x.away, final, src,
                                          {1.5: _f(getattr(x, "p_over_1_5", None)), 2.5: _f(getattr(x, "p_over_2_5", None))},
                                          _f(getattr(x, "p_btts", None)), goals_ok=sport != "intl" and valid,
                                          book_over=_f(getattr(x, "mkt_over", None)),
                                          kalshi3=_tri(x, ["k_mid_H", "k_mid_D", "k_mid_A"]))})
    return out


# Catálogo de la sección «Ligas» (estilo Oddster): código -> (nombre, país, tipo). País = clave de COUNTRIES.
CATALOG = [
    ("esp.1", "LaLiga", "esp", "Primera división"), ("esp.2", "LaLiga 2", "esp", "Segunda división"), ("esp.copa_del_rey", "Copa del Rey", "esp", "Copa nacional"),
    ("eng.1", "Premier League", "eng", "Primera división"), ("eng.2", "Championship", "eng", "Segunda división"),
    ("eng.fa", "FA Cup", "eng", "Copa nacional"), ("eng.league_cup", "Copa de la Liga", "eng", "Copa nacional"),
    ("ita.1", "Serie A", "ita", "Primera división"), ("ita.2", "Serie B", "ita", "Segunda división"), ("ita.coppa_italia", "Coppa Italia", "ita", "Copa nacional"),
    ("ger.1", "Bundesliga", "ger", "Primera división"), ("ger.2", "2. Bundesliga", "ger", "Segunda división"), ("ger.dfb_pokal", "Copa de Alemania", "ger", "Copa nacional"),
    ("fra.1", "Ligue 1", "fra", "Primera división"), ("fra.2", "Ligue 2", "fra", "Segunda división"), ("fra.coupe_de_france", "Copa de Francia", "fra", "Copa nacional"),
    ("uefa.champions", "Champions League", "uefa", "Copa internacional"), ("uefa.europa", "Europa League", "uefa", "Copa internacional"),
    ("uefa.europa.conf", "Conference League", "uefa", "Copa internacional"),
    ("nba", "NBA", "usa", "Baloncesto"), ("nfl", "NFL", "usa", "Fútbol americano"), ("usa.1", "MLS", "usa", "Primera división"),
    ("por.1", "Liga Portugal", "por", "Primera división"), ("ned.1", "Eredivisie", "ned", "Primera división"),
    ("bel.1", "Liga de Bélgica", "bel", "Primera división"), ("tur.1", "Superliga", "tur", "Primera división"),
    ("sco.1", "Premiership", "sco", "Primera división"), ("mex.1", "Liga MX", "mex", "Primera división"),
    ("bra.1", "Brasileirão", "bra", "Primera división"), ("arg.1", "Liga Profesional", "arg", "Primera división"),
    ("ksa.1", "Liga Saudí", "ksa", "Primera división"),
    ("conmebol.libertadores", "Copa Libertadores", "conmebol", "Copa internacional"), ("conmebol.sudamericana", "Copa Sudamericana", "conmebol", "Copa internacional"),
    ("fifa.world", "Mundial", "world", "Selecciones"), ("fifa.worldq.uefa", "Eliminatorias UEFA", "world", "Selecciones"),
    ("fifa.worldq.conmebol", "Eliminatorias CONMEBOL", "world", "Selecciones"), ("uefa.nations", "Nations League", "world", "Selecciones"),
    ("uefa.euro", "Eurocopa", "world", "Selecciones"), ("uefa.euroq", "Clasificación Eurocopa", "world", "Selecciones"),
    ("conmebol.america", "Copa América", "world", "Selecciones"), ("fifa.friendly", "Amistosos", "world", "Selecciones"),
]
COUNTRIES = {"esp": "España", "eng": "Inglaterra", "ita": "Italia", "ger": "Alemania", "fra": "Francia", "uefa": "Europa (UEFA)",
             "usa": "Estados Unidos", "por": "Portugal", "ned": "Países Bajos", "bel": "Bélgica", "tur": "Turquía", "sco": "Escocia",
             "mex": "México", "bra": "Brasil", "arg": "Argentina", "ksa": "Arabia Saudí", "conmebol": "Sudamérica (CONMEBOL)",
             "world": "Selecciones"}
FLAG = "https://a.espncdn.com/i/teamlogos/countries/500/{}.png"


def catalog(logos) -> list:
    """Competiciones que cubre la página (las nuevas, solo si pasaron la validación)."""
    out = []
    for code, name, cc, tipo in CATALOG:
        sport = code if code in ("nba", "nfl") else None
        out.append({"code": code, "name": name, "cc": cc, "country": COUNTRIES[cc], "tipo": tipo,
                    "beta": code in GROUPS["ligas"]["target"] and code not in PUBLICAR,
                    "flag": FLAG.format(cc) if len(cc) == 3 and cc not in ("uefa",) else None,
                    "logo": logos.comp(sport, code) if sport else logos.comp("soccer", code)})
    return out


def collect(now=None, score_getter=None) -> dict:
    global P
    from . import resumen as _r
    P = _r.P                                   # misma carpeta que PREDICCIONES.md (las pruebas la cambian)
    now = now or pd.Timestamp.now(tz=TZ)
    finals = _final_picks()
    games = games_us("nba", now, finals) + games_us("nfl", now, finals) + games_ligas(now) + games_intl(now, finals)
    games.sort(key=lambda g: g["t"])
    try:
        scores = fetch_scores(games, now, getter=score_getter) if score_getter is not False else {}
    except Exception:  # noqa: BLE001 - sin marcadores, la página sigue funcionando
        scores = {}
    logos = Logos.load(P / "logos.json")
    try:
        stats = json.loads((P / "stats.json").read_text(encoding="utf-8")).get("games", {})
    except (OSError, ValueError):
        stats = {}
    for g in games:
        g["hlogo"], g["alogo"] = logos.team(g["sport"], g["home"]), logos.team(g["sport"], g["away"])
        g["clogo"] = logos.comp(g["sport"], g.get("code"))
        g["st"] = stats.get(f"{g['sport']}:{g['id']}")
    for g in games:
        sc = scores.get(f"{g['sport']}:{g.get('id')}")
        started = pd.Timestamp(g["t"]) <= now
        g["state"] = sc["state"] if sc else ("in" if started and pd.Timestamp(g["t"]) > now - pd.Timedelta(hours=3) else ("post" if started else "pre"))
        g["score"] = [sc["hs"], sc["as"]] if sc and sc["hs"] is not None and sc["state"] != "pre" else None
        g["detail"] = sc["detail"] if sc else ""
        g["ev"] = (sc or {}).get("ev") or []
        g["hit"] = hit(g, sc)
    from .analisis import _fiab, analyze
    from .estadisticas import comp_names
    fiab = _fiab()
    for g in games:
        try:
            g["an"] = analyze(g, fiab, comp_names())
        except Exception:  # noqa: BLE001 - un análisis que falla no rompe la página
            g["an"] = None
    from .estadisticas import comp_names
    for g in games:                                      # código de competición también para NBA/NFL (sección Ligas)
        g.setdefault("code", g["sport"] if g["sport"] in ("nba", "nfl") else None)
        if not g.get("code"):
            g["code"] = g["sport"]
    return {"updated": now.isoformat(), "tz": TZ, "games": games, "codes": comp_names(), "catalog": catalog(logos)}


def render(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", payload).replace("__UPDATED__", html.escape(pd.Timestamp(data["updated"]).strftime("%d %b %Y %H:%M")))


TEMPLATE = Path(__file__).with_name("pagina_template.html").read_text(encoding="utf-8")


def main(out="docs/index.html"):
    data = collect()
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render(data), encoding="utf-8")
    (p.parent / ".nojekyll").write_text("", encoding="utf-8")
    print(f"{out} generado: {len(data['games'])} partidos")


if __name__ == "__main__":
    main()
