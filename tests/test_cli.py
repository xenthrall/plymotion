"""Tests for CLI module."""

from __future__ import annotations

from typer.testing import CliRunner

from plymotion.cli import app

runner = CliRunner()


def test_help() -> None:
    """CLI shows help text."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Plymouth boot splash" in result.output


def test_version() -> None:
    """CLI shows version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_convert_no_video_shows_error() -> None:
    """Convert command requires video input."""
    result = runner.invoke(app, ["convert"])
    assert result.exit_code != 0
