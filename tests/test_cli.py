"""Unit tests for touring-machine CLI."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from touring_machine.cli import app
from touring_machine.exceptions import PlaylistCreationError
from touring_machine.models import Playlist

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Concert playlist generator" in result.stdout
    assert "create-playlist" in result.stdout
    assert "login" in result.stdout
    assert "status" in result.stdout


def test_status_command() -> None:
    mock_service = MagicMock()
    mock_service.is_authenticated.return_value = True
    mock_service.session_path = "/path/to/session.json"

    with patch("touring_machine.cli.get_streaming_service", return_value=mock_service):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "tidal" in result.stdout
        assert "Authenticated" in result.stdout


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
