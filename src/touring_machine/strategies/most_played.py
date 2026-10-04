"""Strategy that generates a tracklist based on song frequency across recent concerts."""

from collections import defaultdict

from touring_machine.models import ConcertSetlist, RankedSong
from touring_machine.strategies.base import PlaylistStrategy


class MostPlayedStrategy(PlaylistStrategy):
    """Generates a playlist from the most frequently played songs across recent concerts."""

    def __init__(self, ignore_tapes: bool = True) -> None:
        """Initialize strategy.

        Args:
            ignore_tapes: If True, exclude songs recorded as pre-recorded tape intros/outros.
        """
        self.ignore_tapes = ignore_tapes

    @property
    def name(self) -> str:
        return "most-played"

    @property
    def description(self) -> str:
        return "Most frequently performed songs across recent concerts"

    def generate_ranked_songs(
        self,
        setlists: list[ConcertSetlist],
    ) -> list[RankedSong]:
        """Calculate play counts, percentages, and average positions for all songs."""
        if not setlists:
            return []

        counts: dict[str, int] = defaultdict(int)
        positions: dict[str, list[int]] = defaultdict(list)
        total_setlists = len(setlists)

        for setlist in setlists:
            seen_in_setlist: set[str] = set()
            position = 1
            for song in setlist.songs:
                if self.ignore_tapes and song.is_tape:
                    continue

                song_name = song.name.strip()
                if not song_name:
                    continue

                # Record position
                positions[song_name].append(position)
                position += 1

                # Count each song once per show to calculate accurate percentages
                if song_name not in seen_in_setlist:
                    counts[song_name] += 1
                    seen_in_setlist.add(song_name)

        ranked: list[RankedSong] = []
        for song_name, count in counts.items():
            pos_list = positions[song_name]
            avg_pos = sum(pos_list) / len(pos_list) if pos_list else 0.0
            pct = round((count / total_setlists) * 100.0, 1)
            ranked.append(
                RankedSong(
                    name=song_name,
                    play_count=count,
                    appearances_total=total_setlists,
                    percentage=pct,
                    average_position=round(avg_pos, 1),
                )
            )

        # Sort primarily by play count descending, secondarily by avg position ascending
        ranked.sort(key=lambda s: (-s.play_count, s.average_position, s.name))
        return ranked

    def generate_tracklist(
        self,
        setlists: list[ConcertSetlist],
        limit: int | None = None,
    ) -> list[str]:
        """Generate ordered list of song titles based on performance frequency."""
        ranked = self.generate_ranked_songs(setlists)
        tracklist = [s.name for s in ranked]
        if limit is not None and limit > 0:
            return tracklist[:limit]
        return tracklist
