"""Shared state and helpers passed to every view builder in ui/views/."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import flet as ft


@dataclass
class AppContext:
    """Cross-view plumbing owned by ui/app.py: shared log/status, the single
    busy gate that keeps privileged (pkexec) actions from overlapping, and
    refresh hooks views register so completing an action in one view (e.g.
    converting, or installing from the gallery) updates another."""

    page: ft.Page
    log: Callable[[str], None]
    notify: Callable[[str], None]
    set_status: Callable[[str], None]
    confirm_action: Callable[[str, str, str, Callable[[], None]], None]
    is_busy: Callable[[], bool]
    set_busy: Callable[[bool], None]
    busy_listeners: list[Callable[[bool], None]] = field(default_factory=list)
    refresh_gallery: Callable[[], None] = lambda: None
    refresh_system: Callable[[], None] = lambda: None
    switch_view: Callable[[int], None] = lambda index: None
    load_video_into_convert: Callable[[str], None] = lambda path: None

    def on_busy_change(self, listener: Callable[[bool], None]) -> None:
        """Register a callback invoked whenever the shared busy gate flips.

        Used by views to disable their own action buttons while any
        privileged (pkexec) action started from any view is in flight.
        """
        self.busy_listeners.append(listener)
