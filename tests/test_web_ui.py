from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

ROOT = Path(tempfile.mkdtemp(prefix="vibeforge-webui-test-"))
os.environ.setdefault("VIBEFORGE_DATA", str(ROOT / "data"))
os.environ.setdefault("VIBEFORGE_PROJECTS", str(ROOT / "legacy-projects"))
os.environ.setdefault("VIBEFORGE_DB", str(ROOT / "data" / "vibeforge.db"))
os.environ.setdefault("VIBEFORGE_ADMIN_PASSWORD", "admin-test-password")
os.environ.setdefault("VIBEFORGE_COOKIE_SECURE", "0")
os.environ.setdefault("VIBEFORGE_AUTO_MIGRATE", "0")

from fastapi.testclient import TestClient  # noqa: E402

import server.main as main_module  # noqa: E402
from server.db import db  # noqa: E402
from server.events import store  # noqa: E402
from server.templates.library import classify  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(main_module.app) as test_client:
        response = test_client.post(
            "/api/auth/register",
            json={"username": "webuiuser", "password": "webui-password"},
        )
        if response.status_code == 409:
            response = test_client.post(
                "/api/auth/login",
                json={"username": "webuiuser", "password": "webui-password"},
            )
        assert response.status_code == 200, response.text
        yield test_client


@pytest.fixture()
def react_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text(
        '<!doctype html><div id="root" data-ui="react"></div>'
        '<script type="module" src="/assets/index-abc.js"></script>',
        encoding="utf-8",
    )
    (assets / "index-abc.js").write_text("console.log('react-ui');", encoding="utf-8")
    return dist


def test_legacy_ui_serves_static_app(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert 'href="/static/app.css' in response.text
    assert "react-ui" not in response.text

    projects = client.get("/projects/demo123")
    assert projects.status_code == 200
    assert 'href="/static/app.css' in projects.text

    assert client.get("/assets/index-abc.js").status_code == 404


def test_capabilities_do_not_expose_stack_choice(client: TestClient):
    response = client.get("/api/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "stacks" not in data
    assert [item["key"] for item in data["items"]] == [
        "game",
        "website",
        "image",
        "video",
        "resume",
        "travel",
        "code",
    ]
    labels = {item["key"]: item["label"] for item in data["items"]}
    assert labels["video"] == "视频制作"
    assert "adapt" not in labels
    assert "sandbox" in data


def test_classification_no_longer_routes_to_adapt():
    assert classify("把主视觉适配成 16:9、1:1、9:16 三种尺寸") != "adapt"
    assert classify("做一个霓虹风格的贪吃蛇小游戏") == "game"


def test_new_static_project_gets_unlisted_public_link(client: TestClient):
    user = db.get_user_by_key("webuiuser")
    assert user
    task = store.create(
        "公开链接测试",
        "website",
        "Public share",
        owner_id=user.id,
        stack="static",
    )
    (task.workspace / "index.html").write_text(
        "<html><body>public-share</body></html>", encoding="utf-8"
    )
    task.save_meta()

    assert task.share_token
    assert task.visibility == "share"
    meta = task.meta()
    assert meta["share_url"] == f"/s/{task.share_token}/"

    anonymous = TestClient(main_module.app)
    shared = anonymous.get(meta["share_url"])
    assert shared.status_code == 200
    assert "public-share" in shared.text

    assert client.delete(f"/api/projects/{task.id}/share").status_code == 200
    assert anonymous.get(meta["share_url"]).status_code == 404


def test_react_project_public_link_serves_dist_assets(client: TestClient):
    user = db.get_user_by_key("webuiuser")
    assert user
    task = store.create(
        "React 公开链接测试",
        "website",
        "React public share",
        owner_id=user.id,
        stack="react",
    )
    dist = task.artifact_dir
    (dist / "assets").mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(
        '<div id="root"></div><script src="./assets/index.js"></script>',
        encoding="utf-8",
    )
    (dist / "assets" / "index.js").write_text("console.log('public')", encoding="utf-8")
    task.save_meta()

    assert task.share_token
    anonymous = TestClient(main_module.app)
    base = f"/s/{task.share_token}/"
    assert anonymous.get(base).status_code == 200
    asset = anonymous.get(base + "assets/index.js")
    assert asset.status_code == 200
    assert "public" in asset.text


def test_next_project_waits_for_runtime_public_link(client: TestClient):
    user = db.get_user_by_key("webuiuser")
    assert user
    task = store.create(
        "应用运行时项目",
        "website",
        "Runtime only",
        owner_id=user.id,
        stack="next",
    )
    task.save_meta()

    assert task.share_token is None
    assert task.visibility == "private"
    assert task.meta()["share_url"] is None
    assert client.post(f"/api/projects/{task.id}/share").status_code == 400


def test_react_ui_serves_dist_and_spa_fallback(client: TestClient, react_dist, monkeypatch):
    monkeypatch.setattr(main_module, "UI_MODE", "react")
    monkeypatch.setattr(main_module, "REACT_DIST_DIR", react_dist)

    for path in ("/", "/projects", "/projects/demo123", "/admin", "/projects/demo123/refine"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert 'data-ui="react"' in response.text, path
        assert response.headers["cache-control"].startswith("no-store"), path

    asset = client.get("/assets/index-abc.js")
    assert asset.status_code == 200
    assert "react-ui" in asset.text or "react-ui" in asset.content.decode()
    assert "immutable" in asset.headers["cache-control"]

    api = client.get("/api/health")
    assert api.status_code == 200
    assert api.json()["status"] == "ok"
    assert 'data-ui="react"' not in api.text

    assert client.get("/assets/../app.js").status_code == 404
    assert client.get("/assets/%2e%2e/app.js").status_code == 404


def test_react_login_is_public_and_served_by_spa(react_dist, monkeypatch):
    monkeypatch.setattr(main_module, "UI_MODE", "react")
    monkeypatch.setattr(main_module, "REACT_DIST_DIR", react_dist)

    anonymous = TestClient(main_module.app)
    page = anonymous.get("/login")
    assert page.status_code == 200
    assert 'data-ui="react"' in page.text

    # The legacy login page remains available when the switch is off.
    monkeypatch.setattr(main_module, "UI_MODE", "legacy")
    legacy = TestClient(main_module.app).get("/login")
    assert legacy.status_code == 200
    assert "访问保护" in legacy.text


def test_react_ui_reports_missing_build(client: TestClient, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(main_module, "UI_MODE", "react")
    monkeypatch.setattr(main_module, "REACT_DIST_DIR", tmp_path / "missing")

    response = client.get("/")
    assert response.status_code == 503
    assert "npm run build" in response.json()["detail"]
