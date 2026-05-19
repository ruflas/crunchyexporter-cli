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
