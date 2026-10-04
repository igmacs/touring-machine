"""Factory to instantiate streaming service providers."""

from touring_machine.services.base import StreamingService
from touring_machine.services.tidal import TidalService

SUPPORTED_SERVICES = {
    "tidal": TidalService,
}


def get_streaming_service(name: str = "tidal") -> StreamingService:
    """Return an instance of the requested streaming service provider.

    Args:
        name: Name of the streaming service (e.g. 'tidal').

    Raises:
        ValueError: If the streaming service is unknown.
    """
    normalized = name.lower().strip()
    service_cls = SUPPORTED_SERVICES.get(normalized)
    if not service_cls:
        supported = ", ".join(f"'{s}'" for s in SUPPORTED_SERVICES)
        msg = f"Unsupported streaming service: '{name}'. Supported: {supported}"
        raise ValueError(msg)

    return service_cls()
