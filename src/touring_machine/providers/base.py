"""Abstract base class and interface for concert setlist providers."""

from abc import ABC, abstractmethod

from touring_machine.models import Artist, ConcertSetlist


class ConcertDataProvider(ABC):
    """Interface for concert setlist providers (Setlist.fm, Bandsintown, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the concert provider (e.g. 'setlistfm')."""
        ...

    @abstractmethod
    def search_artist(self, query: str) -> list[Artist]:
        """Search for an artist by name.

        Args:
            query: Artist name or query.

        Returns:
            List of matching Artist domain objects.
        """
        ...

    @abstractmethod
    def get_recent_setlists(
        self,
        artist: str | Artist,
        limit: int = 5,
    ) -> list[ConcertSetlist]:
        """Fetch the most recent concert setlists for an artist.

        Args:
            artist: Artist name string or Artist model instance with mbid.
            limit: Maximum number of setlists to retrieve.

        Returns:
            List of ConcertSetlist domain objects in reverse chronological order.
        """
        ...
