import pytest
from src.crunchyroll.history import CRHistory
from src.crunchyroll.models import CRToken


def make_history() -> CRHistory:
    token = CRToken(access_token="x", refresh_token="y", account_id="123")
    h = object.__new__(CRHistory)
    h.token = token
    return h


def make_item(**overrides) -> dict:
    item = {
        "date_played": "2026-01-01T00:00:00Z",
        "fully_watched": True,
        "panel": {
            "id": "EP1",
            "title": "Episode 1",
            "episode_metadata": {
                "series_id": "S1",
                "series_title": "My Anime",
                "season_number": 1,
                "episode_number": 5,
            },
        },
    }
    item.update(overrides)
    return item


def test_parse_normal_episode():
    ep = make_history()._parse_item(make_item())
    assert ep is not None
    assert ep.series_id == "S1"
    assert ep.series_title == "My Anime"
    assert ep.season_number == 1
    assert ep.episode_number == 5.0
    assert ep.fully_watched is True
    assert ep.watched_at == "2026-01-01T00:00:00Z"


def test_parse_empty_panel_returns_none():
    ep = make_history()._parse_item({"panel": {}})
    assert ep is None


def test_parse_missing_panel_returns_none():
    ep = make_history()._parse_item({})
    assert ep is None


def test_parse_movie_empty_episode_metadata():
    item = make_item()
    item["panel"]["episode_metadata"] = {}
    ep = make_history()._parse_item(item)
    assert ep is not None
    assert ep.episode_number == 0.0


def test_parse_malformed_episode_number():
    item = make_item()
    item["panel"]["episode_metadata"]["episode_number"] = "abc"
    ep = make_history()._parse_item(item)
    assert ep is not None
    assert ep.episode_number == 0.0


def test_parse_null_episode_number():
    item = make_item()
    item["panel"]["episode_metadata"]["episode_number"] = None
    ep = make_history()._parse_item(item)
    assert ep.episode_number == 0.0


def test_parse_null_season_number_defaults_to_1():
    item = make_item()
    item["panel"]["episode_metadata"]["season_number"] = None
    ep = make_history()._parse_item(item)
    assert ep.season_number == 1


def test_parse_fully_watched_false():
    ep = make_history()._parse_item(make_item(fully_watched=False))
    assert ep.fully_watched is False


def test_parse_episode_id_from_panel():
    ep = make_history()._parse_item(make_item())
    assert ep.episode_id == "EP1"
