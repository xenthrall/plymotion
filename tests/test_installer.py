"""Tests for installer module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

import plymotion.installer as installer
from plymotion.installer import (
    activate_theme,
    install_theme,
    list_installed_themes,
    preview_installed_theme,
    reset_to_default,
    restore_backup,
    uninstall_theme,
    validate_theme,
)


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


class _FakeRun:
    """Captures the argv passed to subprocess.run, without executing anything."""

    def __init__(self, returncode: int = 0, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        return subprocess.CompletedProcess(argv, self.returncode, stdout="", stderr=self.stderr)

    @property
    def script(self) -> str:
        """The bash -c script from the sole captured pkexec call."""
        assert len(self.calls) == 1
        argv = self.calls[0]
        assert argv[:2] == ["pkexec", "bash"]
        assert argv[2] == "-c"
        return argv[3]


def test_install_theme_runs_privileged_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """install_theme validates locally, then does everything else as one pkexec script."""
    source = tmp_path / "source"
    source.mkdir()
    _make_theme(source)

    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    monkeypatch.setattr(installer, "THEMES_DIR", tmp_path / "themes")
    monkeypatch.setattr(installer, "BACKUP_DIR", tmp_path / "backups")

    install_theme(source, theme_name="mytheme", priority=100)

    script = fake_run.script
    assert "mkdir -p" in script
    assert str(tmp_path / "backups") in script
    assert f"cp -r {source}" in script
    assert str(tmp_path / "themes" / "mytheme") in script
    assert "update-alternatives --install" in script
    assert "default.plymouth" in script
    assert "100" in script
    assert "update-initramfs -u" in script


def test_install_theme_rejects_invalid_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An invalid theme is rejected before any privileged command runs."""
    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    with pytest.raises(ValueError):
        install_theme(tmp_path, theme_name="mytheme")

    assert fake_run.calls == []


def test_install_theme_raises_with_pkexec_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pkexec/script failure surfaces its stderr as the exception message."""
    source = tmp_path / "source"
    source.mkdir()
    _make_theme(source)

    fake_run = _FakeRun(returncode=1, stderr="Authorization failed")
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    monkeypatch.setattr(installer, "THEMES_DIR", tmp_path / "themes")
    monkeypatch.setattr(installer, "BACKUP_DIR", tmp_path / "backups")

    with pytest.raises(RuntimeError, match="Authorization failed"):
        install_theme(source, theme_name="mytheme")


def test_restore_backup_without_existing_backup_is_a_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """restore_backup returns False and never touches the system if there's no backup."""
    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    monkeypatch.setattr(installer, "BACKUP_DIR", tmp_path / "backups")

    assert restore_backup("mytheme") is False
    assert fake_run.calls == []


def test_restore_backup_runs_privileged_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """restore_backup copies the backup over the theme dir and updates initramfs."""
    backup_dir = tmp_path / "backups"
    (backup_dir / "mytheme").mkdir(parents=True)

    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    monkeypatch.setattr(installer, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(installer, "THEMES_DIR", tmp_path / "themes")

    assert restore_backup("mytheme") is True

    script = fake_run.script
    assert str(backup_dir / "mytheme") in script
    assert str(tmp_path / "themes" / "mytheme") in script
    assert "update-initramfs -u" in script


def test_reset_to_default_runs_privileged_script(monkeypatch: pytest.MonkeyPatch) -> None:
    """reset_to_default points update-alternatives at the text theme."""
    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    reset_to_default()

    script = fake_run.script
    assert "update-alternatives --set default.plymouth" in script
    assert str(installer.TEXT_THEME_PLYMOUTH) in script
    assert "update-initramfs -u" in script


def test_list_installed_themes_empty_when_dir_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing THEMES_DIR yields an empty list instead of raising."""
    monkeypatch.setattr(installer, "THEMES_DIR", tmp_path / "does-not-exist")
    assert list_installed_themes() == []


def test_list_installed_themes_marks_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Themes are listed with parsed name/description, and the default is flagged."""
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()

    spinner_dir = themes_dir / "spinner"
    spinner_dir.mkdir()
    (spinner_dir / "spinner.plymouth").write_text(
        "[Plymouth Theme]\nName=Spinner\nDescription=A spinner theme\nModuleName=script\n"
    )

    mine_dir = themes_dir / "mytheme"
    mine_dir.mkdir()
    (mine_dir / "mytheme.plymouth").write_text(
        "[Plymouth Theme]\nName=My Theme\nDescription=Custom\nModuleName=script\n"
    )

    (themes_dir / "default.plymouth").symlink_to(mine_dir / "mytheme.plymouth")

    monkeypatch.setattr(installer, "THEMES_DIR", themes_dir)
    themes = {t.name: t for t in list_installed_themes()}

    assert set(themes) == {"Spinner", "My Theme"}
    assert themes["My Theme"].is_default is True
    assert themes["Spinner"].is_default is False
    assert themes["Spinner"].description == "A spinner theme"


def test_list_installed_themes_skips_unparseable_plymouth_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A corrupt/missing-section .plymouth file is skipped, not fatal."""
    themes_dir = tmp_path / "themes"
    broken_dir = themes_dir / "broken"
    broken_dir.mkdir(parents=True)
    (broken_dir / "broken.plymouth").write_text("not an ini section at all")

    monkeypatch.setattr(installer, "THEMES_DIR", themes_dir)
    assert list_installed_themes() == []


def _make_installed_theme(themes_dir: Path, dir_name: str) -> Path:
    theme_dir = themes_dir / dir_name
    theme_dir.mkdir(parents=True)
    plymouth_file = theme_dir / f"{dir_name}.plymouth"
    plymouth_file.write_text(f"[Plymouth Theme]\nName={dir_name}\nModuleName=script\n")
    return plymouth_file


def test_activate_theme_runs_privileged_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """activate_theme only flips default.plymouth + rebuilds initramfs, no copy."""
    themes_dir = tmp_path / "themes"
    plymouth_file = _make_installed_theme(themes_dir, "mytheme")

    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    monkeypatch.setattr(installer, "THEMES_DIR", themes_dir)

    activate_theme("mytheme")

    script = fake_run.script
    assert f"update-alternatives --set default.plymouth {plymouth_file}" in script
    assert "update-initramfs -u" in script
    assert "cp -r" not in script


def test_activate_theme_rejects_unknown_theme(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    monkeypatch.setattr(installer, "THEMES_DIR", tmp_path / "themes")

    with pytest.raises(ValueError):
        activate_theme("does-not-exist")
    assert fake_run.calls == []


def test_uninstall_theme_runs_privileged_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    themes_dir = tmp_path / "themes"
    plymouth_file = _make_installed_theme(themes_dir, "mytheme")

    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    monkeypatch.setattr(installer, "THEMES_DIR", themes_dir)

    uninstall_theme("mytheme")

    script = fake_run.script
    assert f"update-alternatives --remove default.plymouth {plymouth_file}" in script
    assert f"rm -rf {themes_dir / 'mytheme'}" in script
    assert "update-initramfs -u" in script
    assert "update-alternatives --set default.plymouth" in script  # the conditional fallback


def test_uninstall_theme_rejects_unknown_theme(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    monkeypatch.setattr(installer, "THEMES_DIR", tmp_path / "themes")

    with pytest.raises(ValueError):
        uninstall_theme("does-not-exist")
    assert fake_run.calls == []


def test_uninstall_theme_refuses_text_theme(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    with pytest.raises(ValueError, match="text theme"):
        uninstall_theme("text")
    assert fake_run.calls == []


def test_preview_installed_theme_runs_privileged_script(monkeypatch: pytest.MonkeyPatch) -> None:
    """preview_installed_theme drives plymouthd/plymouth through pkexec."""
    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    preview_installed_theme(seconds=9)

    script = fake_run.script
    assert "plymouthd --no-daemon --debug" in script
    assert "plymouth --show-splash" in script
    assert "sleep 9" in script
    assert "plymouth --quit" in script
