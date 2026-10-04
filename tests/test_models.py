"""Unit tests for core domain models."""

from touring_machine.models import (
    Artist,
    ConcertSetlist,
    Playlist,
    RankedSong,
    SongPerformance,
    Track,
)


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


def test_artist_creation() -> None:
    artist = Artist(name="The Smile", mbid="abc-123", disambiguation="English rock band")
    assert artist.name == "The Smile"
    assert artist.mbid == "abc-123"
    assert artist.disambiguation == "English rock band"


def test_concert_setlist_creation() -> None:
    artist = Artist(name="Radiohead", mbid="a74b1b7f-71a5-4011-9441-d0b5e4122711")
    song1 = SongPerformance(name="Burn the Witch")
    song2 = SongPerformance(name="Daydreaming", is_tape=False)
    song3 = SongPerformance(name="Treefingers", is_tape=True)

    setlist = ConcertSetlist(
        id="setlist-001",
        event_date="2024-08-23",
        artist=artist,
        venue_name="Madison Square Garden",
        city="New York",
        country="United States",
        tour_name="US Tour 2024",
        songs=[song1, song2, song3],
        url="https://www.setlist.fm/setlist/test",
    )

    assert setlist.id == "setlist-001"
    assert setlist.event_date == "2024-08-23"
    assert setlist.artist.name == "Radiohead"
    assert len(setlist.songs) == 3
    assert setlist.songs[2].is_tape is True


def test_ranked_song_creation() -> None:
    ranked = RankedSong(
        name="Idioteque",
        play_count=8,
        appearances_total=10,
        percentage=80.0,
        average_position=14.5,
    )
    assert ranked.name == "Idioteque"
    assert ranked.play_count == 8
    assert ranked.percentage == 80.0
    assert ranked.average_position == 14.5
