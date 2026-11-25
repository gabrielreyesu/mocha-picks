from types import SimpleNamespace

import pytest
import requests

from kalshi_intl import lesiones
from kalshi_nba.resumen import _bajas_fut


@pytest.mark.parametrize(
    ("counts", "expected"),
    [((None, None), "Sin datos de bajas"), ((0, None), "0 / Sin datos"), ((1, 2), "1 / 2")],
)
def test_missing_injury_data_is_distinguished_from_a_count(monkeypatch, counts, expected):
    results = iter(counts)
    monkeypatch.setattr(lesiones, "count_out", lambda *_: next(results))
    match = SimpleNamespace(home="Local", away="Visita", kickoff_utc="2026-11-25")
    assert _bajas_fut(match, None) == expected


def test_injury_collection_continues_after_provider_timeout(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("API_FOOTBALL_KEY", "test")
    monkeypatch.setattr(lesiones, "FILE", tmp_path / "injuries.csv")
    calls = []

    def get(*args, **kwargs):
        calls.append(kwargs["params"]["date"])
        if len(calls) == 1:
            raise requests.Timeout()
        return SimpleNamespace(
            headers={"content-type": "application/json"},
            status_code=200,
            json=lambda: {"response": [{"player": {"name": "Jugador", "type": "Missing Fixture"}}]},
        )

    monkeypatch.setattr(lesiones.requests, "get", get)
    assert lesiones.record(days=2) == 1
    assert len(calls) == 2
    assert "sin datos de bajas" in capsys.readouterr().out
    assert "Jugador" in lesiones.FILE.read_text()
