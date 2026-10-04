"""Abstract base class and interface for music streaming providers."""

from abc import ABC, abstractmethod

from touring_machine.models import Playlist, Track


class StreamingService(ABC):
    """Interface for music streaming platform providers (Tidal, Spotify, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the streaming service (e.g. 'tidal', 'spotify')."""
        ...

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check whether the service currently has valid, usable credentials."""
        ...

    @abstractmethod
    def authenticate(self, interactive: bool = True) -> bool:
        """Perform authentication (via cached credentials or interactive flow).

        Args:
            interactive: If True, prompt user interactively if no valid cached session exists.

        Returns:
            True if authentication succeeded, False otherwise.
        """
        ...

    @abstractmethod
    def create_playlist(self, name: str, description: str = "") -> Playlist:
        """Create a new playlist in the user's account.

        Args:
            name: Playlist name.
            description: Optional playlist description.

        Returns:
            The created Playlist domain object.

        Raises:
            AuthenticationError: If the user is not authenticated.
            PlaylistCreationError: If creation failed on the remote provider.
        """
        ...

    @abstractmethod
    def add_tracks(self, playlist_id: str, tracks: list[Track]) -> None:
        """Add tracks to an existing playlist.

        Args:
            playlist_id: Service-specific playlist identifier.
            tracks: List of Track objects to add.
        """
        ...

    @abstractmethod
    def search_track(self, query: str, artist: str | None = None) -> list[Track]:
        """Search the streaming service for tracks matching title/artist.

        Args:
            query: Track title or general query.
            artist: Optional artist name filter.

        Returns:
            List of matching Track objects.
        """
        ...

    @abstractmethod
    def get_playlist(self, playlist_id: str) -> Playlist | None:
        """Retrieve playlist details and tracklist.

        Args:
            playlist_id: Service-specific playlist identifier.

        Returns:
            Playlist object or None if not found.
        """
        ...
