"""Runtime configuration for one API server instance."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from pathlib import Path

SESSION_COOKIE = "plymotion_session"
DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "web"
VITE_DEV_PORT = 5173


@dataclass
class ApiConfig:
    """`port` is the one the server listens on; hosts/origins are derived from it.

    `dev` additionally trusts the Vite dev server's origin, which proxies
    /api and /auth to this server during frontend development.
    """

    port: int
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    dev: bool = False
    static_dir: Path | None = DEFAULT_STATIC_DIR

    @property
    def allowed_hosts(self) -> set[str]:
        hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}
        if self.dev:
            hosts |= {f"127.0.0.1:{VITE_DEV_PORT}", f"localhost:{VITE_DEV_PORT}"}
        return hosts

    @property
    def allowed_origins(self) -> set[str]:
        return {f"http://{host}" for host in self.allowed_hosts}

    def auth_url(self, base: str | None = None) -> str:
        return f"{base or f'http://127.0.0.1:{self.port}'}/auth?token={self.token}"
