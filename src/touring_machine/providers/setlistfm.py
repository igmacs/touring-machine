"""Setlist.fm concert data provider implementation."""

import logging
import time
from typing import Any

import httpx

from touring_machine.config import get_api_key
from touring_machine.exceptions import (
    ArtistNotFoundError,
    MissingApiKeyError,
    ProviderError,
    TourNotFoundError,
)
from touring_machine.models import Artist, ConcertSetlist, SongPerformance
from touring_machine.providers.base import ConcertDataProvider

logger = logging.getLogger(__name__)

SETLISTFM_BASE_URL = "https://api.setlist.fm/rest/1.0"

# Setlist.fm's origin allows 2 requests/second with no burst allowance, so
# requests must be spaced out; stay safely below the limit.
MIN_REQUEST_INTERVAL = 0.6


def _format_event_date(date_str: str) -> str:
    """Format Setlist.fm 'dd-MM-yyyy' date to ISO 'YYYY-MM-DD'."""
    try:
        parts = date_str.strip().split("-")
        if len(parts) == 3 and len(parts[0]) == 2 and len(parts[2]) == 4:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except Exception:
        pass
    return date_str


class SetlistFmProvider(ConcertDataProvider):
    """Provider for concert setlists using the Setlist.fm REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        request_interval: float = MIN_REQUEST_INTERVAL,
    ) -> None:
        """Initialize Setlist.fm provider.

        Args:
            api_key: Setlist.fm API key (defaults to config or SETLISTFM_API_KEY env var).
            client: Optional pre-configured httpx.Client (useful for testing/mocking).
            request_interval: Minimum seconds between API requests (rate limiting).
        """
        self._api_key = api_key
        self._client = client
        self._owns_client = client is None
        self._request_interval = request_interval
        self._last_request_at = 0.0

    @property
    def name(self) -> str:
        return "setlistfm"

    @property
    def api_key(self) -> str:
        """Retrieve the API key, raising MissingApiKeyError if not available."""
        if not self._api_key:
            self._api_key = get_api_key("setlistfm")
        if not self._api_key:
            msg = (
                "Setlist.fm API key is missing.\n"
                "Please obtain a free key at https://www.setlist.fm/settings/api and either:\n"
                "  1. Set the SETLISTFM_API_KEY environment variable, or\n"
                "  2. Run 'touring-machine set-key setlistfm <API_KEY>'."
            )
            raise MissingApiKeyError(msg)
        return self._api_key

    def _get_client(self) -> httpx.Client:
        """Return the shared HTTP client, creating and caching it on first use."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=SETLISTFM_BASE_URL,
                headers={
                    "Accept": "application/json",
                    "x-api-key": self.api_key,
                    "User-Agent": "TouringMachine/0.1.0",
                },
                timeout=15.0,
            )
            self._owns_client = True
        return self._client

    def close(self) -> None:
        """Close the underlying HTTP client if this provider created it."""
        if self._client is not None and self._owns_client:
            self._client.close()
        self._client = None

    def _throttle(self) -> None:
        """Sleep if needed so requests stay at least request_interval seconds apart."""
        wait = self._last_request_at + self._request_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def _request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Perform an HTTP GET request to Setlist.fm.

        Returns None if a 404 is encountered (Setlist.fm returns 404 for empty search results).
        """
        client = self._get_client()
        headers = {
            "Accept": "application/json",
            "x-api-key": self.api_key,
            "User-Agent": "TouringMachine/0.1.0",
        }
        url = (
            f"{SETLISTFM_BASE_URL}{endpoint}"
            if endpoint.startswith("/")
            else f"{SETLISTFM_BASE_URL}/{endpoint}"
        )
        self._throttle()
        try:
            response = client.get(url, params=params, headers=headers)
        except Exception as exc:
            msg = f"Failed to connect to Setlist.fm: {exc}"
            raise ProviderError(msg) from exc

        if response.status_code == 404:
            return None
        if response.status_code in (401, 403):
            msg = "Unauthorized: Invalid Setlist.fm API key."
            raise MissingApiKeyError(msg)
        if response.status_code != 200:
            msg = f"Setlist.fm API returned HTTP {response.status_code}: {response.text}"
            raise ProviderError(msg)

        try:
            return response.json()
        except Exception as exc:
            msg = f"Invalid JSON response from Setlist.fm: {exc}"
            raise ProviderError(msg) from exc

    def search_artist(self, query: str) -> list[Artist]:
        """Search for an artist by name on Setlist.fm."""
        cleaned = query.strip()
        if not cleaned:
            return []

        data = self._request(
            "/search/artists", params={"artistName": cleaned, "p": 1, "sort": "sortName"}
        )
        if not data:
            return []

        raw_artists = data.get("artist", [])
        if isinstance(raw_artists, dict):
            raw_artists = [raw_artists]

        results: list[Artist] = []
        for a in raw_artists:
            mbid = a.get("mbid")
            name = a.get("name")
            if name:
                results.append(
                    Artist(
                        name=name,
                        mbid=mbid,
                        disambiguation=a.get("disambiguation"),
                    )
                )
        return results

    def _resolve_artist(self, query: str) -> Artist:
        """Resolve a name query to the best-matching artist on Setlist.fm.

        Name-sorted search can list tribute or compilation entries before the
        real artist (e.g. 'The Best of Metallica' before 'Metallica'), so an
        exact name match is preferred when present.
        """
        artists = self.search_artist(query)
        if not artists:
            msg = f"Artist '{query}' not found on Setlist.fm."
            raise ArtistNotFoundError(msg)

        cleaned = query.strip().lower()
        for artist in artists:
            if artist.name.strip().lower() == cleaned:
                return artist
        return artists[0]

    def get_recent_setlists(
        self,
        artist: str | Artist,
        limit: int = 5,
        only_with_songs: bool = True,
        tour_name: str | None = None,
        max_pages: int = 5,
    ) -> list[ConcertSetlist]:
        """Fetch the most recent concert setlists for an artist.

        Args:
            artist: Artist name or domain object.
            limit: Maximum number of setlists to return.
            only_with_songs: Skip setlists that contain no songs.
            tour_name: Restrict results to a specific tour (Setlist.fm 'tourName' filter).
            max_pages: Safety limit on how many result pages to fetch.
        """
        if isinstance(artist, str):
            target_artist = self._resolve_artist(artist)
        else:
            target_artist = artist
            if not target_artist.mbid:
                lookup = self.search_artist(target_artist.name)
                if lookup and lookup[0].mbid:
                    target_artist = lookup[0]

        if not target_artist.mbid:
            msg = f"Could not determine MusicBrainz ID for artist '{target_artist.name}'."
            raise ArtistNotFoundError(msg)

        collected: list[ConcertSetlist] = []
        page = 1

        while len(collected) < limit and page <= max_pages:
            params: dict[str, Any] = {"artistMbid": target_artist.mbid, "p": page}
            if tour_name:
                params["tourName"] = tour_name
            data = self._request("/search/setlists", params=params)
            if not data:
                break

            raw_setlists = data.get("setlist", [])
            if isinstance(raw_setlists, dict):
                raw_setlists = [raw_setlists]

            if not raw_setlists:
                break

            for item in raw_setlists:
                setlist = self._parse_setlist(item, target_artist)
                if only_with_songs and not setlist.songs:
                    continue
                collected.append(setlist)
                if len(collected) >= limit:
                    break

            items_per_page = data.get("itemsPerPage", 20)
            total = data.get("total")
            has_no_more = total is not None and len(collected) >= total
            if len(raw_setlists) < items_per_page or has_no_more:
                break

            page += 1

        return collected[:limit]

    def get_current_tour(self, artist: str | Artist, scan_limit: int = 5) -> str | None:
        """Return the name of the artist's current (most recent) tour, if any.

        Scans the most recent setlists and returns the tour name of the
        newest show that belongs to a tour. Festival one-offs without a
        tour are skipped.
        """
        recent = self.get_recent_setlists(artist, limit=scan_limit, only_with_songs=False)
        for setlist in recent:
            if setlist.tour_name:
                return setlist.tour_name
        return None

    def get_current_tour_setlists(
        self,
        artist: str | Artist,
        limit: int = 25,
    ) -> list[ConcertSetlist]:
        """Fetch setlists belonging to the artist's current tour.

        Args:
            artist: Artist name or domain object.
            limit: Maximum number of tour setlists to return.

        Raises:
            TourNotFoundError: If the artist has no recent show assigned to a tour.
        """
        if isinstance(artist, str):
            target_artist = self._resolve_artist(artist)
        else:
            target_artist = artist

        tour_name = self.get_current_tour(target_artist)
        if not tour_name:
            msg = (
                f"No current tour found for artist '{target_artist.name}'. "
                "The artist's recent shows are not assigned to a tour on Setlist.fm."
            )
            raise TourNotFoundError(msg)

        return self.get_recent_setlists(
            target_artist, limit=limit, tour_name=tour_name, max_pages=15
        )

    def _parse_setlist(self, item: dict[str, Any], artist: Artist) -> ConcertSetlist:
        """Parse raw Setlist.fm json dict into ConcertSetlist domain object."""
        setlist_id = str(item.get("id", ""))
        raw_date = item.get("eventDate", "")
        event_date = _format_event_date(raw_date)

        venue_data = item.get("venue", {}) or {}
        venue_name = venue_data.get("name")
        city_data = venue_data.get("city", {}) or {}
        city = city_data.get("name")
        country_data = city_data.get("country", {}) or {}
        country = country_data.get("name")

        tour_data = item.get("tour", {}) or {}
        tour_name = tour_data.get("name")

        url = item.get("url")

        # Parse songs in order
        songs: list[SongPerformance] = []
        sets_container = item.get("sets", {}) or {}
        set_list = sets_container.get("set", [])
        if isinstance(set_list, dict):
            set_list = [set_list]

        for s in set_list:
            raw_songs = s.get("song", [])
            if isinstance(raw_songs, dict):
                raw_songs = [raw_songs]

            for song_dict in raw_songs:
                name = song_dict.get("name", "").strip()
                if not name:
                    continue
                is_tape = bool(song_dict.get("tape", False))
                is_cover = bool(song_dict.get("cover"))
                info = song_dict.get("info")
                songs.append(
                    SongPerformance(
                        name=name,
                        is_tape=is_tape,
                        is_cover=is_cover,
                        info=info,
                    )
                )

        return ConcertSetlist(
            id=setlist_id,
            event_date=event_date,
            artist=artist,
            venue_name=venue_name,
            city=city,
            country=country,
            tour_name=tour_name,
            songs=songs,
            url=url,
        )
