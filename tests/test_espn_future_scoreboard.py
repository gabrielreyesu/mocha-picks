from datetime import date, timedelta

import pytest

from kalshi_nba import data


def test_predict_can_skip_one_failed_future_day_without_caching_it(tmp_path, monkeypatch):
    today = date.today()
    future = today + timedelta(days=1)

    def fetch(url, params):
        if params["dates"] == f"{future:%Y%m%d}":
            raise RuntimeError("ESPN no respondió")
        return {"events": []}

    monkeypatch.setattr(data, "_json", fetch)
    with pytest.warns(UserWarning, match="Calendario ESPN incompleto"):
        assert data.fetch_day(future, tmp_path, allow_missing_future=True) == []
    assert not (tmp_path / "sb" / f"{future:%Y%m%d}.json").exists()
    assert data.fetch_day(today, tmp_path, allow_missing_future=True) == []
    assert (tmp_path / "sb" / f"{today:%Y%m%d}.json").exists()


@pytest.mark.parametrize("offset, allow_missing", [(-1, True), (0, True), (1, False)])
def test_scoreboard_failures_remain_fatal_for_required_days(tmp_path, monkeypatch, offset, allow_missing):
    def unavailable(*args):
        raise RuntimeError("ESPN no respondió")

    monkeypatch.setattr(data, "_json", unavailable)
    with pytest.raises(RuntimeError, match="ESPN no respondió"):
        data.fetch_day(date.today() + timedelta(days=offset), tmp_path, allow_missing_future=allow_missing)
