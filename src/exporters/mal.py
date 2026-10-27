import secrets
import requests
from urllib.parse import urlencode
from src.crunchyroll.models import SeriesSummary
from .base import BaseExporter, ExportResult

MAL_API_BASE = "https://api.myanimelist.net/v2"
MAL_AUTH_URL = "https://myanimelist.net/v1/oauth2/authorize"
MAL_TOKEN_URL = "https://myanimelist.net/v1/oauth2/token"


def get_auth_url(client_id: str) -> tuple[str, str]:
    """Returns (auth_url, code_verifier). MAL uses PKCE plain — challenge == verifier."""
    verifier = secrets.token_urlsafe(96)[:128]
    params = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "code_challenge": verifier,
        "code_challenge_method": "plain",
    })
    return f"{MAL_AUTH_URL}?{params}", verifier


def exchange_code(client_id: str, code: str, verifier: str, client_secret: str = "") -> str:
    """Exchange auth code for access token. Returns the access_token."""
    data = {
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": verifier,
    }
    if client_secret:
        data["client_secret"] = client_secret
    resp = requests.post(MAL_TOKEN_URL, data=data, timeout=15)
    if not resp.ok:
        raise RuntimeError(f"Token exchange failed {resp.status_code}: {resp.text}")
    return resp.json()["access_token"]


class MALExporter(BaseExporter):
    def __init__(self, access_token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    _SERIES_TYPES = {"tv", "ona", "ova"}
    # Stricter set for walking the sequel chain: OVAs linked as sequels are
    # usually side stories, not the next season. Mirrors AniList's _SEASON_FORMATS.
    _SEASON_TYPES = {"tv", "ona"}

    def search_anime(self, series_id: str, title: str) -> dict | None:
        resp = self.session.get(
            f"{MAL_API_BASE}/anime",
            params={"q": title, "limit": 5, "fields": "id,title,num_episodes,media_type"},
            timeout=10,
        )
        if not resp.ok:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise RuntimeError(f"MAL search failed {resp.status_code}: {detail}")
        items = [item["node"] for item in resp.json().get("data", [])]
        if not items:
            return None
        for item in items:
            if item.get("media_type", "").lower() in self._SERIES_TYPES:
                return item
        return items[0]

    def _get_anime(self, anime_id: int, fields: str) -> dict:
        resp = self.session.get(
            f"{MAL_API_BASE}/anime/{anime_id}",
            params={"fields": fields},
            timeout=10,
        )
        if not resp.ok:
            raise RuntimeError(f"MAL lookup of {anime_id} failed {resp.status_code}: {resp.text}")
        return resp.json()

    def _next_season(self, anime_id: int) -> dict | None:
        """Return the TV/ONA sequel of anime_id, or None if the chain ends."""
        related = self._get_anime(anime_id, "related_anime").get("related_anime") or []
        sequel_ids = [
            r["node"]["id"] for r in related
            if r.get("relation_type") == "sequel" and r.get("node", {}).get("id")
        ]
        # related_anime nodes carry no media_type, so fetch each candidate:
        # movies and specials are frequently linked as sequels too.
        for sid in sequel_ids:
            details = self._get_anime(sid, "id,title,num_episodes,media_type")
            if details.get("media_type", "").lower() in self._SEASON_TYPES:
                return details
        return None

    def resolve_season(self, anime: dict, season_number: int) -> dict:
        """
        Walk the sequel chain from the season-1 match to the requested season.
        Raises instead of guessing when the chain is shorter than expected.
        """
        current = anime
        for hop in range(1, season_number):
            nxt = self._next_season(current["id"])
            if not nxt:
                raise RuntimeError(
                    f"Season {season_number} not found on MyAnimeList: sequel chain from "
                    f"anime {anime['id']} ends at season {hop}"
                )
            current = nxt
        return current

    def _determine_status(self, series: SeriesSummary, total_episodes: int) -> str:
        if total_episodes and series.max_episode >= total_episodes:
            return "completed"
        return "watching"

    @staticmethod
    def _mal_date(iso: str | None) -> str | None:
        if not iso:
            return None
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None

    def _update_list(self, anime_id: int, status: str, series: SeriesSummary) -> None:
        data: dict = {
            "status": status,
            "num_watched_episodes": series.max_episode,
        }
        start = self._mal_date(series.first_watched_at)
        if start:
            data["start_date"] = start
        if status == "completed":
            finish = self._mal_date(series.last_watched_at)
            if finish:
                data["finish_date"] = finish
        self.session.patch(
            f"{MAL_API_BASE}/anime/{anime_id}/my_list_status",
            data=data,
            timeout=10,
        ).raise_for_status()

    def export(self, series: list[SeriesSummary]) -> ExportResult:
        result = ExportResult()
        base_cache: dict[tuple[str, str], dict | None] = {}
        for s in series:
            label = s.display_title
            try:
                # All seasons of a series share the same season-1 lookup.
                key = (s.series_id, s.series_title)
                if key not in base_cache:
                    base_cache[key] = self.search_anime(s.series_id, s.series_title)
                anime = base_cache[key]
                if not anime:
                    result.failed.append((label, "Not found on MyAnimeList"))
                    continue
                if s.season_number > 1:
                    anime = self.resolve_season(anime, s.season_number)
                status = self._determine_status(s, anime.get("num_episodes", 0))
                self._update_list(anime["id"], status, s)
                result.updated.append(label)
            except Exception as e:
                result.failed.append((label, str(e)))
        return result
