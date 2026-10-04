"""Unit tests for config helpers."""

import json
from pathlib import Path

import pytest

from touring_machine.config import get_api_key, get_config_dir, save_api_key


def test_get_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SETLISTFM_API_KEY", "env-secret-key")
    assert get_api_key("setlistfm") == "env-secret-key"


def test_save_and_get_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SETLISTFM_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    save_api_key("file-secret-key", "setlistfm")
    assert get_api_key("setlistfm") == "file-secret-key"

    config_file = tmp_path / "touring-machine" / "config.json"
    assert config_file.exists()
    content = json.loads(config_file.read_text())
    assert content["api_keys"]["setlistfm"] == "file-secret-key"


def test_get_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = get_config_dir()
    assert config_dir == tmp_path / "touring-machine"
    assert config_dir.is_dir()
