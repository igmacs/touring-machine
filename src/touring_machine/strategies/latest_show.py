"""Strategy that replicates the exact tracklist of the artist's most recent concert."""

from touring_machine.models import ConcertSetlist, RankedSong
from touring_machine.strategies.base import PlaylistStrategy


class LatestShowStrategy(PlaylistStrategy):
    """Generates a playlist from the exact setlist of the most recent concert."""

    def __init__(self, ignore_tapes: bool = True) -> None:
        """Initialize strategy.

        Args:
            ignore_tapes: If True, exclude pre-recorded intro/outro tapes.
        """
        self.ignore_tapes = ignore_tapes

    @property
    def name(self) -> str:
        return "latest"

    @property
    def description(self) -> str:
        return "Exact setlist from the artist's most recent concert"

    def generate_ranked_songs(
        self,
        setlists: list[ConcertSetlist],
    ) -> list[RankedSong]:
        """Return songs from the latest setlist with 100% appearance."""
        if not setlists:
            return []

        latest_setlist = setlists[0]
        ranked: list[RankedSong] = []
        position = 1

        for song in latest_setlist.songs:
            if self.ignore_tapes and song.is_tape:
                continue
            name = song.name.strip()
            if not name:
                continue
            ranked.append(
                RankedSong(
                    name=name,
                    play_count=1,
                    appearances_total=1,
                    percentage=100.0,
                    average_position=float(position),
                )
            )
            position += 1

        return ranked

    def generate_tracklist(
        self,
        setlists: list[ConcertSetlist],
        limit: int | None = None,
    ) -> list[str]:
        """Return songs from the latest concert in performance order."""
        if not setlists:
            return []

        latest_setlist = setlists[0]
        tracklist: list[str] = []
        seen: set[str] = set()

        for song in latest_setlist.songs:
            if self.ignore_tapes and song.is_tape:
                continue
            name = song.name.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            tracklist.append(name)
            if limit is not None and len(tracklist) >= limit:
                break

        return tracklist
