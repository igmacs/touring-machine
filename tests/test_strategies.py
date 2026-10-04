"""Unit tests for playlist strategies."""

import pytest

from touring_machine.models import Artist, ConcertSetlist, SongPerformance
from touring_machine.strategies import (
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


def test_strategy_factory() -> None:
    s1 = get_strategy("most-played")
    assert isinstance(s1, MostPlayedStrategy)

    s2 = get_strategy("latest")
    assert isinstance(s2, LatestShowStrategy)

    with pytest.raises(ValueError, match="Unknown playlist strategy"):
        get_strategy("nonexistent")
