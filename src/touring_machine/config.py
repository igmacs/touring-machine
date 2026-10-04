"""Configuration helpers and paths for touring-machine."""

import os
from pathlib import Path


def get_config_dir() -> Path:
    """Return the base config directory for touring-machine, creating it if needed."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        base = Path(xdg_config)
    else:
        base = Path.home() / ".config"
    config_dir = base / "touring-machine"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_default_tidal_session_path() -> Path:
    """Return the default path to the Tidal session storage file."""
    return get_config_dir() / "tidal_session.json"
