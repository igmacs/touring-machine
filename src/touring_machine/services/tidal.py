"""Tidal streaming service implementation using tidalapi."""

import logging
from collections.abc import Callable
from pathlib import Path

import tidalapi

from touring_machine.config import get_default_tidal_session_path
from touring_machine.exceptions import (
    AuthenticationError,
    PlaylistCreationError,
    StreamingServiceError,
)
from touring_machine.models import Playlist, Track
from touring_machine.services.base import StreamingService

logger = logging.getLogger(__name__)


class TidalService(StreamingService):
    """Implementation of StreamingService for Tidal."""

    def __init__(
        self,
        session_path: Path | None = None,
        session: tidalapi.Session | None = None,
    ) -> None:
        """Initialize Tidal service.

        Args:
            session_path: Path to stored OAuth session json file.
            session: Optional pre-configured tidalapi.Session (useful for DI/tests).
        """
        self.session_path = session_path or get_default_tidal_session_path()
        self.session = session or tidalapi.Session()
        self._session_loaded = False

    @property
    def name(self) -> str:
        return "tidal"

    def is_authenticated(self) -> bool:
        """Check if currently authenticated or if a valid stored session can be loaded."""
        if self.session.check_login():
            return True

        if not self._session_loaded and self.session_path.exists():
            self._session_loaded = True
            try:
                self.session.load_session_from_file(self.session_path)
                return self.session.check_login()
            except Exception as e:
                logger.debug("Failed to load session from file %s: %s", self.session_path, e)
                return False

        return False

    def authenticate(
        self,
        interactive: bool = True,
        prompt_callback: Callable[[str], None] | None = None,
    ) -> bool:
        """Authenticate with Tidal.

        If a valid session already exists, it is reused. If not, and interactive=True,
        launches the OAuth device authorization flow.
        """
        if self.is_authenticated():
            return True

        if not interactive:
            return False

        try:
            login, future = self.session.login_oauth()
            url = f"https://{login.verification_uri_complete}"

            if prompt_callback:
                prompt_callback(url)
            else:
                print(f"To log in, visit: {url}")

            future.result()

            if not self.session.check_login():
                return False

            self._save_session()
            return True
        except Exception as exc:
            raise AuthenticationError(f"Tidal authentication failed: {exc}") from exc

    def _save_session(self) -> None:
        """Save active session to disk securely."""
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.session.save_session_to_file(self.session_path)
        try:
            self.session_path.chmod(0o600)
        except OSError:
            pass

    def create_playlist(self, name: str, description: str = "") -> Playlist:
        """Create a new playlist in Tidal.

        Args:
            name: Playlist title.
            description: Optional playlist description.

        Returns:
            The created Playlist domain object.
        """
        if not self.is_authenticated():
            raise AuthenticationError(
                "Tidal is not authenticated. Please log in first using 'touring-machine login'."
            )

        user = self.session.user
        if user is None:
            raise AuthenticationError("No authenticated Tidal user found in session.")

        try:
            user_playlist = user.create_playlist(title=name, description=description)
            url = getattr(user_playlist, "share_url", None) or getattr(
                user_playlist, "listen_url", None
            )
            return Playlist(
                id=str(user_playlist.id),
                name=user_playlist.name,
                description=user_playlist.description,
                url=url,
            )
        except Exception as exc:
            raise PlaylistCreationError(f"Failed to create playlist on Tidal: {exc}") from exc

    def add_tracks(self, playlist_id: str, tracks: list[Track]) -> None:
        """Add tracks to an existing playlist (prepared for future iterations)."""
        if not self.is_authenticated():
            raise AuthenticationError("Tidal is not authenticated.")

        track_ids = [t.id for t in tracks if t.id]
        if not track_ids:
            return

        try:
            pl = self.session.playlist(playlist_id)
            if hasattr(pl, "add"):
                pl.add(track_ids)
            else:
                msg = f"Playlist {playlist_id} does not support adding tracks."
                raise StreamingServiceError(msg)
        except Exception as exc:
            raise StreamingServiceError(f"Failed to add tracks to Tidal playlist: {exc}") from exc

    def search_track(self, query: str, artist: str | None = None) -> list[Track]:
        """Search Tidal for tracks matching query and artist."""
        if not self.is_authenticated():
            raise AuthenticationError("Tidal is not authenticated.")

        search_str = f"{artist} - {query}" if artist else query
        try:
            results = self.session.search(query=search_str, models=[tidalapi.Track], limit=10)
            tracks: list[Track] = []
            for item in getattr(results, "tracks", []):
                tracks.append(
                    Track(
                        id=str(item.id),
                        title=item.name,
                        artist=item.artist.name if item.artist else "",
                        album=item.album.name if item.album else None,
                        duration_seconds=getattr(item, "duration", None),
                        url=f"https://tidal.com/browse/track/{item.id}",
                    )
                )
            return tracks
        except Exception as exc:
            raise StreamingServiceError(f"Tidal search failed: {exc}") from exc

    def get_playlist(self, playlist_id: str) -> Playlist | None:
        """Retrieve playlist details from Tidal."""
        if not self.is_authenticated():
            raise AuthenticationError("Tidal is not authenticated.")

        try:
            pl = self.session.playlist(playlist_id)
            if not pl:
                return None
            url = getattr(pl, "share_url", None) or getattr(pl, "listen_url", None)
            return Playlist(
                id=str(pl.id),
                name=pl.name,
                description=pl.description,
                url=url,
            )
        except Exception as exc:
            raise StreamingServiceError(f"Failed to fetch Tidal playlist: {exc}") from exc
