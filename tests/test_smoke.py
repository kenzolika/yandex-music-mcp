"""Import and metadata checks. These do not call the Yandex Music API."""

import tomllib
from importlib.metadata import version
from pathlib import Path

import pytest

from yandex_music_mcp import __version__
from yandex_music_mcp.auth import main as auth_main
from yandex_music_mcp.server import (
    _dur,
    _load_token,
    _safe_name,
    _split_id,
    main as server_main,
    mcp,
)

ROOT = Path(__file__).resolve().parents[1]


def test_version_matches_installed_metadata():
    assert __version__
    assert __version__ == version("yandex-music-mcp")


def test_entry_points_are_callable():
    assert callable(server_main)
    assert callable(auth_main)


def test_server_app_name():
    assert mcp.name == "yandex-music"


def test_project_metadata_has_no_label_prefixes():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    description = project["description"]
    assert description
    assert not description.lower().startswith("description:")
    assert "\n" not in description
    for url in project["urls"].values():
        assert url.startswith("https://")
        assert not url.lower().startswith("website:")


def test_duration_format():
    assert _dur(None) is None
    assert _dur(0) is None
    assert _dur(65_000) == "1:05"


def test_split_track_id():
    assert _split_id("123:456") == ("123", "456")
    assert _split_id("123") == ("123", None)


def test_safe_filename():
    assert _safe_name("a/b") == "a_b"
    assert _safe_name(" . ") == "playlist"


def test_missing_token_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("YANDEX_MUSIC_TOKEN", raising=False)
    monkeypatch.delenv("YANDEX_MUSIC_TOKEN_FILE", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr("yandex_music_mcp.server.Path.home", lambda: tmp_path)
    with pytest.raises(RuntimeError, match="Нет токена"):
        _load_token()
