"""Protection for a localhost server that can trigger root actions (pkexec).

Any web page the user has open could otherwise POST to it (CSRF) or reach
it through a hostname it controls (DNS rebinding). Defenses, all enforced
by SecurityMiddleware:

- Host must be this server's own 127.0.0.1/localhost:port (DNS rebinding).
- /api/* requires the per-launch session token, delivered once through
  /auth?token=... and then kept in an HttpOnly SameSite=Strict cookie, so
  cross-site requests never carry it (CSRF) and page JS can't read it.
- State-changing requests must carry an allowed Origin when one is sent,
  plus the X-Plymotion header, which a cross-site form can't add.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send

from plymotion.api.config import SESSION_COOKIE, ApiConfig

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "x-plymotion"


def _headers(scope: Scope) -> dict[str, str]:
    return {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}


def _cookie(headers: dict[str, str], name: str) -> str | None:
    for part in headers.get("cookie", "").split(";"):
        key, _, value = part.strip().partition("=")
        if key == name:
            return value
    return None


def token_matches(config: ApiConfig, candidate: str | None) -> bool:
    return candidate is not None and secrets.compare_digest(candidate, config.token)


class SecurityMiddleware:
    def __init__(self, app: ASGIApp, config: ApiConfig) -> None:
        self.app = app
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = _headers(scope)
        if headers.get("host") not in self.config.allowed_hosts:
            await _deny(send, 403, "bad_host", "Host no permitido.")
            return

        path: str = scope["path"]
        if path.startswith("/api/"):
            if not token_matches(self.config, _cookie(headers, SESSION_COOKIE)):
                await _deny(send, 401, "unauthorized", "Sesión inválida: abre Plymotion de nuevo.")
                return
            if scope["method"] not in SAFE_METHODS:
                origin = headers.get("origin")
                if origin is not None and origin not in self.config.allowed_origins:
                    await _deny(send, 403, "bad_origin", "Origen no permitido.")
                    return
                if headers.get(CSRF_HEADER) != "1":
                    await _deny(send, 403, "csrf", "Falta el header X-Plymotion.")
                    return

        await self.app(scope, receive, send)


async def _deny(send: Send, status: int, code: str, message: str) -> None:
    body: dict[str, Any] = {"code": code, "message": message}
    payload = json.dumps(body).encode()
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode())],
    })
    await send({"type": "http.response.body", "body": payload})
