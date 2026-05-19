import pytest
import requests
from unittest.mock import MagicMock, patch
from src.exporters.mal import MALExporter, get_auth_url
from src.crunchyroll.models import SeriesSummary


def make_exporter() -> MALExporter:
    return object.__new__(MALExporter)


def make_summary(max_ep: int = 12) -> SeriesSummary:
    s = SeriesSummary(series_id="S1", series_title="Test")
    s.max_episode = max_ep
    s.first_watched_at = "2026-01-01T00:00:00Z"
    s.last_watched_at = "2026-03-01T00:00:00Z"
    return s


# --- _determine_status ---

def test_determine_status_completed():
    assert make_exporter()._determine_status(make_summary(12), 12) == "completed"


def test_determine_status_completed_over():
    assert make_exporter()._determine_status(make_summary(13), 12) == "completed"


def test_determine_status_watching():
    assert make_exporter()._determine_status(make_summary(8), 12) == "watching"


def test_determine_status_zero_total_is_watching():
    assert make_exporter()._determine_status(make_summary(8), 0) == "watching"


# --- _mal_date ---

def test_mal_date_valid():
    assert MALExporter._mal_date("2026-03-15T10:00:00Z") == "2026-03-15"


def test_mal_date_none_returns_none():
    assert MALExporter._mal_date(None) is None


def test_mal_date_malformed_returns_none():
    assert MALExporter._mal_date("not-a-date") is None


def test_mal_date_with_offset():
    assert MALExporter._mal_date("2026-03-15T10:00:00+02:00") == "2026-03-15"


# --- get_auth_url ---

def test_get_auth_url_returns_tuple():
    url, verifier = get_auth_url("my_client")
    assert isinstance(url, str)
    assert isinstance(verifier, str)


def test_get_auth_url_contains_client_id():
    url, _ = get_auth_url("my_client")
    assert "my_client" in url


def test_get_auth_url_verifier_length():
    _, verifier = get_auth_url("cid")
    assert len(verifier) == 128


def test_get_auth_url_pkce_plain_method():
    url, _ = get_auth_url("cid")
    assert "code_challenge_method=plain" in url


def test_get_auth_url_challenge_equals_verifier():
    url, verifier = get_auth_url("cid")
    assert verifier in url


# --- export: HTTPError during search does not stop execution ---

def test_export_http_error_on_search_goes_to_failed():
    exp = make_exporter()
    exp.session = MagicMock()

    bad_response = MagicMock()
    bad_response.ok = False
    bad_response.status_code = 401
    bad_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401")
    exp.session.get.return_value = bad_response

    s1 = make_summary(12)
    s1.series_title = "Failing Series"
    result = exp.export([s1])

    assert result.updated == []
    assert len(result.failed) == 1
    assert result.failed[0][0] == "Failing Series"


def test_export_http_error_mid_list_continues():
    exp = make_exporter()
    exp.session = MagicMock()

    bad_response = MagicMock()
    bad_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401")

    good_response = MagicMock()
    good_response.raise_for_status.return_value = None
    good_response.json.return_value = {"data": [{"node": {"id": 1, "title": "Good", "num_episodes": 12, "media_type": "tv"}}]}

    patch_response = MagicMock()
    patch_response.raise_for_status.return_value = None

    exp.session.get.side_effect = [bad_response, good_response]
    exp.session.patch.return_value = patch_response

    s_bad = make_summary(12)
    s_bad.series_title = "Bad Series"
    s_good = make_summary(12)
    s_good.series_title = "Good Series"

    result = exp.export([s_bad, s_good])

    assert result.updated == ["Good Series"]
    assert len(result.failed) == 1
    assert result.failed[0][0] == "Bad Series"
