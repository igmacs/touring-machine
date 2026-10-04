"""Factory to instantiate playlist generation strategies."""

from touring_machine.strategies.base import PlaylistStrategy
from touring_machine.strategies.latest_show import LatestShowStrategy
from touring_machine.strategies.most_played import MostPlayedStrategy

STRATEGY_MAP: dict[str, type[PlaylistStrategy]] = {
    "most-played": MostPlayedStrategy,
    "most_played": MostPlayedStrategy,
    "top": MostPlayedStrategy,
    "latest": LatestShowStrategy,
    "latest-show": LatestShowStrategy,
    "recent": LatestShowStrategy,
}


def get_strategy(name: str = "most-played", ignore_tapes: bool = True) -> PlaylistStrategy:
    """Return an instance of the requested playlist strategy.

    Args:
        name: Strategy name (e.g. 'most-played', 'latest').
        ignore_tapes: Whether to exclude tape recordings.

    Raises:
        ValueError: If strategy name is unknown.
    """
    normalized = name.lower().strip()
    cls = STRATEGY_MAP.get(normalized)
    if not cls:
        valid = ", ".join(f"'{k}'" for k in sorted({"most-played", "latest"}))
        msg = f"Unknown playlist strategy: '{name}'. Supported: {valid}"
        raise ValueError(msg)

    return cls(ignore_tapes=ignore_tapes)
