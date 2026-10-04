"""Core domain models for touring-machine.

These models are independent of any specific streaming service (Tidal, Spotify, etc.)
or concert data provider (Setlist.fm).
"""

from pydantic import BaseModel, Field


class Track(BaseModel):
    """Represents a musical track/song from a streaming provider catalog."""

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


class Artist(BaseModel):
    """Represents a musical artist/band."""

    name: str = Field(description="Artist name")
    mbid: str | None = Field(default=None, description="MusicBrainz Identifier")
    disambiguation: str | None = Field(
        default=None, description="Disambiguation note e.g. 'British rock band'"
    )


class SongPerformance(BaseModel):
    """Represents a song played at a concert/show."""

    name: str = Field(description="Song title")
    is_tape: bool = Field(
        default=False, description="True if played from tape/recording rather than performed live"
    )
    is_cover: bool = Field(default=False, description="True if the song is a cover")
    info: str | None = Field(default=None, description="Extra performance notes")


class ConcertSetlist(BaseModel):
    """Represents a single concert setlist."""

    id: str = Field(description="Concert or setlist identifier")
    event_date: str = Field(description="Date of the concert (e.g. '2024-08-23')")
    artist: Artist = Field(description="Artist who performed")
    venue_name: str | None = Field(default=None, description="Concert venue name")
    city: str | None = Field(default=None, description="City of the venue")
    country: str | None = Field(default=None, description="Country of the venue")
    tour_name: str | None = Field(default=None, description="Tour name if applicable")
    songs: list[SongPerformance] = Field(
        default_factory=list, description="Ordered list of songs played"
    )
    url: str | None = Field(default=None, description="URL to the setlist on the provider")


class RankedSong(BaseModel):
    """Represents an aggregated song with statistics across multiple setlists."""

    name: str = Field(description="Song name")
    play_count: int = Field(description="Number of times played across analyzed setlists")
    appearances_total: int = Field(description="Total setlists analyzed")
    percentage: float = Field(description="Percentage of shows this song was played (0-100)")
    average_position: float = Field(
        default=0.0, description="Average position within the setlist order"
    )
