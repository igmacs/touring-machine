"""Playlist generation strategies package."""

from touring_machine.strategies.base import PlaylistStrategy
from touring_machine.strategies.factory import get_strategy
from touring_machine.strategies.latest_show import LatestShowStrategy
from touring_machine.strategies.most_played import MostPlayedStrategy

__all__ = [
    "LatestShowStrategy",
    "MostPlayedStrategy",
    "PlaylistStrategy",
    "get_strategy",
]
