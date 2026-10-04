"""Streaming services package."""

from touring_machine.services.base import StreamingService
from touring_machine.services.factory import SUPPORTED_SERVICES, get_streaming_service
from touring_machine.services.tidal import TidalService

__all__ = ["SUPPORTED_SERVICES", "StreamingService", "TidalService", "get_streaming_service"]
