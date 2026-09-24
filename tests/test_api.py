"""Tests for the FastAPI layer: security, jobs and every router."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import plymotion.core.installer as installer
import plymotion.core.library as library
import plymotion.services.convert as convert_service
from plymotion.api import ApiConfig, create_app
from plymotion.api.config import SESSION_COOKIE

PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
HEADERS = {"X-Plymotion": "1"}


class FakeDialogs:
    def __init__(self, paths: list[str]) -> None:
        self.paths = paths

    def pick(self, kind: str) -> list[str]:
        return self.paths


@pytest.fixture
def config(tmp_path: Path) -> ApiConfig:
    return ApiConfig(port=PORT, token="secret-token", static_dir=tmp_path / "web")


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(library, "LIBRARY_DIR", tmp_path / "data")
    monkeypatch.setattr(library, "LIBRARY_THEMES_DIR", tmp_path / "data" / "themes")
    monkeypatch.setattr(library, "PREFS_FILE", tmp_path / "data" / "prefs.json")
    monkeypatch.setattr(installer, "THEMES_DIR", tmp_path / "system-themes")
    monkeypatch.setattr(installer, "BACKUP_DIR", tmp_path / "backups")
    (tmp_path / "system-themes").mkdir()
    return tmp_path


@pytest.fixture
def client(config: ApiConfig, env: Path) -> TestClient:
    app = create_app(config, dialogs=FakeDialogs(["/tmp/a.mp4"]))
    with TestClient(app, base_url=BASE) as test_client:
        test_client.cookies.set(SESSION_COOKIE, config.token)
        yield test_client


def wait_job(client: TestClient, job_id: str, timeout: float = 5) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["state"] != "running":
            return job
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def make_library_theme(root: Path, slug: str = "demo", frames: int = 3) -> Path:
    theme_dir = root / "data" / "themes" / slug
    theme_dir.mkdir(parents=True)
    for i in range(1, frames + 1):
        Image.new("RGB", (8, 8)).save(theme_dir / f"frame{i}.png")
    (theme_dir / f"{slug}.plymouth").write_text(
        "[Plymouth Theme]\nName=Demo\nModuleName=script\n[script]\nImageDir=/x\nScriptFile=/x/s\n"
    )
    (theme_dir / f"{slug}.script").write_text("x")
    library.save_manifest(theme_dir, name="Demo", frame_count=frames, resolution=[8, 8], fps=30,
                          loop_seconds=0.06, created_at="2026-01-01T00:00:00+00:00")
    return theme_dir


# -- security ----------------------------------------------------------------


def test_api_requires_session_cookie(config: ApiConfig, env: Path) -> None:
    with TestClient(create_app(config), base_url=BASE) as anon:
        assert anon.get("/api/meta").status_code == 401


def test_auth_sets_cookie_and_redirects(config: ApiConfig, env: Path) -> None:
    with TestClient(create_app(config), base_url=BASE) as anon:
        response = anon.get("/auth", params={"token": config.token}, follow_redirects=False)
        assert response.status_code == 303
        assert "samesite=strict" in response.headers["set-cookie"].lower()
        assert "httponly" in response.headers["set-cookie"].lower()
        assert anon.get("/api/meta").status_code == 200
        assert anon.get("/auth", params={"token": "wrong"}).status_code == 401


def test_rejects_foreign_host(config: ApiConfig, env: Path) -> None:
    with TestClient(create_app(config), base_url="http://evil.example:8765") as evil:
        evil.cookies.set(SESSION_COOKIE, config.token)
        assert evil.get("/api/meta").status_code == 403


def test_unsafe_requests_need_csrf_header_and_same_origin(client: TestClient) -> None:
    assert client.patch("/api/prefs", json={"theme": "dark"}).status_code == 403
    foreign = {**HEADERS, "Origin": "https://evil.example"}
    assert client.patch("/api/prefs", json={"theme": "dark"}, headers=foreign).status_code == 403
    same = {**HEADERS, "Origin": BASE}
    assert client.patch("/api/prefs", json={"theme": "dark"}, headers=same).status_code == 200


def test_dev_mode_trusts_vite_origin(tmp_path: Path, env: Path) -> None:
    cfg = ApiConfig(port=PORT, token="t", dev=True, static_dir=None)
    with TestClient(create_app(cfg), base_url=BASE) as dev:
        dev.cookies.set(SESSION_COOKIE, "t")
        headers = {**HEADERS, "Origin": "http://localhost:5173"}
        assert dev.patch("/api/prefs", json={"theme": "light"}, headers=headers).status_code == 200
        assert dev.get("/api/openapi.json").status_code == 200


# -- meta, prefs, client -------------------------------------------------------


def test_meta(client: TestClient) -> None:
    body = client.get("/api/meta").json()
    assert body["capabilities"]["native_dialogs"] is True
    assert body["version"]


def test_prefs_roundtrip(client: TestClient) -> None:
    assert client.get("/api/prefs").json()["theme"] == "system"
    patched = client.patch("/api/prefs", json={"sidebar_collapsed": True}, headers=HEADERS).json()
    assert patched["sidebar_collapsed"] is True
    assert client.get("/api/prefs").json()["sidebar_collapsed"] is True


def test_client_fallback_when_not_built(client: TestClient) -> None:
    assert "no está compilado" in client.get("/").text


def test_client_serves_spa(client: TestClient, config: ApiConfig) -> None:
    assert config.static_dir is not None
    (config.static_dir / "assets").mkdir(parents=True)
    (config.static_dir / "index.html").write_text("<html>app</html>")
    (config.static_dir / "assets" / "a.js").write_text("js")
    assert client.get("/galeria").text == "<html>app</html>"
    assert client.get("/assets/a.js").text == "js"
    assert client.get("/api/nope").status_code == 404


def test_pick_uses_dialog_provider(client: TestClient) -> None:
    response = client.post("/api/dialogs/pick", json={"kind": "video"}, headers=HEADERS)
    assert response.json() == {"paths": ["/tmp/a.mp4"]}


# -- convert -------------------------------------------------------------------


def test_convert_job_end_to_end(
    client: TestClient, env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    video = env / "clip.mp4"
    video.write_bytes(b"x")

    def fake_extract(_video: Path, out_dir: Path, **_kw: Any) -> int:
        out_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, 5):
            Image.new("RGB", (40, 30), (i * 40, 0, 0)).save(out_dir / f"frame{i}.png")
        return 4

    monkeypatch.setattr(convert_service, "extract_frames", fake_extract)
    response = client.post("/api/convert", json={"path": str(video), "name": "Mi tema"},
                           headers=HEADERS)
    assert response.status_code == 202
    job = wait_job(client, response.json()["job"]["id"])
    assert job["state"] == "succeeded", job
    assert job["result"]["slug"] == "mi-tema"
    assert any("frames extraídos" in line for line in job["logs"])

    gallery = client.get("/api/library").json()
    assert [t["slug"] for t in gallery] == ["mi-tema"]
    frame = client.get("/api/library/mi-tema/frames/4")
    assert frame.status_code == 200 and frame.headers["content-type"] == "image/png"
    assert client.get("/api/library/mi-tema/frames/5").status_code == 404


def test_convert_rejects_missing_file(client: TestClient) -> None:
    response = client.post("/api/convert", json={"path": "/no/such.mp4", "name": "x"},
                           headers=HEADERS)
    assert response.status_code == 400
    assert response.json()["code"] == "file_not_found"


def test_convert_validation_error_shape(client: TestClient) -> None:
    response = client.post("/api/convert", json={"path": "/x.mp4", "name": "x", "fps": 0},
                           headers=HEADERS)
    assert response.status_code == 422
    assert response.json()["message"].startswith("fps")


def test_estimate(client: TestClient) -> None:
    body = client.post("/api/convert/estimate",
                       json={"duration": 4, "fps": 25}, headers=HEADERS).json()
    assert body == {"frame_count": 100, "loop_seconds": 2.0, "refresh_rate": 50}


def test_media_only_serves_media_files(client: TestClient, env: Path) -> None:
    secret = env / "secret.txt"
    secret.write_text("x")
    assert client.get("/api/media", params={"path": str(secret)}).status_code == 400
    image = env / "pic.png"
    Image.new("RGB", (4, 4)).save(image)
    assert client.get("/api/media", params={"path": str(image)}).status_code == 200


# -- library & system ------------------------------------------------------------


def test_library_delete_and_bad_slug(client: TestClient, env: Path) -> None:
    make_library_theme(env)
    assert client.get("/api/library/demo").json()["frame_count"] == 3
    assert client.get("/api/library/..%2Fetc").status_code == 404
    assert client.delete("/api/library/demo", headers=HEADERS).status_code == 204
    assert client.get("/api/library").json() == []


def test_install_runs_pkexec_job_and_locks(
    client: TestClient, env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading

    make_library_theme(env)
    release = threading.Event()
    scripts: list[str] = []

    def fake_privileged(script: str) -> None:
        scripts.append(script)
        release.wait(5)

    monkeypatch.setattr(installer, "run_privileged", fake_privileged)
    first = client.post("/api/library/demo/install", headers=HEADERS)
    assert first.status_code == 202
    busy = client.post("/api/system/reset-text", headers=HEADERS)
    assert busy.status_code == 409 and busy.json()["code"] == "busy"
    assert client.get("/api/meta").json()["busy_locks"] == {"system": first.json()["job"]["id"]}

    release.set()
    job = wait_job(client, first.json()["job"]["id"])
    assert job["state"] == "succeeded"
    assert "update-alternatives --install" in scripts[0]


def test_failed_job_reports_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(_script: str) -> None:
        raise RuntimeError("Request dismissed")

    monkeypatch.setattr(installer, "run_privileged", boom)
    job_id = client.post("/api/system/reset-text", headers=HEADERS).json()["job"]["id"]
    job = wait_job(client, job_id)
    assert job["state"] == "failed"
    assert job["error"] == "Request dismissed"


def test_installed_themes_listing(client: TestClient, env: Path) -> None:
    theme_dir = env / "system-themes" / "demo"
    theme_dir.mkdir()
    (theme_dir / "demo.plymouth").write_text(
        "[Plymouth Theme]\nName=Demo\nDescription=Generated by Plymotion - video boot splash\n"
    )
    Image.new("RGB", (4, 4)).save(theme_dir / "frame1.png")
    (env / "backups" / "demo").mkdir(parents=True)

    [theme] = client.get("/api/system/themes").json()
    assert theme["is_plymotion"] and theme["has_backup"] and theme["frame_count"] == 1
    assert client.get("/api/system/themes/demo/frames/1").status_code == 200
    assert client.post("/api/system/themes/nope/activate", headers=HEADERS).status_code == 404


def test_restore_backup_requires_existing_backup(client: TestClient) -> None:
    response = client.post("/api/system/restore-backup", json={"theme": "demo"}, headers=HEADERS)
    assert response.status_code == 404


def test_cancel_convert(client: TestClient, env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import threading

    video = env / "clip.mp4"
    video.write_bytes(b"x")
    started = threading.Event()
    proceed = threading.Event()

    def slow_extract(_video: Path, out_dir: Path, **_kw: Any) -> int:
        out_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (4, 4)).save(out_dir / "frame1.png")
        started.set()
        proceed.wait(5)
        return 1

    monkeypatch.setattr(convert_service, "extract_frames", slow_extract)
    job_id = client.post("/api/convert", json={"path": str(video), "name": "c"},
                         headers=HEADERS).json()["job"]["id"]
    started.wait(5)
    assert client.delete(f"/api/jobs/{job_id}", headers=HEADERS).status_code == 202
    proceed.set()
    assert wait_job(client, job_id)["state"] == "cancelled"
    assert client.get("/api/library").json() == []


def test_auth_next_only_allows_local_paths(config: ApiConfig, env: Path) -> None:
    with TestClient(create_app(config), base_url=BASE) as anon:
        ok = anon.get("/auth", params={"token": config.token, "next": "/galeria"},
                      follow_redirects=False)
        assert ok.headers["location"] == "/galeria"
        evil = anon.get("/auth", params={"token": config.token, "next": "//evil.example"},
                        follow_redirects=False)
        assert evil.headers["location"] == "/"


def test_boot_logo_endpoint(
    client: TestClient, env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from plymotion.services import boot_logo

    make_library_theme(env)
    logo = env / "logo.png"
    Image.new("RGBA", (187, 72)).save(logo)
    monkeypatch.setattr(boot_logo, "login_logo_source", lambda: logo)

    body = client.post("/api/library/demo/boot-logo", json={"enabled": True},
                       headers=HEADERS).json()
    assert body["boot_logo"] and body["watermark_url"] == "/api/library/demo/watermark"
    assert client.get(body["watermark_url"]).status_code == 200

    monkeypatch.setattr(boot_logo, "login_logo_source", lambda: None)
    refused = client.post("/api/library/demo/boot-logo", json={"enabled": True}, headers=HEADERS)
    assert refused.status_code == 409
