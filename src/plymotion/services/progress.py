"""Progress reporting contract between services and whoever runs them."""

from __future__ import annotations

from typing import Protocol


class Cancelled(Exception):
    """Raised from Reporter.check_cancelled() when the caller asked to stop."""


class Reporter(Protocol):
    def progress(self, percent: float | None, stage: str | None = None) -> None:
        """Report overall progress (0-100, None = indeterminate) and the current stage."""

    def log(self, message: str) -> None:
        """Append a human-readable line to the operation's log."""

    def check_cancelled(self) -> None:
        """Raise Cancelled if the operation should stop at this point."""


class NullReporter:
    """Reporter that ignores everything; the default for direct calls and tests."""

    def progress(self, percent: float | None, stage: str | None = None) -> None:
        pass

    def log(self, message: str) -> None:
        pass

    def check_cancelled(self) -> None:
        pass
