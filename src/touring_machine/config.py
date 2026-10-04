"""Configuration helpers and paths for touring-machine."""

import json
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


def get_config_file_path() -> Path:
    """Return the path to the general configuration file."""
    return get_config_dir() / "config.json"


def get_default_tidal_session_path() -> Path:
    """Return the default path to the Tidal session storage file."""
    return get_config_dir() / "tidal_session.json"


def get_api_key(provider: str = "setlistfm") -> str | None:
    """Retrieve an API key from environment variables or saved configuration.

    Args:
        provider: Provider identifier (e.g. 'setlistfm').
    """
    env_var = f"{provider.upper()}_API_KEY"
    if env_var in os.environ and os.environ[env_var].strip():
        return os.environ[env_var].strip()

    config_file = get_config_file_path()
    if config_file.exists():
        try:
            with config_file.open("r") as f:
                data = json.load(f)
                key = data.get("api_keys", {}).get(provider.lower())
                if key and str(key).strip():
                    return str(key).strip()
        except Exception:
            pass
    return None


def save_api_key(api_key: str, provider: str = "setlistfm") -> None:
    """Save an API key to the configuration file.

    Args:
        api_key: The secret API key string.
        provider: Provider identifier (e.g. 'setlistfm').
    """
    config_file = get_config_file_path()
    config_file.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {}
    if config_file.exists():
        try:
            with config_file.open("r") as f:
                data = json.load(f)
        except Exception:
            data = {}

    api_keys = data.setdefault("api_keys", {})
    api_keys[provider.lower()] = api_key.strip()

    with config_file.open("w") as f:
        json.dump(data, f, indent=2)

    try:
        config_file.chmod(0o600)
    except OSError:
        pass
