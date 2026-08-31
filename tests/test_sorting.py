"""Tests for the natural filename sort helper."""

from __future__ import annotations

from pathlib import Path

from plymotion.sorting import natural_sort_key


def test_natural_sort_numeric_order() -> None:
    names = ["frame10.png", "frame2.png", "frame1.png"]
    paths = [Path(n) for n in names]

    ordered = sorted(paths, key=natural_sort_key)

    assert [p.name for p in ordered] == ["frame1.png", "frame2.png", "frame10.png"]


def test_natural_sort_ignores_prefix_differences() -> None:
    """A digit run elsewhere in the name doesn't confuse the trailing counter."""
    names = ["v2-frame10.png", "v2-frame2.png", "v2-frame1.png"]
    paths = [Path(n) for n in names]

    ordered = sorted(paths, key=natural_sort_key)

    assert [p.name for p in ordered] == ["v2-frame1.png", "v2-frame2.png", "v2-frame10.png"]


def test_natural_sort_case_insensitive() -> None:
    paths = [Path("Img2.png"), Path("img10.png"), Path("IMG1.png")]

    ordered = sorted(paths, key=natural_sort_key)

    assert [p.name for p in ordered] == ["IMG1.png", "Img2.png", "img10.png"]
