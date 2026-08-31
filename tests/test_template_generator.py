"""Tests for template_generator module."""

from __future__ import annotations

from pathlib import Path

import pytest

from plymotion.template_generator import estimate_loop_seconds, generate_plymouth, generate_script


def test_generate_script(tmp_path: Path) -> None:
    """Script file contains correct frame count and loop."""
    output = tmp_path / "test.script"
    generate_script(output, 100)

    content = output.read_text()
    assert "i < 100" in content
    assert "if (count >= 100)" in content
    assert "count = 0" in content
    assert "Plymouth.SetRefreshFunction" in content
    # Frame paths must be relative to ImageDir ("/frameN.png"), not a
    # baked-in absolute install path — Plymouth's Image() concatenates the
    # given path onto ImageDir, so embedding ImageDir here too would double
    # it up into a path that doesn't exist (silently blank/dark splash).
    assert '"/frame" + (i + 1) + ".png"' in content
    assert "/usr/share/plymouth" not in content
    # Should NOT contain ImageDir (that's for .plymouth)
    assert "ImageDir" not in content


def test_generate_plymouth(tmp_path: Path) -> None:
    """Plymouth config contains theme name and paths."""
    output = tmp_path / "test.plymouth"
    generate_plymouth(output, "mytheme", "/usr/share/plymouth/themes/mytheme",
                      "/usr/share/plymouth/themes/mytheme/test.script")

    content = output.read_text()
    assert "Name=mytheme" in content
    assert "ModuleName=script" in content
    assert "/usr/share/plymouth/themes/mytheme" in content
    assert "test.script" in content


def test_generate_script_single_frame(tmp_path: Path) -> None:
    """Single frame works without loop issues."""
    output = tmp_path / "test.script"
    generate_script(output, 1)

    content = output.read_text()
    assert "i < 1" in content
    assert "count >= 1" in content


def test_estimate_loop_seconds_default_refresh_rate() -> None:
    """Playback time is frame_count / 50Hz, not tied to extraction fps."""
    assert estimate_loop_seconds(150) == 3.0
    assert estimate_loop_seconds(50) == 1.0


def test_estimate_loop_seconds_custom_refresh_rate() -> None:
    """A custom refresh_rate is honored."""
    assert estimate_loop_seconds(100, refresh_rate=25) == 4.0


def test_estimate_loop_seconds_rejects_non_positive_rate() -> None:
    """A zero or negative refresh rate is invalid."""
    with pytest.raises(ValueError):
        estimate_loop_seconds(100, refresh_rate=0)
