"""Tests for login_logo module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

import plymotion.core.installer as installer
import plymotion.core.login_logo as login_logo


class _FakeRun:
    """Captures the pkexec script and the files it would install, without running it."""

    def __init__(self, returncode: int = 0, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.scripts: list[str] = []
        self.installed: dict[str, bytes] = {}

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert argv[:3] == ["pkexec", "bash", "-c"]
        script = argv[3]
        self.scripts.append(script)
        # The temp files the script installs from are deleted once
        # install_logo returns, so snapshot them now.
        for line in script.splitlines():
            if line.startswith("install "):
                src = line.split()[-2]
                self.installed[line.split()[-1]] = Path(src).read_bytes()
        return subprocess.CompletedProcess(argv, self.returncode, stdout="", stderr=self.stderr)


@pytest.fixture
def gdm_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dconf_dir = tmp_path / "gdm" / "dconf"
    dconf_dir.mkdir(parents=True)
    monkeypatch.setattr(login_logo, "GDM_DCONF_DIR", dconf_dir)
    monkeypatch.setattr(login_logo, "DCONF_SNIPPET", dconf_dir / "95-plymotion-logo")
    monkeypatch.setattr(login_logo, "GDM_GENERATE_CONFIG", tmp_path / "gdm" / "generate-config")
    monkeypatch.setattr(login_logo, "LOGO_INSTALL_PATH", tmp_path / "share" / "login-logo.png")
    return tmp_path


def _make_image(path: Path, size: tuple[int, int], mode: str = "RGBA") -> Path:
    color = (255, 255, 255, 0) if mode == "RGBA" else (200, 10, 10)
    Image.new(mode, size, color).save(path)
    return path


def test_prepare_logo_fits_height_and_keeps_aspect(tmp_path: Path) -> None:
    src = _make_image(tmp_path / "big.png", (1000, 400))
    size = login_logo.prepare_logo(src, tmp_path / "out.png", max_height=72)
    assert size == (180, 72)
    with Image.open(tmp_path / "out.png") as out:
        assert out.size == (180, 72)


def test_prepare_logo_caps_width_for_wide_images(tmp_path: Path) -> None:
    src = _make_image(tmp_path / "wide.png", (3000, 100))
    width, height = login_logo.prepare_logo(src, tmp_path / "out.png", max_height=72)
    assert width == login_logo.MAX_LOGO_WIDTH
    assert height < 72


def test_prepare_logo_never_upscales(tmp_path: Path) -> None:
    src = _make_image(tmp_path / "small.png", (40, 20))
    assert login_logo.prepare_logo(src, tmp_path / "out.png", max_height=72) == (40, 20)


def test_prepare_logo_outputs_png_with_alpha(tmp_path: Path) -> None:
    """GDM draws over a dark background, so transparency must survive, and
    non-PNG sources (e.g. JPEG) are converted."""
    src = _make_image(tmp_path / "logo.jpg", (100, 50), mode="RGB")
    out = tmp_path / "out.png"
    login_logo.prepare_logo(src, out)
    with Image.open(out) as img:
        assert img.format == "PNG"
        assert img.mode == "RGBA"


def test_install_logo_writes_image_and_dconf_snippet(
    gdm_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    src = _make_image(gdm_dirs / "logo.png", (500, 200))

    size = login_logo.install_logo(src, max_height=72)

    assert size == (180, 72)
    assert len(fake_run.scripts) == 1
    script = fake_run.scripts[0]
    assert script.startswith("set -e")
    assert str(login_logo.GDM_GENERATE_CONFIG) in script

    snippet = fake_run.installed[str(login_logo.DCONF_SNIPPET)].decode()
    assert "[org/gnome/login-screen]" in snippet
    assert f"logo='{login_logo.LOGO_INSTALL_PATH}'" in snippet

    logo_png = gdm_dirs / "installed.png"
    logo_png.write_bytes(fake_run.installed[str(login_logo.LOGO_INSTALL_PATH)])
    with Image.open(logo_png) as img:
        assert img.size == (180, 72)


def test_install_logo_requires_gdm(gdm_dirs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(login_logo, "GDM_DCONF_DIR", gdm_dirs / "missing")
    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    src = _make_image(gdm_dirs / "logo.png", (100, 50))

    with pytest.raises(RuntimeError, match="GDM not found"):
        login_logo.install_logo(src)
    assert fake_run.scripts == []


def test_install_logo_raises_with_pkexec_stderr(
    gdm_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(installer.subprocess, "run", _FakeRun(returncode=126, stderr="denied"))
    src = _make_image(gdm_dirs / "logo.png", (100, 50))

    with pytest.raises(RuntimeError, match="denied"):
        login_logo.install_logo(src)


def test_restore_default_logo_removes_override(
    gdm_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_run = _FakeRun()
    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    login_logo.restore_default_logo()

    script = fake_run.scripts[0]
    assert f"rm -f {login_logo.DCONF_SNIPPET} {login_logo.LOGO_INSTALL_PATH}" in script
    assert str(login_logo.GDM_GENERATE_CONFIG) in script


def test_is_custom_logo_installed(gdm_dirs: Path) -> None:
    assert not login_logo.is_custom_logo_installed()
    login_logo.DCONF_SNIPPET.write_text("[org/gnome/login-screen]\n")
    assert login_logo.is_custom_logo_installed()


def test_distro_default_logo_last_override_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(login_logo, "SCHEMA_OVERRIDES_DIR", tmp_path)
    (tmp_path / "10_distro.gschema.override").write_text(
        "[org.gnome.login-screen]\nlogo='/usr/share/pixmaps/distro.svg'\n"
    )
    (tmp_path / "20_site.gschema.override").write_text(
        "[org.gnome.login-screen]\nlogo='/opt/site-logo.png'\n"
    )
    (tmp_path / "30_other.gschema.override").write_text("[org.gnome.desktop.interface]\nx=1\n")

    assert login_logo.distro_default_logo() == Path("/opt/site-logo.png")


def test_distro_default_logo_none_without_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(login_logo, "SCHEMA_OVERRIDES_DIR", tmp_path)
    assert login_logo.distro_default_logo() is None


def test_previewable_path_prefers_png_sibling_of_svg(tmp_path: Path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg/>")
    assert login_logo.previewable_path(svg) is None
    png = _make_image(tmp_path / "logo.png", (10, 10))
    assert login_logo.previewable_path(svg) == png
