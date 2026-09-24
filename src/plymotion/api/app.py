"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from plymotion import __version__
from plymotion.api.config import SESSION_COOKIE, ApiConfig
from plymotion.api.deps import ApiException
from plymotion.api.dialogs import FileDialogs, default_dialogs
from plymotion.api.routers import (
    convert,
    files,
    jobs,
    library,
    login_logo,
    meta,
    prefs,
    sequences,
    system,
)
from plymotion.api.security import SecurityMiddleware, token_matches
from plymotion.jobs import JobBusy, JobManager

_NOT_BUILT = """<!doctype html><meta charset="utf-8"><title>Plymotion</title>
<body style="font:15px system-ui;background:#0b0b10;color:#e4e4ea;
display:grid;place-items:center;height:100vh;margin:0">
<div style="max-width:32rem"><h2>El cliente web no está compilado</h2>
<p>Ejecuta <code>npm --prefix frontend install &amp;&amp; npm --prefix frontend run build</code>
y vuelve a abrir Plymotion, o usa <code>plymotion --dev</code> con
<code>npm run dev</code>.</p></div>"""


def _error(status: int, code: str, message: str, detail: object = None) -> JSONResponse:
    return JSONResponse({"code": code, "message": message, "detail": detail}, status_code=status)


def create_app(
    config: ApiConfig,
    *,
    dialogs: FileDialogs | None = None,
    desktop: bool = False,
    job_manager: JobManager | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        app.state.jobs.shutdown()

    app = FastAPI(
        title="Plymotion API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs" if config.dev else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if config.dev else None,
    )
    app.state.config = config
    app.state.jobs = job_manager or JobManager()
    app.state.dialogs = dialogs if dialogs is not None else default_dialogs()
    app.state.desktop = desktop
    app.add_middleware(SecurityMiddleware, config=config)

    @app.exception_handler(ApiException)
    async def api_exception(_request: Request, exc: ApiException) -> JSONResponse:
        return _error(exc.status, exc.code, exc.message, exc.detail)

    @app.exception_handler(JobBusy)
    async def job_busy(_request: Request, exc: JobBusy) -> JSONResponse:
        return _error(409, "busy", f"Espera a que termine: {exc.running.title}.",
                      {"job_id": exc.running.id})

    @app.exception_handler(RequestValidationError)
    async def validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", [])[1:])
        message = f"{field}: {first.get('msg', 'valor inválido')}" if field else "Datos inválidos."
        return _error(422, "validation", message, exc.errors())

    @app.exception_handler(StarletteHTTPException)
    async def http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error(exc.status_code, "http_error", str(exc.detail))

    for module in (meta, jobs, files, convert, library, system, login_logo, sequences, prefs):
        app.include_router(module.router, prefix="/api")

    @app.get("/auth", include_in_schema=False)
    def auth(token: str, next: str = "/") -> Response:
        if not token_matches(config, token):
            return HTMLResponse("Token inválido. Abre Plymotion de nuevo.", status_code=401)
        # Only same-origin paths: never an open redirect to another site.
        target = next if next.startswith("/") and not next.startswith("//") else "/"
        response = RedirectResponse(target, status_code=303)
        response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict", path="/")
        return response

    static_dir = config.static_dir
    index = static_dir / "index.html" if static_dir else None

    @app.get("/{path:path}", include_in_schema=False)
    def client(path: str) -> Response:
        """Serve the built client, falling back to index.html for client-side routes."""
        if path.startswith("api/"):
            return _error(404, "not_found", "Ruta de la API inexistente.")
        if static_dir is None or index is None or not index.is_file():
            return HTMLResponse(_NOT_BUILT)
        candidate = (static_dir / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(static_dir.resolve()):
            hashed = path.startswith("assets/")
            cache = "public, max-age=31536000, immutable" if hashed else "no-cache"
            return FileResponse(candidate, headers={"Cache-Control": cache})
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return app
