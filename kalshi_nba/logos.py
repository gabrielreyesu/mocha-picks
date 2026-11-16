"""Catálogo de escudos (clubes), banderas (selecciones) y logos (NBA/NFL y competiciones) desde ESPN.

Solo guarda URLs públicas de imágenes de ESPN (no descarga ni redistribuye las imágenes). Si falta alguna, la página
muestra las iniciales. Escudos y logos son marcas de sus dueños: uso personal; revisar licencias si la página se hace
pública/comercial.
  python -m kalshi_nba.logos        # escribe predictions/logos.json
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path("predictions/logos.json")
API = "https://site.api.espn.com/apis/site/v2/sports/{path}/{what}"
# Nombres abreviados del registro de ligas (football-data) -> nombre de ESPN
ALIASES = {"Man United": "Manchester United", "Man City": "Manchester City", "Nott'm Forest": "Nottingham Forest",
           "Newcastle": "Newcastle United", "Tottenham": "Tottenham Hotspur", "West Ham": "West Ham United",
           "Wolves": "Wolverhampton Wanderers", "Brighton": "Brighton & Hove Albion", "Leeds": "Leeds United",
           "Sheffield United": "Sheffield United", "Roma": "AS Roma", "Inter": "Internazionale", "Milan": "AC Milan",
           "Paris SG": "Paris Saint-Germain", "Ath Bilbao": "Athletic Club", "Ath Madrid": "Atlético Madrid",
           "Espanol": "Espanyol", "Sociedad": "Real Sociedad", "Betis": "Real Betis", "Celta": "Celta Vigo",
           "Vallecano": "Rayo Vallecano", "La Coruna": "Deportivo La Coruña", "Ein Frankfurt": "Eintracht Frankfurt",
           "M'gladbach": "Borussia Mönchengladbach", "FC Koln": "FC Cologne", "Leverkusen": "Bayer Leverkusen",
           "Dortmund": "Borussia Dortmund", "Rennes": "Stade Rennais", "St Etienne": "Saint-Étienne",
           "Hertha": "Hertha Berlin", "Mainz": "Mainz", "Stuttgart": "VfB Stuttgart", "Verona": "Hellas Verona"}
CLUB_CODES = ["eng.1", "esp.1", "ita.1", "ger.1", "fra.1", "por.1", "ned.1", "uefa.champions", "uefa.europa", "uefa.europa.conf"]


def _https(u):
    return "https://" + u[len("http://"):] if isinstance(u, str) and u.startswith("http://") else u   # sin contenido mixto en Pages


def _get(path, what, getter):
    try:
        return getter(API.format(path=path, what=what)) or {}
    except Exception:  # noqa: BLE001 - un fallo deja ese catálogo vacío, nunca rompe la página
        return {}


def _teams(j) -> dict:
    out = {}
    for lg in (j.get("sports") or [{}])[0].get("leagues", []):
        for t in lg.get("teams", []):
            t = t.get("team") or {}
            ls = t.get("logos") or [{}]
            dark = [l for l in ls if set(l.get("rel") or []) == {"full", "dark"}]      # versión para fondo oscuro
            logo = (dark or ls)[0].get("href")
            if logo and t.get("displayName"):
                out[t["displayName"]] = _https(logo)
    return out


def _league_logo(j) -> str | None:
    lg = (j.get("leagues") or [{}])[0]
    return _https((lg.get("logos") or [{}])[0].get("href"))


def build(getter=None) -> dict:
    if getter is None:
        from kalshi_nba.data import _json as getter
    from kalshi_intl.data import GROUPS
    national = list(GROUPS["selecciones"]["target"]) + GROUPS["selecciones"]["feed"]
    data = {"teams": {"nba": {}, "nfl": {}, "soccer": {}, "national": {}}, "comps": {}}
    for lg, path in (("nba", "basketball/nba"), ("nfl", "football/nfl")):
        data["teams"][lg] = _teams(_get(path, "teams", getter))
        data["comps"][lg] = _league_logo(_get(path, "scoreboard", getter))
    L = GROUPS.get("ligas", {})
    clubs = list(dict.fromkeys(CLUB_CODES + list(L.get("target", {})) + L.get("feed", [])))
    for code in clubs + national:
        teams = _teams(_get(f"soccer/{code}", "teams", getter))
        data["teams"]["national" if code in national else "soccer"].update(teams)
        data["comps"][code] = _league_logo(_get(f"soccer/{code}", "scoreboard", getter))
    data["comps"] = {k: v for k, v in data["comps"].items() if v}
    return data


class Logos:
    """Búsqueda tolerante: nombre exacto y, si no, coincidencia de nombres de producción (kalshi_soccer._same)."""

    def __init__(self, data: dict | None):
        self.d = data or {"teams": {}, "comps": {}}

    @classmethod
    def load(cls, path: Path = OUT) -> "Logos":
        try:
            return cls(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return cls(None)

    def team(self, sport: str, name: str) -> str | None:
        pools = {"nba": ["nba"], "nfl": ["nfl"], "intl": ["national", "soccer"]}.get(sport, ["soccer", "national"])
        name = ALIASES.get(name, name)
        for p in pools:
            t = self.d.get("teams", {}).get(p, {})
            if name in t:
                return t[name]
        from kalshi_soccer.kalshi import _same
        hits = [u for p in pools for n, u in self.d.get("teams", {}).get(p, {}).items() if _same(n, name)]
        return hits[0] if len(set(hits)) == 1 else None

    def comp(self, sport: str, code: str | None) -> str | None:
        c = self.d.get("comps", {})
        return c.get(sport) if sport in ("nba", "nfl") else c.get(code or "")


def main():
    data = build()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    n = {k: len(v) for k, v in data["teams"].items()}
    print(f"logos: equipos {n}, competiciones {len(data['comps'])}")


if __name__ == "__main__":
    main()
