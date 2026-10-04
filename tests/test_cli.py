"""Unit tests for touring-machine CLI."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from touring_machine.cli import app
from touring_machine.exceptions import MissingApiKeyError, PlaylistCreationError
from touring_machine.generator import GenerationResult
from touring_machine.matcher import MatchResult
from touring_machine.models import Artist, ConcertSetlist, Playlist, SongPerformance, Track

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Concert playlist generator" in result.stdout
    assert "create-playlist" in result.stdout
    assert "generate" in result.stdout
    assert "login" in result.stdout
    assert "set-key" in result.stdout
    assert "status" in result.stdout


def test_status_command() -> None:
    mock_service = MagicMock()
    mock_service.is_authenticated.return_value = True
    mock_service.session_path = "/path/to/session.json"

    with patch("touring_machine.cli.get_streaming_service", return_value=mock_service):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "tidal" in result.stdout
        assert "setlistfm" in result.stdout
        assert "Authenticated" in result.stdout


def test_set_key_command() -> None:
    with patch("touring_machine.cli.save_api_key") as mock_save:
        result = runner.invoke(app, ["set-key", "setlistfm", "my-secret-key"])
        assert result.exit_code == 0
        assert "Successfully saved API key for 'setlistfm'" in result.stdout
        mock_save.assert_called_once_with(api_key="my-secret-key", provider="setlistfm")


def test_login_already_authenticated() -> None:
    mock_service = MagicMock()
    mock_service.name = "tidal"
    mock_service.is_authenticated.return_value = True

    with patch("touring_machine.cli.get_streaming_service", return_value=mock_service):
        result = runner.invoke(app, ["login"])
        assert result.exit_code == 0
        assert "Already authenticated with Tidal" in result.stdout
        mock_service.authenticate.assert_not_called()


def test_login_force_when_already_authenticated() -> None:
    mock_service = MagicMock()
    mock_service.name = "tidal"
    mock_service.is_authenticated.return_value = True
    mock_service.authenticate.return_value = True

    with patch("touring_machine.cli.get_streaming_service", return_value=mock_service):
        result = runner.invoke(app, ["login", "--force"])
        assert result.exit_code == 0
        assert "Successfully authenticated with Tidal" in result.stdout
        mock_service.authenticate.assert_called_once()


def test_login_success() -> None:
    mock_service = MagicMock()
    mock_service.name = "tidal"
    mock_service.is_authenticated.return_value = False
    mock_service.authenticate.return_value = True

    with patch("touring_machine.cli.get_streaming_service", return_value=mock_service):
        result = runner.invoke(app, ["login"])
        assert result.exit_code == 0
        assert "Successfully authenticated with Tidal" in result.stdout
        mock_service.authenticate.assert_called_once()


def test_login_failure() -> None:
    mock_service = MagicMock()
    mock_service.name = "tidal"
    mock_service.is_authenticated.return_value = False
    mock_service.authenticate.return_value = False

    with patch("touring_machine.cli.get_streaming_service", return_value=mock_service):
        result = runner.invoke(app, ["login"])
        assert result.exit_code == 1
        assert "Authentication failed with Tidal" in result.output


def test_login_unknown_service() -> None:
    result = runner.invoke(app, ["login", "--service", "foobar"])
    assert result.exit_code == 1
    assert "Unsupported streaming service" in result.output


def test_create_playlist_unauthenticated() -> None:
    mock_service = MagicMock()
    mock_service.name = "tidal"
    mock_service.is_authenticated.return_value = False

    with patch("touring_machine.cli.get_streaming_service", return_value=mock_service):
        result = runner.invoke(app, ["create-playlist", "My Concert"])
        assert result.exit_code == 1
        assert "Not authenticated with Tidal" in result.output


def test_create_playlist_success() -> None:
    mock_service = MagicMock()
    mock_service.name = "tidal"
    mock_service.is_authenticated.return_value = True
    mock_service.create_playlist.return_value = Playlist(
        id="pl-test-123",
        name="Tour Playlist",
        description="Upcoming show",
        url="https://tidal.com/playlist/pl-test-123",
    )

    with patch("touring_machine.cli.get_streaming_service", return_value=mock_service):
        result = runner.invoke(
            app, ["create-playlist", "Tour Playlist", "--description", "Upcoming show"]
        )
        assert result.exit_code == 0
        assert "Playlist Created Successfully" in result.stdout
        assert "Tour Playlist" in result.stdout
        assert "pl-test-123" in result.stdout
        assert "https://tidal.com/playlist/pl-test-123" in result.stdout
        mock_service.create_playlist.assert_called_once_with(
            name="Tour Playlist", description="Upcoming show"
        )


def test_create_playlist_service_error() -> None:
    mock_service = MagicMock()
    mock_service.name = "tidal"
    mock_service.is_authenticated.return_value = True
    mock_service.create_playlist.side_effect = PlaylistCreationError("API quota exceeded")

    with patch("touring_machine.cli.get_streaming_service", return_value=mock_service):
        result = runner.invoke(app, ["create-playlist", "Failed Playlist"])
        assert result.exit_code == 1
        assert "Failed to create playlist: API quota exceeded" in result.output


def test_generate_unauthenticated_streaming() -> None:
    mock_service = MagicMock()
    mock_service.name = "tidal"
    mock_service.is_authenticated.return_value = False

    with patch("touring_machine.cli.get_streaming_service", return_value=mock_service):
        result = runner.invoke(app, ["generate", "Radiohead"])
        assert result.exit_code == 1
        assert "Not authenticated with Tidal" in result.output


def test_generate_missing_api_key() -> None:
    mock_service = MagicMock()
    mock_service.name = "tidal"
    mock_service.is_authenticated.return_value = True

    with (
        patch("touring_machine.cli.get_streaming_service", return_value=mock_service),
        patch(
            "touring_machine.cli.SetlistFmProvider.api_key",
            new_callable=lambda: pytest.fail,
        ),
        patch(
            "touring_machine.cli.SetlistFmProvider",
            side_effect=MissingApiKeyError("Setlist.fm API key is missing"),
        ),
    ):
        result = runner.invoke(app, ["generate", "Radiohead"])
        assert result.exit_code == 1
        assert "Setlist.fm API key is missing" in result.output


def test_generate_dry_run() -> None:
    mock_service = MagicMock()
    mock_service.name = "tidal"
    mock_service.is_authenticated.return_value = True

    artist = Artist(name="Radiohead")
    setlist = ConcertSetlist(
        id="s1",
        event_date="2024-08-01",
        artist=artist,
        songs=[SongPerformance(name="Karma Police")],
    )

    mock_provider = MagicMock()
    mock_provider.api_key = "test-key"
    mock_provider.get_recent_setlists.return_value = [setlist]

    match = MatchResult(
        query_song="Karma Police",
        track=Track(id="t1", title="Karma Police", artist="Radiohead"),
        score=100.0,
        matched=True,
    )

    with (
        patch("touring_machine.cli.get_streaming_service", return_value=mock_service),
        patch("touring_machine.cli.SetlistFmProvider", return_value=mock_provider),
        patch("touring_machine.generator.TrackMatcher.match_songs", return_value=[match]),
    ):
        result = runner.invoke(app, ["generate", "Radiohead", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run complete. No playlist was created." in result.stdout
        assert "Karma Police" in result.stdout
        mock_service.create_playlist.assert_not_called()


def test_generate_success() -> None:
    mock_service = MagicMock()
    mock_service.name = "tidal"
    mock_service.is_authenticated.return_value = True

    artist = Artist(name="Radiohead")
    setlists = [
        ConcertSetlist(
            id="s1",
            event_date="2024-08-01",
            artist=artist,
            songs=[SongPerformance(name="Paranoid Android")],
        )
    ]
    track = Track(id="t1", title="Paranoid Android", artist="Radiohead")
    match = MatchResult(
        query_song="Paranoid Android",
        track=track,
        score=100.0,
        matched=True,
    )
    gen_result = GenerationResult(
        playlist=Playlist(
            id="pl-gen-100",
            name="Radiohead - Concert Setlist",
            url="https://tidal.com/playlist/pl-gen-100",
        ),
        artist=artist,
        setlists=setlists,
        matched_tracks=[track],
        unmatched_songs=[],
        match_results=[match],
    )

    mock_provider = MagicMock()
    mock_provider.api_key = "test-key"

    with (
        patch("touring_machine.cli.get_streaming_service", return_value=mock_service),
        patch("touring_machine.cli.SetlistFmProvider", return_value=mock_provider),
        patch("touring_machine.cli.PlaylistGenerator.generate", return_value=gen_result),
    ):
        result = runner.invoke(app, ["generate", "Radiohead"])
        assert result.exit_code == 0
        assert "Concert Playlist Generated Successfully" in result.stdout
        assert "Radiohead - Concert Setlist" in result.stdout
        assert "Tracks Added: 1 / 1" in result.stdout
