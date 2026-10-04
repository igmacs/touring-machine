"""Unit tests for SetlistFmProvider."""

from unittest.mock import MagicMock

import httpx
import pytest

from touring_machine.exceptions import (
    ArtistNotFoundError,
    MissingApiKeyError,
    ProviderError,
)
from touring_machine.models import Artist
from touring_machine.providers.setlistfm import SetlistFmProvider


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SETLISTFM_API_KEY", raising=False)
    provider = SetlistFmProvider(api_key=None)
    with pytest.raises(MissingApiKeyError, match="API key is missing"):
        _ = provider.api_key


def test_provider_name() -> None:
    provider = SetlistFmProvider(api_key="test-key")
    assert provider.name == "setlistfm"


def test_search_artist_success() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "type": "artists",
        "artist": [
            {
                "mbid": "radiohead-mbid",
                "name": "Radiohead",
                "disambiguation": "British rock band",
            }
        ],
    }
    mock_client.get.return_value = mock_response

    provider = SetlistFmProvider(api_key="test-key", client=mock_client)
    artists = provider.search_artist("Radiohead")

    assert len(artists) == 1
    assert artists[0].name == "Radiohead"
    assert artists[0].mbid == "radiohead-mbid"
    assert artists[0].disambiguation == "British rock band"


def test_search_artist_not_found_returns_empty() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_client.get.return_value = mock_response

    provider = SetlistFmProvider(api_key="test-key", client=mock_client)
    artists = provider.search_artist("Nonexistent Band 12345")
    assert artists == []


def test_search_artist_invalid_api_key() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_client.get.return_value = mock_response

    provider = SetlistFmProvider(api_key="bad-key", client=mock_client)
    with pytest.raises(MissingApiKeyError, match="Unauthorized"):
        provider.search_artist("Radiohead")


def test_search_artist_server_error() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_client.get.return_value = mock_response

    provider = SetlistFmProvider(api_key="test-key", client=mock_client)
    with pytest.raises(ProviderError, match="HTTP 500"):
        provider.search_artist("Radiohead")


def test_get_recent_setlists_success() -> None:
    mock_client = MagicMock(spec=httpx.Client)

    # 1st call: search_artist
    search_resp = MagicMock(spec=httpx.Response)
    search_resp.status_code = 200
    search_resp.json.return_value = {"artist": [{"mbid": "radiohead-mbid", "name": "Radiohead"}]}

    # 2nd call: search_setlists
    setlist_resp = MagicMock(spec=httpx.Response)
    setlist_resp.status_code = 200
    setlist_resp.json.return_value = {
        "setlist": [
            {
                "id": "setlist-1",
                "eventDate": "04-08-2018",
                "venue": {
                    "name": "Wells Fargo Center",
                    "city": {
                        "name": "Philadelphia",
                        "country": {"name": "United States"},
                    },
                },
                "tour": {"name": "A Moon Shaped Pool Tour"},
                "sets": {
                    "set": [
                        {
                            "song": [
                                {"name": "Daydreaming"},
                                {"name": "Desert Island Disk"},
                                {"name": "Treefingers", "tape": True},
                            ]
                        },
                        {
                            "encore": 1,
                            "song": [
                                {"name": "The National Anthem"},
                                {
                                    "name": "Ceremony",
                                    "cover": {"name": "Joy Division"},
                                },
                            ],
                        },
                    ]
                },
                "url": "https://www.setlist.fm/setlist/test",
            },
            {
                "id": "empty-setlist",
                "eventDate": "01-08-2018",
                "sets": {"set": []},
            },
        ]
    }

    mock_client.get.side_effect = [search_resp, setlist_resp]

    provider = SetlistFmProvider(api_key="test-key", client=mock_client)
    setlists = provider.get_recent_setlists("Radiohead", limit=5)

    assert len(setlists) == 1  # Empty setlist was filtered out
    s = setlists[0]
    assert s.id == "setlist-1"
    assert s.event_date == "2018-08-04"
    assert s.venue_name == "Wells Fargo Center"
    assert s.city == "Philadelphia"
    assert s.country == "United States"
    assert s.tour_name == "A Moon Shaped Pool Tour"
    assert len(s.songs) == 5
    assert s.songs[0].name == "Daydreaming"
    assert s.songs[2].is_tape is True
    assert s.songs[4].name == "Ceremony"
    assert s.songs[4].is_cover is True


def test_get_recent_setlists_artist_not_found() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    search_resp = MagicMock(spec=httpx.Response)
    search_resp.status_code = 404
    mock_client.get.return_value = search_resp

    provider = SetlistFmProvider(api_key="test-key", client=mock_client)
    with pytest.raises(ArtistNotFoundError, match="not found"):
        provider.get_recent_setlists("Unknown Band")


def test_get_recent_setlists_with_artist_object() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    setlist_resp = MagicMock(spec=httpx.Response)
    setlist_resp.status_code = 200
    setlist_resp.json.return_value = {
        "setlist": [
            {
                "id": "setlist-2",
                "eventDate": "10-10-2024",
                "sets": {"set": [{"song": [{"name": "Karma Police"}]}]},
            }
        ]
    }
    mock_client.get.return_value = setlist_resp

    provider = SetlistFmProvider(api_key="test-key", client=mock_client)
    artist = Artist(name="Radiohead", mbid="radiohead-mbid")
    setlists = provider.get_recent_setlists(artist, limit=1)

    assert len(setlists) == 1
    assert setlists[0].id == "setlist-2"
    assert setlists[0].songs[0].name == "Karma Police"
