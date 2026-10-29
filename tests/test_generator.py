"""Unit tests for PlaylistGenerator engine."""

from unittest.mock import MagicMock

import pytest

from touring_machine.exceptions import TouringMachineError
from touring_machine.generator import PlaylistGenerator
from touring_machine.models import (
    Artist,
    ConcertSetlist,
    Playlist,
    SongPerformance,
    Track,
)


@pytest.fixture
def mock_streaming_service() -> MagicMock:
    service = MagicMock()
    service.name = "tidal"
    service.create_playlist.return_value = Playlist(
        id="pl-generated-1",
        name="Radiohead - Concert Setlist",
        description="Test description",
        url="https://tidal.com/playlist/pl-generated-1",
    )

    # Search track returns a matching track
    def search_mock(query: str, artist: str | None = None) -> list[Track]:
        return [
            Track(
                id=f"track-{query}",
                title=query,
                artist=artist or "Radiohead",
            )
        ]

    service.search_track.side_effect = search_mock
    return service


@pytest.fixture
def mock_concert_provider() -> MagicMock:
    provider = MagicMock()
    provider.name = "setlistfm"
    artist = Artist(name="Radiohead", mbid="radiohead-mbid")
    provider.get_recent_setlists.return_value = [
        ConcertSetlist(
            id="c1",
            event_date="2024-08-01",
            artist=artist,
            songs=[
                SongPerformance(name="Karma Police"),
                SongPerformance(name="No Surprises"),
            ],
        ),
        ConcertSetlist(
            id="c2",
            event_date="2024-08-02",
            artist=artist,
            songs=[
                SongPerformance(name="Karma Police"),
                SongPerformance(name="Paranoid Android"),
            ],
        ),
    ]
    return provider


def test_generator_success(
    mock_streaming_service: MagicMock, mock_concert_provider: MagicMock
) -> None:
    generator = PlaylistGenerator(
        streaming_service=mock_streaming_service,
        concert_provider=mock_concert_provider,
    )

    result = generator.generate(
        artist_name="Radiohead",
        shows=2,
        limit=10,
        strategy_name="most-played",
    )

    assert result.playlist.id == "pl-generated-1"
    assert result.artist.name == "Radiohead"
    assert len(result.setlists) == 2
    assert len(result.matched_tracks) == 3
    assert result.unmatched_songs == []

    mock_streaming_service.create_playlist.assert_called_once()
    mock_streaming_service.add_tracks.assert_called_once()


def test_generator_passes_folder_to_playlist_creation(
    mock_streaming_service: MagicMock, mock_concert_provider: MagicMock
) -> None:
    generator = PlaylistGenerator(
        streaming_service=mock_streaming_service,
        concert_provider=mock_concert_provider,
    )

    generator.generate(artist_name="Radiohead", playlist_folder="2026 Tours")

    create_kwargs = mock_streaming_service.create_playlist.call_args.kwargs
    assert create_kwargs["folder"] == "2026 Tours"


def test_generator_no_setlists_raises(mock_streaming_service: MagicMock) -> None:
    provider = MagicMock()
    provider.get_recent_setlists.return_value = []

    generator = PlaylistGenerator(
        streaming_service=mock_streaming_service,
        concert_provider=provider,
    )

    with pytest.raises(TouringMachineError, match="No recent concert setlists found"):
        generator.generate("Unknown Artist")


def test_generator_no_songs_raises(mock_streaming_service: MagicMock) -> None:
    provider = MagicMock()
    artist = Artist(name="Silent Band")
    provider.get_recent_setlists.return_value = [
        ConcertSetlist(id="c1", event_date="2024-01-01", artist=artist, songs=[])
    ]

    generator = PlaylistGenerator(
        streaming_service=mock_streaming_service,
        concert_provider=provider,
    )

    with pytest.raises(TouringMachineError, match="No playable songs found"):
        generator.generate("Silent Band")


def test_generator_tour_without_song_setlists_raises(mock_streaming_service: MagicMock) -> None:
    provider = MagicMock()
    provider.get_current_tour_setlists.return_value = []

    generator = PlaylistGenerator(
        streaming_service=mock_streaming_service,
        concert_provider=provider,
    )

    with pytest.raises(TouringMachineError, match="no setlists with songs yet"):
        generator.generate("Radiohead", strategy_name="current-tour")


def test_generator_fetches_current_tour_setlists_for_tour_strategy(
    mock_streaming_service: MagicMock,
) -> None:
    provider = MagicMock()
    artist = Artist(name="Radiohead", mbid="radiohead-mbid")
    provider.get_current_tour_setlists.return_value = [
        ConcertSetlist(
            id="t1",
            event_date="2024-08-01",
            artist=artist,
            tour_name="A Moon Shaped Pool Tour",
            songs=[SongPerformance(name="Burn the Witch")],
        )
    ]

    generator = PlaylistGenerator(
        streaming_service=mock_streaming_service,
        concert_provider=provider,
    )

    generator.generate("Radiohead", strategy_name="current-tour", shows=10)

    provider.get_current_tour_setlists.assert_called_once_with("Radiohead", limit=10)
    provider.get_recent_setlists.assert_not_called()


def test_generator_fetches_recent_setlists_for_default_strategy(
    mock_streaming_service: MagicMock,
) -> None:
    provider = MagicMock()
    artist = Artist(name="Radiohead", mbid="radiohead-mbid")
    provider.get_recent_setlists.return_value = [
        ConcertSetlist(
            id="c1",
            event_date="2024-08-01",
            artist=artist,
            songs=[SongPerformance(name="Burn the Witch")],
        )
    ]

    generator = PlaylistGenerator(
        streaming_service=mock_streaming_service,
        concert_provider=provider,
    )

    generator.generate("Radiohead", strategy_name="most-played", shows=3)

    provider.get_recent_setlists.assert_called_once_with("Radiohead", limit=3)
    provider.get_current_tour_setlists.assert_not_called()
