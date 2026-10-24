from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

ROOT = Path(tempfile.mkdtemp(prefix="reify-webui-test-"))
os.environ.setdefault("REIFY_DATA", str(ROOT / "data"))
os.environ.setdefault("REIFY_PROJECTS", str(ROOT / "legacy-projects"))
os.environ.setdefault("REIFY_DB", str(ROOT / "data" / "reify.db"))
os.environ.setdefault("REIFY_ADMIN_PASSWORD", "admin-test-password")
os.environ.setdefault("REIFY_COOKIE_SECURE", "0")
os.environ.setdefault("REIFY_AUTO_MIGRATE", "0")

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


def test_legacy_ui_is_gone(client: TestClient, react_dist, monkeypatch):
    monkeypatch.setattr(main_module, "REACT_DIST_DIR", react_dist)

    response = client.get("/")
    assert response.status_code == 200
    assert 'data-ui="react"' in response.text
    assert client.get("/static/app.js").status_code == 404
    assert client.get("/static/app.css").status_code == 404


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
    (task.workspace / "README.md").write_text("secret prompt", encoding="utf-8")
    assets = task.workspace / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "note.txt").write_text("public asset", encoding="utf-8")
    task.save_meta()

    assert task.share_token
    assert task.visibility == "share"
    meta = task.meta()
    assert meta["share_url"] == f"/s/{task.share_token}/"
    asset_key = task.asset_key

    anonymous = TestClient(main_module.app)
    shared = anonymous.get(meta["share_url"])
    assert shared.status_code == 200
    assert "public-share" in shared.text
    assert anonymous.get(meta["share_url"] + "README.md").status_code == 404
    assert anonymous.get(meta["share_url"] + "assets/note.txt").text == "public asset"
    assert anonymous.get(f"/p/{task.id}/assets/note.txt?k={asset_key}").status_code == 200

    assert client.delete(f"/api/projects/{task.id}/share").status_code == 200
    assert anonymous.get(meta["share_url"]).status_code == 404
    assert anonymous.get(f"/p/{task.id}/assets/note.txt?k={asset_key}").status_code == 404
    assert anonymous.get(f"/media/{task.id}/assets/note.txt?k={asset_key}").status_code == 404
    assert client.get(f"/p/{task.id}/").status_code == 200


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
    index = anonymous.get(base)
    assert index.status_code == 200
    assert index.headers["access-control-allow-origin"] == "*"
    asset = anonymous.get(base + "assets/index.js")
    assert asset.status_code == 200
    assert asset.headers["access-control-allow-origin"] == "*"
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
    monkeypatch.setattr(main_module, "REACT_DIST_DIR", react_dist)

    anonymous = TestClient(main_module.app)
    page = anonymous.get("/login")
    assert page.status_code == 200
    assert 'data-ui="react"' in page.text


def test_react_ui_reports_missing_build(client: TestClient, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(main_module, "REACT_DIST_DIR", tmp_path / "missing")

    response = client.get("/")
    assert response.status_code == 503
    assert "npm run build" in response.json()["detail"]


def test_refine_accepts_legacy_jsx_and_typescript_sources(client: TestClient, monkeypatch):
    async def noop(_task, _instruction):
        return None

    monkeypatch.setattr(main_module, "run_refine", noop)
    monkeypatch.setattr(main_module, "_enforce_user_quota", lambda *_args, **_kwargs: None)
    user = db.get_user_by_key("webuiuser")
    assert user
    cases = [
        ("react", "src/App.jsx"),
        ("react", "src/App.tsx"),
        ("next", "app/page.jsx"),
        ("next", "app/page.tsx"),
    ]
    for stack, source in cases:
        task = store.create(
            f"refine {source}",
            "website",
            f"Refine {source}",
            owner_id=user.id,
            stack=stack,
        )
        target = task.workspace / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("export default function App() { return null; }\n", encoding="utf-8")
        task.status = "done"
        task.save_meta()
        response = client.post(
            f"/api/projects/{task.id}/refine",
            json={"instruction": "改标题"},
        )
        assert response.status_code == 200, (source, response.text)
        task.status = "done"
        task.save_meta()


def test_auto_source_routing_falls_back_when_sandbox_unavailable(monkeypatch):
    async def noop(_task):
        return None

    monkeypatch.setattr(main_module, "run_task", noop)
    headers = {"X-Forwarded-For": "198.51.100.71"}
    with TestClient(main_module.app) as routed:
        registered = routed.post(
            "/api/auth/register",
            json={"username": "autofallback", "password": "correct-horse-battery"},
            headers=headers,
        )
        assert registered.status_code == 200, registered.text

        auto = routed.post(
            "/api/projects",
            json={"prompt": "帮我做一个个人作品集网站", "capability": "website"},
            headers=headers,
        )
        assert auto.status_code == 200, auto.text
        auto_task = auto.json()["task"]
        assert auto_task["stack"] == "static"
        assert auto_task["share_url"]

        game = routed.post(
            "/api/projects",
            json={
                "prompt": "做一个霓虹风格的贪吃蛇小游戏",
                "capability": "game",
                "stack": "react",
            },
            headers=headers,
        )
        assert game.status_code == 200, game.text
        assert game.json()["task"]["stack"] == "static"

        explicit = routed.post(
            "/api/projects",
            json={
                "prompt": "用 React 做一个作品集网站",
                "capability": "website",
                "stack": "react",
            },
            headers=headers,
        )
        assert explicit.status_code == 503


def test_auto_source_routing_selects_react_and_next_with_sandbox_available(monkeypatch):
    class FakeSandbox:
        enabled = True

        async def reachable(self):
            return True

    async def noop(_task):
        return None

    monkeypatch.setattr(main_module, "sandbox_runner", FakeSandbox())
    monkeypatch.setattr(main_module, "run_task", noop)
    react_headers = {"X-Forwarded-For": "198.51.100.81"}
    with TestClient(main_module.app) as react_client:
        registered = react_client.post(
            "/api/auth/register",
            json={"username": "autoreact", "password": "correct-horse-battery"},
            headers=react_headers,
        )
        assert registered.status_code == 200, registered.text
        created = react_client.post(
            "/api/projects",
            json={"prompt": "帮我做一个个人作品集网站", "capability": "website"},
            headers=react_headers,
        )
        assert created.status_code == 200, created.text
        react_task = created.json()["task"]
        assert react_task["stack"] == "react"
        assert react_task["share_url"]

    next_headers = {"X-Forwarded-For": "198.51.100.82"}
    with TestClient(main_module.app) as next_client:
        registered = next_client.post(
            "/api/auth/register",
            json={"username": "autonext", "password": "correct-horse-battery"},
            headers=next_headers,
        )
        assert registered.status_code == 200, registered.text
        created = next_client.post(
            "/api/projects",
            json={
                "prompt": "用 Next.js 做官网，带服务端留言板",
                "capability": "website",
            },
            headers=next_headers,
        )
        assert created.status_code == 200, created.text
        next_task = created.json()["task"]
        assert next_task["stack"] == "next"
        assert next_task["share_url"] is None


def test_runtime_start_respects_per_user_cap(client: TestClient, monkeypatch):
    monkeypatch.setattr(main_module, "MAX_RUNTIME_PER_USER", 2)
    user = db.get_user_by_key("webuiuser")
    assert user
    running = []
    for index in range(2):
        project = store.create(
            f"runtime {index}",
            "website",
            f"Runtime {index}",
            owner_id=user.id,
            stack="next",
        )
        db.save_runtime({"project_id": project.id, "status": "running", "revision": 0})
        running.append(project)
    target = store.create(
        "runtime target",
        "website",
        "Runtime target",
        owner_id=user.id,
        stack="next",
    )
    target.status = "done"
    target.save_meta()

    response = client.post(f"/api/projects/{target.id}/runtime/start")
    assert response.status_code == 429
    assert "运行中的应用数量已达上限" in response.json()["detail"]

    for project in [*running, target]:
        db.save_runtime({"project_id": project.id, "status": "stopped", "revision": 0})


def test_owner_can_delete_project(client: TestClient):
    user = db.get_user_by_key("webuiuser")
    assert user
    task = store.create("待删除项目", "website", "Delete me", owner_id=user.id, stack="static")
    (task.workspace / "index.html").write_text("<html><body>delete-me</body></html>", encoding="utf-8")
    task.status = "done"
    task.save_meta()
    project_dir = task.dir
    share_url = task.meta()["share_url"]
    assert project_dir.exists()

    response = client.delete(f"/api/projects/{task.id}")
    assert response.status_code == 200
    assert not project_dir.exists()
    assert db.get_project(task.id) is None
    assert store.get_any(task.id) is None
    assert client.get(f"/api/projects/{task.id}").status_code == 404
    assert TestClient(main_module.app).get(share_url).status_code == 404
    assert any(item["action"] == "project.delete" for item in db.list_audit(200))


def test_delete_is_owner_only(client: TestClient):
    admin = db.get_user_by_key("admin")
    assert admin
    other = store.create("别人的项目", "website", "Other", owner_id=admin.id, stack="static")
    other.status = "done"
    other.save_meta()
    response = client.delete(f"/api/projects/{other.id}")
    assert response.status_code == 404
    assert other.dir.exists()
    db.delete_project(other.id)
    store.remove(other.id)
    import shutil
    shutil.rmtree(other.dir, ignore_errors=True)


def test_delete_rejects_running_project(client: TestClient):
    user = db.get_user_by_key("webuiuser")
    assert user
    task = store.create("运行中的项目", "website", "Running", owner_id=user.id, stack="static")
    task.status = "running"
    task.save_meta()
    assert client.delete(f"/api/projects/{task.id}").status_code == 409
    assert task.dir.exists()
    task.status = "done"
    task.save_meta()
    assert client.delete(f"/api/projects/{task.id}").status_code == 200


def test_delete_stops_next_runtime(client: TestClient, monkeypatch):
    user = db.get_user_by_key("webuiuser")
    assert user
    task = store.create("SSR 待删除", "website", "Runtime delete", owner_id=user.id, stack="next")
    task.status = "done"
    (task.workspace / "runtime").mkdir(parents=True, exist_ok=True)
    (task.workspace / "runtime" / "server.js").write_text("", encoding="utf-8")
    task.save_meta()
    db.save_runtime({"project_id": task.id, "status": "running", "revision": 0})
    stopped = []

    async def fake_stop(item):
        stopped.append(item.id)
        return {"status": "stopped"}

    monkeypatch.setattr(main_module.runtime_manager, "stop", fake_stop)
    response = client.delete(f"/api/projects/{task.id}")
    assert response.status_code == 200
    assert stopped == [task.id]
    assert db.get_runtime(task.id) is None
    assert not task.dir.exists()


def test_delete_fails_closed_when_runtime_stop_fails(client: TestClient, monkeypatch):
    user = db.get_user_by_key("webuiuser")
    assert user
    task = store.create("SSR 运行时失败", "website", "Runtime fail", owner_id=user.id, stack="next")
    task.status = "done"
    (task.workspace / "runtime").mkdir(parents=True, exist_ok=True)
    (task.workspace / "runtime" / "server.js").write_text("", encoding="utf-8")
    task.save_meta()
    db.save_runtime({"project_id": task.id, "status": "running", "revision": 0})

    async def failing_stop(_task):
        raise RuntimeError("sandbox down")

    monkeypatch.setattr(main_module.runtime_manager, "stop", failing_stop)
    response = client.delete(f"/api/projects/{task.id}")
    assert response.status_code == 503
    assert task.dir.exists()
    assert db.get_runtime(task.id) is not None
    task.status = "done"
    task.save_meta()
    db.delete_project(task.id)
    store.remove(task.id)
    import shutil
    shutil.rmtree(task.dir, ignore_errors=True)


def test_delete_rejects_a_symlinked_project_directory(client: TestClient):
    user = db.get_user_by_key("webuiuser")
    assert user
    victim = store.create("目标项目", "website", "Victim", owner_id=user.id, stack="static")
    victim.status = "done"
    victim.save_meta()
    task = store.create("链接项目", "website", "Link", owner_id=user.id, stack="static")
    task.status = "done"
    task.save_meta()
    import shutil
    shutil.rmtree(task.dir)
    task.dir.symlink_to(victim.dir, target_is_directory=True)

    response = client.delete(f"/api/projects/{task.id}")
    assert response.status_code == 500
    assert victim.dir.exists()
    assert db.get_project(task.id) is not None

    task.dir.unlink()
    db.delete_project(task.id)
    db.delete_project(victim.id)
    store.remove(task.id)
    store.remove(victim.id)
    shutil.rmtree(victim.dir, ignore_errors=True)


def test_delete_keeps_other_projects(client: TestClient):
    user = db.get_user_by_key("webuiuser")
    assert user
    keep = store.create("保留项目", "website", "Keep", owner_id=user.id, stack="static")
    keep.status = "done"
    keep.save_meta()
    drop = store.create("删除项目", "website", "Drop", owner_id=user.id, stack="static")
    drop.status = "done"
    drop.save_meta()

    assert client.delete(f"/api/projects/{drop.id}").status_code == 200
    assert keep.dir.exists()
    assert db.get_project(keep.id) is not None
    assert client.get(f"/api/projects/{keep.id}").status_code == 200
