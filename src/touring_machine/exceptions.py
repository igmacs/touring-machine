"""Exception hierarchy for touring-machine."""


class TouringMachineError(Exception):
    """Base exception for all touring-machine errors."""


class AuthenticationError(TouringMachineError):
    """Raised when authentication with a service fails or is missing."""


class StreamingServiceError(TouringMachineError):
    """Raised when a streaming service operation fails."""


class PlaylistCreationError(StreamingServiceError):
    """Raised when playlist creation fails on the streaming provider."""
