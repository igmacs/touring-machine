"""Unit tests for service factory."""

import pytest

from touring_machine.services.factory import get_streaming_service
from touring_machine.services.tidal import TidalService


def test_get_streaming_service_tidal() -> None:
    service = get_streaming_service("tidal")
    assert isinstance(service, TidalService)
    assert service.name == "tidal"


def test_get_streaming_service_case_insensitive() -> None:
    service = get_streaming_service("  TIDAL  ")
    assert isinstance(service, TidalService)


def test_get_streaming_service_unsupported() -> None:
    with pytest.raises(ValueError, match="Unsupported streaming service"):
        get_streaming_service("unknown_service")
