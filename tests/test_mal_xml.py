import pytest
from src.exporters.mal_xml import MALXMLExporter
from src.crunchyroll.models import SeriesSummary


def make_summary(title: str = "Test Anime", max_ep: int = 12) -> SeriesSummary:
    s = SeriesSummary(series_id="S1", series_title=title)
    s.max_episode = max_ep
    s.first_watched_at = "2026-01-01T00:00:00Z"
    s.last_watched_at = "2026-03-01T00:00:00Z"
    return s


def get_xml(tmp_path, summaries) -> str:
    out = tmp_path / "out.xml"
    MALXMLExporter(out).export(summaries)
    return out.read_text(encoding="utf-8")


# --- campos obligatorios ---

def test_contains_required_fields(tmp_path):
    xml = get_xml(tmp_path, [make_summary()])
    for field in [
        "series_title", "series_type", "series_episodes",
        "my_id", "my_watched_episodes", "my_start_date", "my_finish_date",
        "my_score", "my_status", "update_on_import",
    ]:
        assert f"<{field}>" in xml


def test_series_animedb_id_present(tmp_path):
    xml = get_xml(tmp_path, [make_summary()])
    assert "series_animedb_id" in xml


def test_update_on_import_is_1(tmp_path):
    xml = get_xml(tmp_path, [make_summary()])
    assert "<update_on_import>1</update_on_import>" in xml


def test_watched_episodes_correct(tmp_path):
    xml = get_xml(tmp_path, [make_summary(max_ep=24)])
    assert "<my_watched_episodes>24</my_watched_episodes>" in xml


def test_myinfo_present(tmp_path):
    xml = get_xml(tmp_path, [make_summary(), make_summary("Other", 6)])
    assert "<myinfo>" in xml
    assert "<user_total_anime>2</user_total_anime>" in xml


# --- títulos ---

def test_title_in_output(tmp_path):
    xml = get_xml(tmp_path, [make_summary("Chainsaw Man")])
    assert "Chainsaw Man" in xml


def test_title_special_chars_no_crash(tmp_path):
    xml = get_xml(tmp_path, [make_summary("Kaguya-sama: Love Is War?")])
    assert "Kaguya-sama" in xml


def test_multiple_series(tmp_path):
    summaries = [make_summary(f"Anime {i}", i) for i in range(1, 6)]
    xml = get_xml(tmp_path, summaries)
    assert xml.count("<anime>") == 5


# --- status ---

def test_status_completed_when_max_episode_gt_zero(tmp_path):
    xml = get_xml(tmp_path, [make_summary(max_ep=12)])
    assert "<my_status>Completed</my_status>" in xml


def test_status_plan_to_watch_when_zero_episodes(tmp_path):
    xml = get_xml(tmp_path, [make_summary(max_ep=0)])
    assert "<my_status>Plan to Watch</my_status>" in xml


# --- resultado ---

def test_export_result_contains_all_titles(tmp_path):
    out = tmp_path / "out.xml"
    summaries = [make_summary(f"Anime {i}") for i in range(3)]
    result = MALXMLExporter(out).export(summaries)
    assert len(result.updated) == 3
    assert all(f"Anime {i}" in result.updated for i in range(3))
