"""Application and host capabilities."""

from __future__ import annotations

import platform
import shutil
from pathlib import Path

from fastapi import APIRouter, Request

from plymotion import __version__
from plymotion.api.deps import jobs
from plymotion.api.schemas import Capabilities, Meta, SystemInfo
from plymotion.core import installer, library, login_logo
from plymotion.core.video_extractor import ffmpeg_available

router = APIRouter(tags=["meta"])


def _distro() -> str:
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return platform.system()


def _initramfs_tool() -> str | None:
    # See docs/plymouth-ubuntu-gnome.md §4: recent Ubuntu builds the
    # initramfs with dracut even though update-initramfs still exists.
    if shutil.which("dracut") and not shutil.which("mkinitramfs"):
        return "dracut"
    if shutil.which("mkinitramfs"):
        return "initramfs-tools"
    return None


@router.get("/meta", response_model=Meta)
def get_meta(request: Request) -> Meta:
    return Meta(
        version=__version__,
        capabilities=Capabilities(
            ffmpeg=ffmpeg_available(),
            pkexec=shutil.which("pkexec") is not None,
            gdm=login_logo.gdm_available(),
            native_dialogs=request.app.state.dialogs is not None,
            desktop=request.app.state.desktop,
        ),
        system=SystemInfo(
            distro=_distro(),
            kernel=platform.release(),
            default_theme=installer.current_default_theme_dir_name(),
            initramfs_tool=_initramfs_tool(),
        ),
        data_dir=str(library.LIBRARY_DIR),
        busy_locks=jobs(request).busy_locks(),
    )
