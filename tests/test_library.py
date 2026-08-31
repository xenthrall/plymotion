"""Tests for the local theme library module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import plymotion.library as library
from plymotion.library import (
    delete_library_theme,
    list_library_themes,
    sample_preview_frames,
    save_manifest,
    slugify,
    unique_slug,
)


def test_slugify_basic() -> None:
    assert slugify("My Theme!") == "my-theme"
    assert slugify("  spaced -- out  ") == "spaced-out"
    assert slugify("") == "theme"


def test_unique_slug_avoids_collisions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    themes_dir = tmp_path / "themes"
    monkeypatch.setattr(library, "LIBRARY_THEMES_DIR", themes_dir)

    first = unique_slug("Cool Theme")
    (themes_dir / first).mkdir(parents=True)
    second = unique_slug("Cool Theme")

    assert first == "cool-theme"
    assert second == "cool-theme-2"
    assert first != second


def _write_theme(
    themes_dir: Path, slug: str, *, frame_count: int = 3, name: str | None = None
) -> Path:
    theme_dir = themes_dir / slug
    theme_dir.mkdir(parents=True)
    for i in range(1, frame_count + 1):
        (theme_dir / f"frame{i}.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    save_manifest(
        theme_dir,
        name=name or slug,
        frame_count=frame_count,
        resolution=[1920, 1080],
        fps=30,
        loop_seconds=frame_count / 50,
        source_video="/tmp/input.mp4",
        created_at="2026-08-31T00:00:00+00:00",
    )
    return theme_dir


def test_list_library_themes_empty_when_dir_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(library, "LIBRARY_THEMES_DIR", tmp_path / "does-not-exist")
    assert list_library_themes() == []


def test_list_library_themes_reads_manifest_and_thumbnail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    themes_dir = tmp_path / "themes"
    monkeypatch.setattr(library, "LIBRARY_THEMES_DIR", themes_dir)
    _write_theme(themes_dir, "onepiece", frame_count=5, name="One Piece")

    themes = list_library_themes()

    assert len(themes) == 1
    theme = themes[0]
    assert theme.slug == "onepiece"
    assert theme.name == "One Piece"
    assert theme.frame_count == 5
    assert theme.resolution == (1920, 1080)
    assert theme.thumbnail == theme.directory / "frame1.png"


def test_list_library_themes_skips_corrupt_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    themes_dir = tmp_path / "themes"
    monkeypatch.setattr(library, "LIBRARY_THEMES_DIR", themes_dir)
    _write_theme(themes_dir, "good")

    broken_dir = themes_dir / "broken"
    broken_dir.mkdir()
    (broken_dir / "theme.json").write_text("{not valid json")

    themes = {t.slug for t in list_library_themes()}
    assert themes == {"good"}


def test_delete_library_theme(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    themes_dir = tmp_path / "themes"
    monkeypatch.setattr(library, "LIBRARY_THEMES_DIR", themes_dir)
    theme_dir = _write_theme(themes_dir, "gone")

    assert theme_dir.is_dir()
    delete_library_theme("gone")
    assert not theme_dir.exists()


def test_delete_library_theme_missing_is_a_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(library, "LIBRARY_THEMES_DIR", tmp_path / "themes")
    delete_library_theme("does-not-exist")  # must not raise


def test_sample_preview_frames_natural_sort(tmp_path: Path) -> None:
    """frame2.png must sort before frame10.png (numeric, not lexicographic)."""
    for i in [1, 2, 10, 11]:
        (tmp_path / f"frame{i}.png").write_bytes(b"")

    frames = sample_preview_frames(tmp_path, max_frames=100)

    assert [f.name for f in frames] == ["frame1.png", "frame2.png", "frame10.png", "frame11.png"]


def test_sample_preview_frames_downsamples(tmp_path: Path) -> None:
    for i in range(1, 101):
        (tmp_path / f"frame{i}.png").write_bytes(b"")

    frames = sample_preview_frames(tmp_path, max_frames=10)

    assert len(frames) == 10
    # Still in ascending frame order.
    numbers = [int(f.stem.removeprefix("frame")) for f in frames]
    assert numbers == sorted(numbers)


def test_load_and_save_prefs_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(library, "LIBRARY_DIR", tmp_path)
    monkeypatch.setattr(library, "PREFS_FILE", tmp_path / "prefs.json")

    library.save_prefs(theme_mode="dark")

    assert json.loads((tmp_path / "prefs.json").read_text()) == {"theme_mode": "dark"}
    assert library.load_prefs() == {"theme_mode": "dark"}


def test_load_prefs_missing_file_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(library, "PREFS_FILE", tmp_path / "does-not-exist.json")
    assert library.load_prefs() == {}
