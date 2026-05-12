import secrets
import hashlib
import base64
import webbrowser
import requests
from urllib.parse import urlencode
from src.crunchyroll.models import SeriesSummary
from .base import BaseExporter, ExportResult

MAL_API_BASE = "https://api.myanimelist.net/v2"
MAL_AUTH_URL = "https://myanimelist.net/v1/oauth2/authorize"
MAL_TOKEN_URL = "https://myanimelist.net/v1/oauth2/token"


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(96)[:128]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def get_auth_url(client_id: str) -> tuple[str, str]:
    """Returns (auth_url, code_verifier). User must open the URL and get the code."""
    verifier, challenge = _pkce_pair()
    params = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return f"{MAL_AUTH_URL}?{params}", verifier


def exchange_code(client_id: str, code: str, verifier: str) -> str:
    """Exchange auth code for access token. Returns the access_token."""
    resp = requests.post(
        MAL_TOKEN_URL,
        data={
            "client_id": client_id,
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


class MALExporter(BaseExporter):
    def __init__(self, access_token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    def search_anime(self, title: str) -> dict | None:
        resp = self.session.get(
            f"{MAL_API_BASE}/anime",
            params={"q": title, "limit": 3, "fields": "id,title,num_episodes"},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("data", [])
        return items[0]["node"] if items else None

    def _determine_status(self, series: SeriesSummary, total_episodes: int) -> str:
        if total_episodes and series.max_episode >= total_episodes:
            return "completed"
        return "watching"

    def _update_list(self, anime_id: int, status: str, num_watched: int) -> None:
        self.session.patch(
            f"{MAL_API_BASE}/anime/{anime_id}/my_list_status",
            data={"status": status, "num_watched_episodes": num_watched},
            timeout=10,
        ).raise_for_status()

    def export(self, series: list[SeriesSummary]) -> ExportResult:
        result = ExportResult()
        for s in series:
            anime = self.search_anime(s.series_title)
            if not anime:
                result.failed.append((s.series_title, "Not found on MyAnimeList"))
                continue
            try:
                status = self._determine_status(s, anime.get("num_episodes", 0))
                self._update_list(anime["id"], status, s.max_episode)
                result.updated.append(s.series_title)
            except Exception as e:
                result.failed.append((s.series_title, str(e)))
        return result
