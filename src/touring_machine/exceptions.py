"""Exception hierarchy for touring-machine."""


class TouringMachineError(Exception):
    """Base exception for all touring-machine errors."""


class AuthenticationError(TouringMachineError):
    """Raised when authentication with a service fails or is missing."""


class StreamingServiceError(TouringMachineError):
    """Raised when a streaming service operation fails."""


class PlaylistCreationError(StreamingServiceError):
    """Raised when playlist creation fails on the streaming provider."""


class ProviderError(TouringMachineError):
    """Raised when an external data provider operation fails."""


class MissingApiKeyError(ProviderError):
    """Raised when an API key is required but not provided."""


class ArtistNotFoundError(ProviderError):
    """Raised when an artist cannot be found on a concert provider."""
