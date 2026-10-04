"""Unit tests for TrackMatcher."""

from unittest.mock import MagicMock

from touring_machine.matcher import TrackMatcher, normalize_title
from touring_machine.models import Track


def test_normalize_title() -> None:
    assert normalize_title("Paranoid Android - Remastered 2017") == "paranoid android"
    assert normalize_title("Karma Police (Live in Berlin)") == "karma police"
    assert (
        normalize_title("Everything In Its Right Place [Remaster]")
        == "everything in its right place"
    )
    assert normalize_title("No Surprises - Single Version") == "no surprises"
    assert normalize_title("Where I End and You Begin.") == "where i end and you begin"


def test_match_song_exact_match() -> None:
    mock_service = MagicMock()
    candidate = Track(
        id="track-1",
        title="Paranoid Android",
        artist="Radiohead",
        album="OK Computer",
    )
    mock_service.search_track.return_value = [candidate]

    matcher = TrackMatcher(service=mock_service)
    result = matcher.match_song("Paranoid Android", "Radiohead")

    assert result.matched is True
    assert result.track is not None
    assert result.track.id == "track-1"
    assert result.score >= 90.0


def test_match_song_remastered_version() -> None:
    mock_service = MagicMock()
    candidate = Track(
        id="track-2",
        title="Karma Police - 2017 Remaster",
        artist="Radiohead",
        album="OK Computer OKNOTOK",
    )
    mock_service.search_track.return_value = [candidate]

    matcher = TrackMatcher(service=mock_service)
    result = matcher.match_song("Karma Police", "Radiohead")

    assert result.matched is True
    assert result.track is not None
    assert result.track.id == "track-2"


def test_match_song_prefers_studio_over_live() -> None:
    mock_service = MagicMock()
    live_track = Track(
        id="track-live",
        title="Idioteque (Live in Oxford)",
        artist="Radiohead",
    )
    studio_track = Track(
        id="track-studio",
        title="Idioteque",
        artist="Radiohead",
    )
    mock_service.search_track.return_value = [live_track, studio_track]

    matcher = TrackMatcher(service=mock_service)
    result = matcher.match_song("Idioteque", "Radiohead")

    assert result.matched is True
    assert result.track is not None
    assert result.track.id == "track-studio"


def test_match_song_no_candidates_returns_unmatched() -> None:
    mock_service = MagicMock()
    mock_service.search_track.return_value = []

    matcher = TrackMatcher(service=mock_service)
    result = matcher.match_song("Very Obscure Unreleased Song", "Radiohead")

    assert result.matched is False
    assert result.track is None
    assert result.score == 0.0


def test_match_song_below_threshold_returns_unmatched() -> None:
    mock_service = MagicMock()
    unrelated_track = Track(
        id="track-unrelated",
        title="Completely Different Song",
        artist="Radiohead",
    )
    mock_service.search_track.return_value = [unrelated_track]

    matcher = TrackMatcher(service=mock_service, min_score=75.0)
    result = matcher.match_song("Creep", "Radiohead")

    assert result.matched is False
    assert result.track is None


def test_match_songs_batch() -> None:
    mock_service = MagicMock()
    t1 = Track(id="1", title="Song One", artist="Artist")
    t2 = Track(id="2", title="Song Two", artist="Artist")

    mock_service.search_track.side_effect = [[t1], [t2]]

    matcher = TrackMatcher(service=mock_service)
    results = matcher.match_songs(["Song One", "Song Two"], "Artist")

    assert len(results) == 2
    assert results[0].matched is True
    assert results[0].track.id == "1"
    assert results[1].matched is True
    assert results[1].track.id == "2"
