"""Core domain models for touring-machine.

These models are independent of any specific streaming service (Tidal, Spotify, etc.)
or concert data provider (Setlist.fm).
"""

from pydantic import BaseModel, Field


class Track(BaseModel):
    """Represents a musical track/song."""

    id: str | None = Field(default=None, description="Service-specific identifier")
    title: str = Field(description="Track title")
    artist: str = Field(description="Primary artist name")
    album: str | None = Field(default=None, description="Album name")
    isrc: str | None = Field(default=None, description="International Standard Recording Code")
    duration_seconds: int | None = Field(default=None, description="Track duration in seconds")
    url: str | None = Field(default=None, description="Web URL to listen to the track")


class Playlist(BaseModel):
    """Represents a music playlist."""

    id: str = Field(description="Unique service identifier for the playlist")
    name: str = Field(description="Playlist title")
    description: str | None = Field(default=None, description="Playlist description")
    url: str | None = Field(default=None, description="Shareable URL to the playlist")
    tracks: list[Track] = Field(default_factory=list, description="Ordered tracks in playlist")
