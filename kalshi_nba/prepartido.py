"""¿Qué deportes necesitan una foto nueva de precios porque tienen partidos a punto de empezar?

  python -m kalshi_nba.prepartido       # imprime p. ej. "nba intl" (vacío si no hace falta nada)

Regla: hay al menos un partido que empieza entre 10 y 150 minutos desde ahora, y la última foto de precios de ese
deporte tiene más de 25 minutos. Así el pick usa el precio más cercano al inicio (ya incluye alineaciones y bajas de
última hora), que en las pruebas fue claramente el más fiable (KALSHI_BENCHMARK.md).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

P = Path("predictions")
SOURCES = {  # deporte -> (registro, columna de inicio, fotos de precios)
    "nba": ("nba_registry.csv", "kickoff_utc", "nba_kalshi_snapshots.csv"),
    "nfl": ("nfl_registry.csv", "kickoff_utc", "nfl_kalshi_snapshots.csv"),
    "intl": ("intl_registry.csv", "kickoff_utc", "intl_kalshi_snapshots.csv"),
    "liga": ("registry.csv", "kickoff_utc", "registry.csv"),
}
LO, HI, STALE = 10, 150, 25          # minutos


def _last(path: Path, col: str):
    if not path.exists():
        return None
    try:
        s = pd.read_csv(path, usecols=[col])[col]
        return pd.to_datetime(s, utc=True, errors="coerce").max()
    except (ValueError, KeyError):
        return None


def due(now=None, folder: Path = P) -> list:
    now = pd.Timestamp(now or pd.Timestamp.now(tz="UTC"))
    out = []
    for sport, (reg, kcol, snap) in SOURCES.items():
        p = folder / reg
        if not p.exists():
            continue
        k = pd.to_datetime(pd.read_csv(p, usecols=[kcol])[kcol], utc=True, errors="coerce")
        soon = ((k >= now + pd.Timedelta(minutes=LO)) & (k <= now + pd.Timedelta(minutes=HI))).any()
        if not soon:
            continue
        last = _last(folder / snap, "snapshot_utc" if snap != reg else "created_utc")
        if last is None or now - last > pd.Timedelta(minutes=STALE):
            out.append(sport)
    return out


if __name__ == "__main__":
    print(" ".join(due()))
