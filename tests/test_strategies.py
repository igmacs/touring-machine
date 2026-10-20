"""Unit tests for playlist strategies."""

import pytest

from touring_machine.models import Artist, ConcertSetlist, SongPerformance
from touring_machine.strategies import (
    CurrentTourStrategy,
    LatestShowStrategy,
    MostPlayedStrategy,
    get_strategy,
)


@pytest.fixture
def sample_setlists() -> list[ConcertSetlist]:
    artist = Artist(name="Radiohead")
    s1 = ConcertSetlist(
        id="s1",
        event_date="2024-08-01",
        artist=artist,
        songs=[
            SongPerformance(name="Intro Tape", is_tape=True),
            SongPerformance(name="Burn the Witch"),
            SongPerformance(name="Daydreaming"),
            SongPerformance(name="Karma Police"),
        ],
    )
    s2 = ConcertSetlist(
        id="s2",
        event_date="2024-08-02",
        artist=artist,
        songs=[
            SongPerformance(name="Burn the Witch"),
            SongPerformance(name="Karma Police"),
            SongPerformance(name="No Surprises"),
        ],
    )
    s3 = ConcertSetlist(
        id="s3",
        event_date="2024-08-03",
        artist=artist,
        songs=[
            SongPerformance(name="Burn the Witch"),
            SongPerformance(name="Daydreaming"),
            SongPerformance(name="Paranoid Android"),
        ],
    )
    return [s1, s2, s3]


def test_most_played_strategy(sample_setlists: list[ConcertSetlist]) -> None:
    strategy = MostPlayedStrategy(ignore_tapes=True)
    tracklist = strategy.generate_tracklist(sample_setlists)

    # Burn the Witch: 3/3
    # Daydreaming: 2/3
    # Karma Police: 2/3
    # No Surprises: 1/3
    # Paranoid Android: 1/3
    assert tracklist[0] == "Burn the Witch"
    assert "Intro Tape" not in tracklist
    assert len(tracklist) == 5

    ranked = strategy.generate_ranked_songs(sample_setlists)
    assert ranked[0].name == "Burn the Witch"
    assert ranked[0].play_count == 3
    assert ranked[0].percentage == 100.0


def test_most_played_strategy_with_limit(sample_setlists: list[ConcertSetlist]) -> None:
    strategy = MostPlayedStrategy()
    tracklist = strategy.generate_tracklist(sample_setlists, limit=2)
    assert len(tracklist) == 2
    assert tracklist[0] == "Burn the Witch"


def test_latest_show_strategy(sample_setlists: list[ConcertSetlist]) -> None:
    strategy = LatestShowStrategy(ignore_tapes=True)
    tracklist = strategy.generate_tracklist(sample_setlists)

    # s1 is the first/latest in sample_setlists
    assert tracklist == ["Burn the Witch", "Daydreaming", "Karma Police"]
    assert "Intro Tape" not in tracklist


def test_latest_show_strategy_limit(sample_setlists: list[ConcertSetlist]) -> None:
    strategy = LatestShowStrategy()
    tracklist = strategy.generate_tracklist(sample_setlists, limit=2)
    assert tracklist == ["Burn the Witch", "Daydreaming"]


@pytest.fixture
def tour_setlists() -> list[ConcertSetlist]:
    """Shows of a single tour where average-position ordering differs from play counts.

    A: played at slot 1, 2, 1 (avg 1.33, 3 shows)
    B: played at slot 2, 2 (avg 2.0, 2 shows)
    D: played once as show opener (avg 1.0, 1 show)
    """
    artist = Artist(name="Radiohead")
    return [
        ConcertSetlist(
            id="t1",
            event_date="2024-08-01",
            artist=artist,
            tour_name="A Moon Shaped Pool Tour",
            songs=[
                SongPerformance(name="Intro Tape", is_tape=True),
                SongPerformance(name="A Song"),
                SongPerformance(name="B Song"),
                SongPerformance(name="C Song"),
            ],
        ),
        ConcertSetlist(
            id="t2",
            event_date="2024-08-02",
            artist=artist,
            tour_name="A Moon Shaped Pool Tour",
            songs=[
                SongPerformance(name="D Song"),
                SongPerformance(name="A Song"),
                SongPerformance(name="E Song"),
            ],
        ),
        ConcertSetlist(
            id="t3",
            event_date="2024-08-03",
            artist=artist,
            tour_name="A Moon Shaped Pool Tour",
            songs=[
                SongPerformance(name="A Song"),
                SongPerformance(name="B Song"),
                SongPerformance(name="F Song"),
            ],
        ),
    ]


def test_current_tour_strategy_average_setlist_order(tour_setlists: list[ConcertSetlist]) -> None:
    strategy = CurrentTourStrategy(ignore_tapes=True)
    tracklist = strategy.generate_tracklist(tour_setlists)

    # Ordered by average position: D (1.0), A (1.33), B (2.0), then one-offs at slot 3
    assert tracklist == ["D Song", "A Song", "B Song", "C Song", "E Song", "F Song"]
    assert "Intro Tape" not in tracklist

    ranked = strategy.generate_ranked_songs(tour_setlists)
    assert ranked[0].name == "D Song"
    assert ranked[0].average_position == 1.0
    assert ranked[0].percentage == 33.3
    a_song = next(s for s in ranked if s.name == "A Song")
    assert a_song.play_count == 3
    assert a_song.percentage == 100.0
    assert a_song.average_position == 1.3  # positions 1, 2, 1 -> 4/3 rounded to 1.3


def test_current_tour_strategy_with_limit(tour_setlists: list[ConcertSetlist]) -> None:
    strategy = CurrentTourStrategy()
    tracklist = strategy.generate_tracklist(tour_setlists, limit=2)
    assert tracklist == ["D Song", "A Song"]


def test_current_tour_strategy_scope() -> None:
    assert CurrentTourStrategy().scope == "current-tour"
    assert MostPlayedStrategy().scope == "recent"
    assert LatestShowStrategy().scope == "recent"


def test_strategy_factory() -> None:
    s1 = get_strategy("most-played")
    assert isinstance(s1, MostPlayedStrategy)

    s2 = get_strategy("latest")
    assert isinstance(s2, LatestShowStrategy)

    s3 = get_strategy("current-tour")
    assert isinstance(s3, CurrentTourStrategy)

    s4 = get_strategy("average-setlist")
    assert isinstance(s4, CurrentTourStrategy)

    with pytest.raises(ValueError, match="Unknown playlist strategy"):
        get_strategy("nonexistent")
