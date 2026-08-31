"""Tests for template_generator module."""

from __future__ import annotations

from pathlib import Path

from plymotion.template_generator import generate_plymouth, generate_script


def test_generate_script(tmp_path: Path) -> None:
    """Script file contains correct frame count and loop."""
    output = tmp_path / "test.script"
    generate_script(output, 100, "/usr/share/plymouth/themes/plymotion")

    content = output.read_text()
    assert "i < 100" in content
    assert "if (count >= 100)" in content
    assert "count = 0" in content
    assert "Plymouth.SetRefreshFunction" in content
    assert "/usr/share/plymouth/themes/plymotion/frame" in content
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
    generate_script(output, 1, "/frames")

    content = output.read_text()
    assert "i < 1" in content
    assert "count >= 1" in content
