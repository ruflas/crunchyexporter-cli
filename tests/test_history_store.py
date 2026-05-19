import pytest
from src.crunchyroll.models import Episode
from src.storage.history_store import HistoryStore


def make_ep(**kwargs) -> Episode:
    defaults = dict(
        series_id="S1", series_title="Test Anime", season_number=1,
        episode_number=1.0, episode_title="Ep", episode_id="E1",
        watched_at="2026-01-01T00:00:00Z", fully_watched=True,
    )
    defaults.update(kwargs)
    return Episode(**defaults)


def make_store(tmp_path, episodes=None) -> HistoryStore:
    store = HistoryStore(tmp_path / "history.json")
    if episodes:
        store.replace(episodes)
    return store


def test_series_summaries_groups_by_series_id(tmp_path):
    eps = [
        make_ep(series_id="A", episode_id="E1", episode_number=1.0),
        make_ep(series_id="A", episode_id="E2", episode_number=2.0),
        make_ep(series_id="B", episode_id="E3", episode_number=1.0),
    ]
    summaries = make_store(tmp_path, eps).series_summaries()
    assert {s.series_id for s in summaries} == {"A", "B"}


def test_series_summaries_max_episode(tmp_path):
    eps = [
        make_ep(episode_id="E1", episode_number=3.0),
        make_ep(episode_id="E2", episode_number=7.0),
        make_ep(episode_id="E3", episode_number=5.0),
    ]
    s = make_store(tmp_path, eps).series_summaries()[0]
    assert s.max_episode == 7


def test_series_summaries_movie_episode_zero(tmp_path):
    eps = [make_ep(episode_id="E1", episode_number=0.0)]
    s = make_store(tmp_path, eps).series_summaries()[0]
    assert s.max_episode == 1


def test_series_summaries_dates(tmp_path):
    eps = [
        make_ep(episode_id="E1", episode_number=1.0, watched_at="2026-01-01T00:00:00Z"),
        make_ep(episode_id="E2", episode_number=2.0, watched_at="2026-06-01T00:00:00Z"),
        make_ep(episode_id="E3", episode_number=3.0, watched_at="2026-03-15T00:00:00Z"),
    ]
    s = make_store(tmp_path, eps).series_summaries()[0]
    assert s.first_watched_at == "2026-01-01T00:00:00Z"
    assert s.last_watched_at == "2026-06-01T00:00:00Z"


def test_update_no_duplicates(tmp_path):
    store = make_store(tmp_path)
    ep = make_ep(episode_id="E1")
    store.update([ep])
    added = store.update([ep])
    assert added == 0
    assert len(store) == 1


def test_update_returns_new_count(tmp_path):
    store = make_store(tmp_path)
    ep1 = make_ep(episode_id="E1", episode_number=1.0)
    ep2 = make_ep(episode_id="E2", episode_number=2.0)
    store.update([ep1])
    added = store.update([ep1, ep2])
    assert added == 1


def test_update_incremental_keeps_old(tmp_path):
    store = make_store(tmp_path)
    store.update([make_ep(episode_id="E1")])
    store.update([make_ep(episode_id="E2", episode_number=2.0)])
    assert len(store) == 2


def test_replace_overwrites(tmp_path):
    store = make_store(tmp_path)
    store.update([make_ep(episode_id="E1")])
    store.replace([make_ep(episode_id="E2", episode_number=2.0)])
    assert len(store) == 1
    assert store.all_episodes()[0].episode_id == "E2"


def test_replace_updates_last_sync(tmp_path):
    store = make_store(tmp_path)
    assert store.last_sync is None
    store.replace([make_ep(episode_id="E1")])
    assert store.last_sync is not None


def test_len(tmp_path):
    eps = [make_ep(episode_id=f"E{i}", episode_number=float(i)) for i in range(5)]
    assert len(make_store(tmp_path, eps)) == 5


def test_empty_store_len_zero(tmp_path):
    assert len(make_store(tmp_path)) == 0
