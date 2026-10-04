"""Unit tests for core domain models."""

from touring_machine.models import Playlist, Track


def test_track_creation() -> None:
    track = Track(
        id="12345",
        title="Paranoid Android",
        artist="Radiohead",
        album="OK Computer",
        duration_seconds=387,
        url="https://tidal.com/track/12345",
    )
    assert track.id == "12345"
    assert track.title == "Paranoid Android"
    assert track.artist == "Radiohead"
    assert track.album == "OK Computer"
    assert track.duration_seconds == 387
    assert track.url == "https://tidal.com/track/12345"


def test_playlist_creation_empty() -> None:
    playlist = Playlist(
        id="playlist-123",
        name="Radiohead Tour 2026",
        description="Concert playlist",
    )
    assert playlist.id == "playlist-123"
    assert playlist.name == "Radiohead Tour 2026"
    assert playlist.description == "Concert playlist"
    assert playlist.tracks == []


def test_playlist_with_tracks() -> None:
    track1 = Track(title="Karma Police", artist="Radiohead")
    track2 = Track(title="No Surprises", artist="Radiohead")
    playlist = Playlist(
        id="playlist-456",
        name="Radiohead Encores",
        tracks=[track1, track2],
    )
    assert len(playlist.tracks) == 2
    assert playlist.tracks[0].title == "Karma Police"
    assert playlist.tracks[1].title == "No Surprises"
