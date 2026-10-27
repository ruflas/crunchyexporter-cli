import pytest
from src.exporters.anilist import AniListExporter, _normalize
from src.crunchyroll.models import SeriesSummary


def make_exporter() -> AniListExporter:
    return object.__new__(AniListExporter)


def make_summary(max_ep: int = 12, last_watched: str = "2026-03-15T10:00:00Z") -> SeriesSummary:
    s = SeriesSummary(series_id="S1", series_title="Test")
    s.max_episode = max_ep
    s.last_watched_at = last_watched
    return s


# --- _determine_status ---

def test_determine_status_completed_exact():
    assert make_exporter()._determine_status(make_summary(12), 12) == "COMPLETED"


def test_determine_status_completed_over():
    assert make_exporter()._determine_status(make_summary(13), 12) == "COMPLETED"


def test_determine_status_current_less():
    assert make_exporter()._determine_status(make_summary(8), 12) == "CURRENT"


def test_determine_status_no_total_is_current():
    assert make_exporter()._determine_status(make_summary(8), None) == "CURRENT"


def test_determine_status_zero_total_is_current():
    assert make_exporter()._determine_status(make_summary(8), 0) == "CURRENT"


# --- _fuzzy_date ---

def test_fuzzy_date_valid():
    result = AniListExporter._fuzzy_date("2026-03-15T10:00:00Z")
    assert result == {"year": 2026, "month": 3, "day": 15}


def test_fuzzy_date_none_returns_none():
    assert AniListExporter._fuzzy_date(None) is None


def test_fuzzy_date_malformed_returns_none():
    assert AniListExporter._fuzzy_date("not-a-date") is None


def test_fuzzy_date_with_offset():
    result = AniListExporter._fuzzy_date("2026-03-15T10:00:00+02:00")
    assert result == {"year": 2026, "month": 3, "day": 15}


# --- _normalize ---

def test_normalize_collapses_whitespace():
    assert _normalize("MY  ANIME") == "My Anime"


def test_normalize_title_case():
    assert _normalize("sword art online") == "Sword Art Online"


def test_normalize_strips_edges():
    assert _normalize("  Chainsaw Man  ") == "Chainsaw Man"


# --- multi-season: SEQUEL chain resolution ---

def _media(mid, fmt="TV", episodes=12):
    return {"id": mid, "type": "ANIME", "format": fmt, "episodes": episodes,
            "title": {"romaji": f"M{mid}"}, "status": "FINISHED"}


def _relations(*edges):
    return {"Media": {"relations": {"edges": [
        {"relationType": rel, "node": node} for rel, node in edges
    ]}}}


class FakeAniList(AniListExporter):
    """AniListExporter with _gql backed by an in-memory relation graph."""

    def __init__(self, graph, search_result):
        self.graph = graph            # media_id -> list of (relationType, node)
        self.search_result = search_result
        self.mutations = []

    def _gql(self, query, variables):
        if "SaveMediaListEntry" in query:
            self.mutations.append(variables)
            return {"SaveMediaListEntry": {}}
        if "relations" in query:
            return _relations(*self.graph.get(variables["id"], []))
        return {"Media": self.search_result}


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("src.exporters.anilist.time.sleep", lambda *_: None)


def kingdom_graph():
    # S1(1) -> S2(2) -> S3(3), with a movie also linked as SEQUEL of S1
    return {
        1: [("PREQUEL", _media(0)), ("SEQUEL", _media(90, fmt="MOVIE", episodes=1)),
            ("SEQUEL", _media(2))],
        2: [("PREQUEL", _media(1)), ("SEQUEL", _media(3, episodes=26))],
        3: [("PREQUEL", _media(2))],
    }


def test_resolve_season_1_is_noop():
    exp = FakeAniList(kingdom_graph(), _media(1))
    media, err = exp.resolve_season(_media(1), 1)
    assert err is None and media["id"] == 1


def test_resolve_season_walks_chain_skipping_movies():
    exp = FakeAniList(kingdom_graph(), _media(1))
    media, err = exp.resolve_season(_media(1), 3)
    assert err is None
    assert media["id"] == 3
    assert media["episodes"] == 26


def test_resolve_season_fails_loudly_when_chain_ends():
    exp = FakeAniList(kingdom_graph(), _media(1))
    media, err = exp.resolve_season(_media(1), 6)
    assert media is None
    assert "Season 6" in err and "ends at season 3" in err


def test_export_targets_correct_season_media_id():
    exp = FakeAniList(kingdom_graph(), _media(1))
    s1 = SeriesSummary(series_id="K", series_title="Kingdom", season_number=1, max_episode=12)
    s3 = SeriesSummary(series_id="K", series_title="Kingdom", season_number=3, max_episode=10)
    result = exp.export([s1, s3])
    assert result.failed == []
    assert result.updated == ["Kingdom", "Kingdom (Season 3)"]
    assert [(m["mediaId"], m["progress"], m["status"]) for m in exp.mutations] == [
        (1, 12, "COMPLETED"),
        (3, 10, "CURRENT"),
    ]


def test_export_missing_season_reported_as_failed():
    exp = FakeAniList(kingdom_graph(), _media(1))
    s6 = SeriesSummary(series_id="K", series_title="Kingdom", season_number=6, max_episode=10)
    result = exp.export([s6])
    assert result.updated == []
    assert result.failed[0][0] == "Kingdom (Season 6)"
    assert exp.mutations == []
