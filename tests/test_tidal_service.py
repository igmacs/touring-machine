"""Unit tests for TidalService."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from touring_machine.exceptions import AuthenticationError, PlaylistCreationError
from touring_machine.models import Track
from touring_machine.services.tidal import TidalService


def test_tidal_service_name() -> None:
    service = TidalService()
    assert service.name == "tidal"


def test_is_authenticated_false_when_no_session(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = False

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    assert not service.is_authenticated()
    mock_session.load_session_from_file.assert_not_called()


def test_is_authenticated_true_when_session_already_valid(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = True

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    assert service.is_authenticated()


def test_is_authenticated_loads_existing_session_file(tmp_path: Path) -> None:
    session_file = tmp_path / "session.json"
    session_file.write_text('{"token": "dummy"}')

    mock_session = MagicMock()
    # Initially False before loading, True after loading
    mock_session.check_login.side_effect = [False, True]

    service = TidalService(session_path=session_file, session=mock_session)
    assert service.is_authenticated()
    mock_session.load_session_from_file.assert_called_once_with(session_file)


def test_is_authenticated_caches_successful_check(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = True

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    assert service.is_authenticated()
    assert service.is_authenticated()
    assert service.is_authenticated()

    # check_login() hits the network in tidalapi; it must run only once per run
    mock_session.check_login.assert_called_once()


def test_is_authenticated_does_not_cache_failure(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = False

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    assert not service.is_authenticated()
    assert not service.is_authenticated()
    assert mock_session.check_login.call_count == 2


def test_search_track_checks_auth_once_across_searches(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = True
    mock_session.search.return_value = {"tracks": []}

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    service.search_track("Song A", "Artist")
    service.search_track("Song B", "Artist")

    mock_session.check_login.assert_called_once()
    assert mock_session.search.call_count == 2


def test_authenticate_non_interactive_returns_false_when_unauthenticated(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = False

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    assert not service.authenticate(interactive=False)


def test_authenticate_interactive_success(tmp_path: Path) -> None:
    session_file = tmp_path / "session.json"
    mock_session = MagicMock()
    # Not logged in initially, logged in after oauth future resolves
    mock_session.check_login.side_effect = [False, True]

    mock_login = MagicMock()
    mock_login.verification_uri_complete = "link.tidal.com/TESTCODE"
    mock_future = MagicMock()
    mock_session.login_oauth.return_value = (mock_login, mock_future)

    prompt_urls: list[str] = []

    def on_prompt(url: str) -> None:
        prompt_urls.append(url)

    service = TidalService(session_path=session_file, session=mock_session)
    result = service.authenticate(interactive=True, prompt_callback=on_prompt)

    assert result is True
    assert prompt_urls == ["https://link.tidal.com/TESTCODE"]
    mock_future.result.assert_called_once()
    mock_session.save_session_to_file.assert_called_once_with(session_file)


def test_create_playlist_raises_when_unauthenticated(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = False

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    with pytest.raises(AuthenticationError, match="not authenticated"):
        service.create_playlist("My Playlist")


def test_create_playlist_success(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = True

    mock_user = MagicMock()
    mock_user_playlist = MagicMock()
    mock_user_playlist.id = "pl-999"
    mock_user_playlist.name = "Radiohead Setlist"
    mock_user_playlist.description = "Tour 2026"
    mock_user_playlist.share_url = "https://tidal.com/playlist/pl-999"
    mock_user.create_playlist.return_value = mock_user_playlist

    mock_session.user = mock_user

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    playlist = service.create_playlist("Radiohead Setlist", "Tour 2026")

    assert playlist.id == "pl-999"
    assert playlist.name == "Radiohead Setlist"
    assert playlist.description == "Tour 2026"
    assert playlist.url == "https://tidal.com/playlist/pl-999"
    mock_user.create_playlist.assert_called_once_with(
        title="Radiohead Setlist", description="Tour 2026"
    )


def test_create_playlist_wraps_exception(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = True
    mock_user = MagicMock()
    mock_user.create_playlist.side_effect = RuntimeError("Network error")
    mock_session.user = mock_user

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    with pytest.raises(PlaylistCreationError, match="Network error"):
        service.create_playlist("Failing Playlist")


def test_create_playlist_with_folder_reuses_existing_folder(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = True

    existing_folder = MagicMock()
    existing_folder.id = "folder-1"
    existing_folder.name = "2026 Tours"
    mock_user = MagicMock()
    mock_user.favorites.playlist_folders.return_value = [existing_folder]
    mock_user_playlist = MagicMock()
    mock_user_playlist.id = "pl-1"
    mock_user_playlist.name = "My Pl"
    mock_user_playlist.description = ""
    mock_user_playlist.share_url = "https://tidal.com/playlist/pl-1"
    mock_user.create_playlist.return_value = mock_user_playlist
    mock_session.user = mock_user

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    service.create_playlist("My Pl", folder="2026 Tours")

    mock_user.create_folder.assert_not_called()
    mock_user.create_playlist.assert_called_once_with(
        title="My Pl", description="", parent_id="folder-1"
    )


def test_create_playlist_with_folder_creates_missing_folder(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = True

    new_folder = MagicMock()
    new_folder.id = "folder-new"
    new_folder.name = "2026 Tours"
    mock_user = MagicMock()
    mock_user.favorites.playlist_folders.return_value = []
    mock_user.create_folder.return_value = new_folder
    mock_user_playlist = MagicMock()
    mock_user_playlist.id = "pl-1"
    mock_user_playlist.name = "My Pl"
    mock_user_playlist.description = ""
    mock_user_playlist.share_url = "https://tidal.com/playlist/pl-1"
    mock_user.create_playlist.return_value = mock_user_playlist
    mock_session.user = mock_user

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    service.create_playlist("My Pl", folder="2026 Tours")

    mock_user.create_folder.assert_called_once_with(title="2026 Tours", parent_id="root")
    mock_user.create_playlist.assert_called_once_with(
        title="My Pl", description="", parent_id="folder-new"
    )


def test_create_playlist_rejects_nested_folder_path(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = True
    mock_user = MagicMock()
    mock_session.user = mock_user

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    with pytest.raises(PlaylistCreationError, match="top-level playlist folders"):
        service.create_playlist("My Pl", folder="2026 Tours/Radiohead")
    mock_user.create_playlist.assert_not_called()
    mock_user.create_folder.assert_not_called()


def test_create_playlist_with_folder_wraps_exception(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = True
    mock_user = MagicMock()
    mock_user.favorites.playlist_folders.side_effect = RuntimeError("Network error")
    mock_session.user = mock_user

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    with pytest.raises(PlaylistCreationError, match="Failed to resolve Tidal folder"):
        service.create_playlist("My Pl", folder="2026 Tours")
    mock_user.create_playlist.assert_not_called()


def test_add_tracks_success(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = True
    mock_pl = MagicMock()
    mock_session.playlist.return_value = mock_pl

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    tracks = [
        Track(id="t1", title="Song 1", artist="Artist"),
        Track(id="t2", title="Song 2", artist="Artist"),
    ]
    service.add_tracks("pl-123", tracks)

    mock_session.playlist.assert_called_once_with("pl-123")
    mock_pl.add.assert_called_once_with(["t1", "t2"])


def test_get_playlist_success(tmp_path: Path) -> None:
    mock_session = MagicMock()
    mock_session.check_login.return_value = True
    mock_pl = MagicMock()
    mock_pl.id = "pl-123"
    mock_pl.name = "My Pl"
    mock_pl.description = "A description"
    mock_pl.share_url = "https://tidal.com/playlist/pl-123"
    mock_session.playlist.return_value = mock_pl

    service = TidalService(session_path=tmp_path / "session.json", session=mock_session)
    pl = service.get_playlist("pl-123")
    assert pl is not None
    assert pl.id == "pl-123"
    assert pl.name == "My Pl"
