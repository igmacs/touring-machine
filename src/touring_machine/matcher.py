"""Track matching and resolution between concert setlists and streaming services."""

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial

from rapidfuzz import fuzz

from touring_machine.models import Track
from touring_machine.services.base import StreamingService

# Tidal's edge (CloudFront) starts returning 429s at roughly 30 req/s sustained
# (measured empirically; no documented limit). At ~0.4s per search, 8 workers
# run at ~16-20 req/s, safely below that. Higher counts gain little because the
# origin latency grows under concurrency anyway.
DEFAULT_MAX_WORKERS = 8


def normalize_title(title: str) -> str:
    """Normalize song title for resilient fuzzy matching."""
    s = title.lower().strip()
    # Remove parenthetical / bracketed content like (Live), [Remastered]
    s = re.sub(r"[\(\[\{].*?[\)\]\}]", "", s)
    # Remove common trailing tags e.g. "- Remastered 2021", "- Live at ..."
    s = re.sub(
        r"-\s*(remaster(ed)?|live|mono|stereo|single|radio edit|deluxe|bonus track).*$",
        "",
        s,
        flags=re.IGNORECASE,
    )
    # Remove punctuation characters
    s = re.sub(r"[^\w\s]", "", s)
    return " ".join(s.split())


@dataclass
class MatchResult:
    """Result of matching a setlist song against a streaming provider catalog."""

    query_song: str
    track: Track | None
    score: float
    matched: bool


class TrackMatcher:
    """Resolves setlist song titles to streaming service catalog tracks."""

    def __init__(
        self,
        service: StreamingService,
        min_score: float = 70.0,
        max_workers: int = DEFAULT_MAX_WORKERS,
    ) -> None:
        """Initialize matcher.

        Args:
            service: Authenticated streaming service provider.
            min_score: Minimum match confidence score (0-100) to accept a candidate.
            max_workers: Max concurrent catalog searches (searches are network-bound).
        """
        self.service = service
        self.min_score = min_score
        self.max_workers = max_workers

    def match_song(self, song_name: str, artist_name: str) -> MatchResult:
        """Search and find the best matching track for a given song and artist."""
        clean_query = song_name.strip()
        if not clean_query:
            return MatchResult(query_song=song_name, track=None, score=0.0, matched=False)

        norm_query = normalize_title(clean_query)
        norm_artist = normalize_title(artist_name)

        # 1. Search with both artist and song name
        candidates = self.service.search_track(query=clean_query, artist=artist_name)

        # 2. Fallback: if no candidates, search by song name alone
        if not candidates:
            candidates = self.service.search_track(query=clean_query)

        if not candidates:
            return MatchResult(query_song=song_name, track=None, score=0.0, matched=False)

        best_track: Track | None = None
        best_score = 0.0

        for candidate in candidates:
            norm_cand_title = normalize_title(candidate.title)
            norm_cand_artist = normalize_title(candidate.artist)

            title_score = fuzz.token_set_ratio(norm_query, norm_cand_title)
            artist_score = (
                fuzz.token_set_ratio(norm_artist, norm_cand_artist)
                if norm_artist and norm_cand_artist
                else 100.0
            )

            # Combined weighted score (70% title, 30% artist)
            score = (title_score * 0.7) + (artist_score * 0.3)

            # Bonus for exact normalized match
            if norm_query == norm_cand_title:
                score += 5.0

            # Penalize live versions if the query didn't explicitly request live
            if "live" in candidate.title.lower() and "live" not in clean_query.lower():
                score -= 10.0

            if score > best_score:
                best_score = score
                best_track = candidate

        matched = best_score >= self.min_score and best_track is not None
        final_track = best_track if matched else None
        return MatchResult(
            query_song=song_name,
            track=final_track,
            score=round(best_score, 1),
            matched=matched,
        )

    def match_songs(self, song_names: list[str], artist_name: str) -> list[MatchResult]:
        """Batch match a list of song names for an artist.

        Songs are matched concurrently in a bounded thread pool; the returned
        list preserves the input order.
        """
        if not song_names:
            return []
        worker = partial(self.match_song, artist_name=artist_name)
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(pool.map(worker, song_names))
