"""Request/response models. These define the OpenAPI schema the web client is generated from."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from plymotion.core.frame_processor import DEFAULT_COLORS


class ApiError(BaseModel):
    code: str
    message: str
    detail: Any = None


# -- meta ------------------------------------------------------------------


class Capabilities(BaseModel):
    ffmpeg: bool
    pkexec: bool
    gdm: bool
    native_dialogs: bool
    desktop: bool


class SystemInfo(BaseModel):
    distro: str
    kernel: str
    default_theme: str | None
    initramfs_tool: str | None


class Meta(BaseModel):
    version: str
    capabilities: Capabilities
    system: SystemInfo
    data_dir: str
    busy_locks: dict[str, str]


# -- jobs ------------------------------------------------------------------

JobStateName = Literal["running", "succeeded", "failed", "cancelled"]


class JobInfo(BaseModel):
    id: str
    kind: str
    title: str
    state: JobStateName
    progress: float | None
    stage: str | None
    result: Any = None
    error: str | None
    cancellable: bool
    created_at: str
    finished_at: str | None
    log_tail: list[str]


class JobDetail(JobInfo):
    logs: list[str]


class JobAccepted(BaseModel):
    job: JobInfo


# -- files & dialogs -------------------------------------------------------

DialogKind = Literal["video", "image", "images"]


class PickRequest(BaseModel):
    kind: DialogKind


class PickResult(BaseModel):
    paths: list[str]


class PathRequest(BaseModel):
    path: str


# -- conversion ------------------------------------------------------------


class VideoInfo(BaseModel):
    path: str
    name: str
    width: int
    height: int
    duration: float
    fps: float | None
    codec: str
    size_bytes: int
    media_url: str


class EstimateRequest(BaseModel):
    duration: float = Field(ge=0)
    fps: int = Field(ge=1, le=120)
    trim_start: float = Field(default=0, ge=0)
    trim_duration: float | None = Field(default=None, gt=0)


class Estimate(BaseModel):
    frame_count: int
    loop_seconds: float
    refresh_rate: int


class ConvertRequest(BaseModel):
    path: str
    name: str = Field(min_length=1, max_length=80)
    max_width: int = Field(default=320, ge=16, le=7680)
    max_height: int = Field(default=240, ge=16, le=4320)
    fps: int = Field(default=30, ge=1, le=120)
    colors: int = Field(default=DEFAULT_COLORS, ge=2, le=256)
    trim_start: float = Field(default=0, ge=0)
    trim_duration: float | None = Field(default=None, gt=0)


# -- library ---------------------------------------------------------------


class LibraryTheme(BaseModel):
    slug: str
    name: str
    frame_count: int
    width: int
    height: int
    fps: int
    colors: int
    loop_seconds: float
    total_bytes: int
    source_video: str
    created_at: str
    installed: bool
    thumbnail_url: str | None
    frame_url_template: str


# -- system ----------------------------------------------------------------


class InstalledTheme(BaseModel):
    dir_name: str
    name: str
    description: str
    is_default: bool
    is_plymotion: bool
    has_backup: bool
    frame_count: int
    thumbnail_url: str | None
    frame_url_template: str | None


class PreviewRequest(BaseModel):
    seconds: int = Field(default=6, ge=2, le=30)


class RestoreBackupRequest(BaseModel):
    theme: str


# -- login logo ------------------------------------------------------------


class LoginLogoState(BaseModel):
    gdm_available: bool
    custom_installed: bool
    current_url: str | None
    default_height: int
    max_width: int


class LogoPreviewRequest(BaseModel):
    path: str
    max_height: int = Field(default=72, ge=16, le=400)


class LogoPreview(BaseModel):
    url: str
    width: int
    height: int


# -- sequences -------------------------------------------------------------


class SequenceRequest(BaseModel):
    images: list[str] = Field(min_length=1)
    name: str = Field(min_length=1, max_length=80)
    format: Literal["mp4", "gif"] = "mp4"
    fps: int = Field(default=24, ge=1, le=120)
    max_width: int | None = Field(default=None, ge=16, le=7680)


class SequenceOutput(BaseModel):
    filename: str
    path: str
    size_bytes: int
    created_at: str
    url: str


# -- prefs -----------------------------------------------------------------


class Prefs(BaseModel):
    theme: Literal["system", "light", "dark"] = "system"
    accent: str = "violet"
    sidebar_collapsed: bool = False
    convert_defaults: dict[str, Any] = Field(default_factory=dict)


class PrefsPatch(BaseModel):
    theme: Literal["system", "light", "dark"] | None = None
    accent: str | None = None
    sidebar_collapsed: bool | None = None
    convert_defaults: dict[str, Any] | None = None
