"""Abstract base class and interface for playlist generation strategies."""

from abc import ABC, abstractmethod

from touring_machine.models import ConcertSetlist, RankedSong


class PlaylistStrategy(ABC):
    """Base interface for strategies that generate a tracklist from concert setlists."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Machine-friendly name of the strategy (e.g. 'most-played', 'latest')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this strategy generates."""
        ...

    @abstractmethod
    def generate_tracklist(
        self,
        setlists: list[ConcertSetlist],
        limit: int | None = None,
    ) -> list[str]:
        """Generate an ordered list of song names from concert setlists.

        Args:
            setlists: List of analyzed ConcertSetlists.
            limit: Optional maximum number of songs to include.

        Returns:
            List of song title strings in recommended playlist playback order.
        """
        ...

    def generate_ranked_songs(
        self,
        setlists: list[ConcertSetlist],
    ) -> list[RankedSong]:
        """Return song statistics across setlists if supported by the strategy.

        Defaults to calculating basic appearance counts.
        """
        return []
