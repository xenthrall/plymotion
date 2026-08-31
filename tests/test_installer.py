"""Tests for installer module."""

from __future__ import annotations

from pathlib import Path

from plymotion.installer import validate_theme


def _make_theme(directory: Path, *, with_script: bool = True, with_frames: bool = True) -> None:
    """Helper to create a minimal valid theme."""
    config = directory / "test.plymouth"
    config.write_text(
        "[Plymouth Theme]\n"
        "Name=test\n"
        "ModuleName=script\n"
        "\n"
        "[script]\n"
        "ImageDir=/test\n"
        "ScriptFile=/test/test.script\n"
    )
    if with_script:
        script = directory / "test.script"
        script.write_text("sprite = Sprite(Image('/test/frame1.png'));\n")
    if with_frames:
        frame = directory / "frame1.png"
        frame.write_bytes(b"\x89PNG\r\n\x1a\n")


def test_validate_valid_theme(tmp_path: Path) -> None:
    """Valid theme passes validation."""
    _make_theme(tmp_path)
    errors = validate_theme(tmp_path)
    assert errors == []


def test_validate_no_plymouth(tmp_path: Path) -> None:
    """Missing .plymouth config is detected."""
    errors = validate_theme(tmp_path)
    assert any("plymouth" in e.lower() for e in errors)


def test_validate_no_script(tmp_path: Path) -> None:
    """Missing .script file is detected."""
    (tmp_path / "test.plymouth").write_text(
        "[Plymouth Theme]\nName=test\nModuleName=script\n"
        "[script]\nImageDir=/test\nScriptFile=/test/test.script\n"
    )
    errors = validate_theme(tmp_path)
    assert any("script" in e.lower() for e in errors)


def test_validate_empty_script(tmp_path: Path) -> None:
    """Empty script file is detected."""
    (tmp_path / "test.plymouth").write_text(
        "[Plymouth Theme]\nName=test\nModuleName=script\n"
        "[script]\nImageDir=/test\nScriptFile=/test/test.script\n"
    )
    (tmp_path / "test.script").touch()
    errors = validate_theme(tmp_path)
    assert any("empty" in e.lower() for e in errors)


def test_validate_no_frames(tmp_path: Path) -> None:
    """Missing frame images are detected."""
    _make_theme(tmp_path, with_frames=False)
    errors = validate_theme(tmp_path)
    assert any("frame" in e.lower() for e in errors)
