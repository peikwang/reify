from __future__ import annotations

import io
import json
import os
import tarfile
import tempfile
from pathlib import Path

import pytest

ROOT = Path(tempfile.mkdtemp(prefix="reify-test-"))
os.environ["REIFY_DATA"] = str(ROOT / "data")
os.environ["REIFY_PROJECTS"] = str(ROOT / "legacy-projects")
os.environ["REIFY_DB"] = str(ROOT / "data" / "reify.db")
os.environ["REIFY_ADMIN_PASSWORD"] = "admin-test-password"
os.environ["REIFY_COOKIE_SECURE"] = "0"
os.environ["REIFY_REGISTRATION"] = "open"
os.environ["REIFY_AUTO_MIGRATE"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from server.db import db  # noqa: E402
from server.events import store  # noqa: E402
from server.main import app  # noqa: E402
from server.migrate import migrate_legacy  # noqa: E402
from server.sandbox import SandboxError, SandboxRunner, _sign_asset_urls  # noqa: E402
from server.templates.next_app import build_files as next_build_files  # noqa: E402
from server.templates.next_app import next_checks_files  # noqa: E402
from server.templates.react_app import build_files as react_build_files  # noqa: E402
from server.templates.react_app import react_checks_files  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _register(client: TestClient, username: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "correct-horse-battery",
            "display_name": username.title(),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["user"]


def _make_project(owner_id: str, title: str):
    task = store.create("做一个隔离测试项目", "website", title, owner_id=owner_id)
    task.workspace.mkdir(parents=True, exist_ok=True)
    (task.workspace / "index.html").write_text("<html><body>hello</body></html>", encoding="utf-8")
    assets = task.workspace / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "pic.png").write_bytes(b"fake-png")
    (assets / "evil.svg").write_text("<svg onload='alert(1)'/>", encoding="utf-8")
    task.save_meta()
    return task


def test_registration_persists_and_is_case_insensitive(client: TestClient):
    alice = _register(client, "Alice")
    bob = _register(TestClient(app), "bob")

    assert db.get_user_by_key("alice") is not None
    assert alice["username"] == "Alice"
    assert bob["username"] == "bob"

    duplicate = TestClient(app).post(
        "/api/auth/register",
        json={"username": "alice", "password": "another-password"},
    )
    assert duplicate.status_code == 409


def test_cross_user_project_access_is_denied(client: TestClient):
    alice = db.get_user_by_key("alice")
    bob = db.get_user_by_key("bob")
    assert alice and bob
    task = _make_project(alice.id, "Alice project")

    own = client.get(f"/api/projects/{task.id}")
    assert own.status_code == 200
    assert own.json()["task"]["id"] == task.id

    bob_client = TestClient(app)
    login = bob_client.post(
        "/api/auth/login", json={"username": "bob", "password": "correct-horse-battery"}
    )
    assert login.status_code == 200

    assert bob_client.get("/api/projects").json()["items"] == []
    assert bob_client.get(f"/api/projects/{task.id}").status_code == 404
    assert bob_client.get(f"/api/projects/{task.id}/events").status_code == 404
    assert bob_client.get(f"/api/projects/{task.id}/bundle").status_code == 404
    assert bob_client.post(
        f"/api/projects/{task.id}/refine", json={"instruction": "改一下"}
    ).status_code == 404
    assert bob_client.post(f"/api/projects/{task.id}/deploy").status_code == 404
    assert bob_client.get(f"/p/{task.id}/", follow_redirects=False).status_code == 404


def test_preview_and_media_capability_urls(client: TestClient):
    alice = db.get_user_by_key("alice")
    assert alice
    task = _make_project(alice.id, "Media project")

    unauthorized = TestClient(app).get(f"/p/{task.id}/", follow_redirects=False)
    assert unauthorized.status_code == 303
    assert unauthorized.headers["location"].startswith("/login")

    assert client.get(f"/p/{task.id}/").status_code == 200
    assert client.get(f"/p/{task.id}/index.html").status_code == 200

    bad_key = TestClient(app).get(f"/media/{task.id}/assets/pic.png?k=wrong")
    assert bad_key.status_code == 404
    good_key = TestClient(app).get(f"/media/{task.id}/assets/pic.png?k={task.asset_key}")
    assert good_key.status_code == 200
    assert good_key.content == b"fake-png"
    svg = TestClient(app).get(f"/media/{task.id}/assets/evil.svg?k={task.asset_key}")
    assert svg.status_code == 404


def test_path_traversal_is_rejected(client: TestClient):
    alice = db.get_user_by_key("alice")
    assert alice
    task = _make_project(alice.id, "Traversal project")
    response = client.get(f"/p/{task.id}/%2e%2e/%2e%2e/etc/passwd")
    assert response.status_code == 404


def test_session_is_server_side_and_revocable(client: TestClient):
    alice = db.get_user_by_key("alice")
    assert alice
    task = _make_project(alice.id, "Session project")
    token = client.cookies.get("reify_session")
    assert token

    # A brand-new client with the same cookie is authenticated: state lives in SQLite.
    second = TestClient(app)
    second.cookies.set("reify_session", token)
    assert second.get("/api/auth/me").json()["authenticated"] is True
    assert second.get(f"/api/projects/{task.id}").status_code == 200

    assert client.post("/api/auth/logout").status_code == 200
    third = TestClient(app)
    third.cookies.set("reify_session", token)
    assert third.get("/api/auth/me").json()["authenticated"] is False
    assert third.get(f"/api/projects/{task.id}").status_code == 401


def test_react_requires_sandbox_and_signs_assets(client: TestClient):
    fresh = TestClient(app)
    login = fresh.post(
        "/api/auth/login", json={"username": "alice", "password": "correct-horse-battery"}
    )
    assert login.status_code == 200
    response = fresh.post(
        "/api/projects",
        json={"prompt": "做一个 React 官网", "capability": "website", "stack": "react"},
    )
    assert response.status_code == 503

    html = '<script type="module" crossorigin src="./assets/index-abc.js"></script><link rel="stylesheet" href="./assets/index-abc.css">'
    signed = _sign_asset_urls(html, "deadbeef")
    assert "./assets/index-abc.js?k=deadbeef" in signed
    assert "./assets/index-abc.css?k=deadbeef" in signed
    external = '<script src="https://evil.example/assets/x.js"></script>'
    assert _sign_asset_urls(external, "deadbeef") == external


def test_react_artifact_validation_and_tar_escape():
    source = react_build_files(
        {
            "title": "Test",
            "tagline": "tag",
            "paragraph": "copy",
            "highlights": ["a", "b", "c", "d"],
            "accent": "#1e5c40",
        },
        "prompt",
    )
    assert "package.json" in source
    assert "package-lock.json" in source and source["package-lock.json"]
    assert "src/main.tsx" in source
    assert "src/App.tsx" in source
    assert "tsconfig.json" in source
    assert "vite.config.ts" in source
    assert not any(path.endswith((".jsx", ".ts.jsx")) for path in source)
    package = json.loads(source["package.json"])
    assert "tsc --noEmit" in package["scripts"]["build"]
    assert "typescript" in package["devDependencies"]
    assert '"jsx": "react-jsx"' in source["tsconfig.json"]
    checks = react_checks_files(
        {"index.html": b'<div id="root"></div>', "assets/app.js": b"bundle"}
    )
    assert all(ok for _, ok, _ in checks)

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo("../escape.txt")
        data = b"x"
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    with pytest.raises(SandboxError):
        SandboxRunner._extract_artifact(buffer.getvalue(), 1024)


def test_next_scaffold_and_artifact_checks():
    source = next_build_files(
        {
            "title": "Test",
            "tagline": "tag",
            "paragraph": "copy",
            "highlights": ["a", "b", "c", "d"],
            "accent": "#1e5c40",
        },
        "prompt",
        "abc123",
    )
    assert "app/page.tsx" in source
    assert "app/layout.tsx" in source
    assert "app/NoteBoard.tsx" in source
    assert "app/api/notes/route.ts" in source
    assert "tsconfig.json" in source
    assert "next-env.d.ts" in source
    assert "next.config.mjs" in source
    assert not any(path.endswith((".jsx", ".ts.jsx")) for path in source)
    package = json.loads(source["package.json"])
    assert "typescript" in package["devDependencies"]
    assert source["package-lock.json"]
    checks = next_checks_files(
        {
            "server.js": b"x",
            ".next/BUILD_ID": b"x",
            ".next/static/app.js": b"x",
            "node_modules/next/package.json": b"{}",
        }
    )
    assert all(ok for _, ok, _ in checks)


def test_unauthenticated_api_and_cross_origin_writes_are_rejected():
    anon = TestClient(app)
    assert anon.get("/api/projects").status_code == 401
    response = anon.post(
        "/api/auth/login",
        json={"username": "alice", "password": "correct-horse-battery"},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403


def test_admin_and_share_flows():
    with TestClient(app) as admin:
        login = admin.post(
            "/api/auth/login", json={"username": "admin", "password": "admin-test-password"}
        )
        assert login.status_code == 200
        owner = TestClient(app)
        registered = owner.post(
            "/api/auth/register",
            json={"username": "shareuser", "password": "password123"},
        )
        assert registered.status_code == 200
        owner_id = registered.json()["user"]["id"]
        users = admin.get("/api/admin/users")
        assert users.status_code == 200
        assert any(item["username"] == "shareuser" for item in users.json()["items"])
        assert admin.get("/api/admin/audit").status_code == 200

        task = _make_project(owner_id, "Share project")
        shared = owner.post(f"/api/projects/{task.id}/share")
        assert shared.status_code == 200
        token = shared.json()["share_token"]

        anon = TestClient(app)
        assert anon.get(f"/s/{token}/").status_code == 200
        assert anon.get(f"/p/{task.id}/", follow_redirects=False).status_code == 303

        assert owner.delete(f"/api/projects/{task.id}/share").status_code == 200
        assert anon.get(f"/s/{token}/").status_code == 404
        assert owner.get("/api/admin/users").status_code == 403

        assert admin.post(
            f"/api/admin/users/{owner_id}/status", json={"disabled": True}
        ).status_code == 200
        blocked = TestClient(app).post(
            "/api/auth/login", json={"username": "shareuser", "password": "password123"}
        )
        assert blocked.status_code == 401
        assert admin.post(
            f"/api/admin/users/{owner_id}/status", json={"disabled": False}
        ).status_code == 200
        assert admin.post(
            "/api/admin/users/" + admin.get("/api/auth/me").json()["user"]["id"] + "/status",
            json={"disabled": True},
        ).status_code == 400


def test_storage_is_per_user():
    alice = db.get_user_by_key("alice")
    bob = db.get_user_by_key("bob")
    assert alice and bob
    row = db.get_project(store.list(alice.id)[0]["id"])
    assert row is not None
    assert row["owner_id"] == alice.id
    assert (ROOT / "data" / "users" / alice.id / "projects" / row["id"] / "workspace" / "index.html").exists()
    meta = (ROOT / "data" / "users" / alice.id / "projects" / row["id"] / "meta.json").read_text(
        encoding="utf-8"
    )
    assert alice.id in meta


def test_legacy_migration_rewrites_urls_and_media_keys():
    admin = db.get_user_by_key("admin")
    assert admin

    project_id = "legacy001"
    task_dir = ROOT / "data" / "tasks" / project_id
    workspace_dir = ROOT / "legacy-projects" / project_id
    task_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "assets").mkdir(parents=True, exist_ok=True)
    (task_dir / "meta.json").write_text(
        '{"id":"legacy001","capability":"image","status":"done","title":"Old","prompt":"p",'
        '"created_at":"2026-10-01T00:00:00+00:00","updated_at":"2026-10-02T00:00:00+00:00",'
        '"result":{"url":"/tasks/legacy001/"}}',
        encoding="utf-8",
    )
    (task_dir / "events.jsonl").write_text(
        '{"seq":1,"type":"deployed","url":"/tasks/legacy001/"}\n', encoding="utf-8"
    )
    (workspace_dir / "index.html").write_text(
        '<img src="/media/legacy001/assets/a.png"><img src="/media/legacy001/assets/b.png?x=1">',
        encoding="utf-8",
    )
    (workspace_dir / "assets" / "a.png").write_bytes(b"a")
    (workspace_dir / "assets" / "b.png").write_bytes(b"b")

    report = migrate_legacy(admin.id)
    assert project_id in [item["id"] for item in report["migrated"]]

    row = db.get_project(project_id)
    assert row and row["owner_id"] == admin.id
    target = ROOT / "data" / "users" / admin.id / "projects" / project_id
    html = (target / "workspace" / "index.html").read_text(encoding="utf-8")
    assert f"/media/{project_id}/assets/a.png?k={row['asset_key']}" in html
    assert f"/media/{project_id}/assets/b.png?x=1&k={row['asset_key']}" in html
    events = (target / "events.jsonl").read_text(encoding="utf-8")
    assert f"/p/{project_id}/" in events
    assert "/tasks/" not in events

    store.reload()
    migrated = store.get(project_id, admin.id)
    assert migrated is not None
    assert migrated.url == f"/p/{project_id}/"

    again = migrate_legacy(admin.id)
    assert project_id in again["skipped"]
    assert db.get_project(project_id)["asset_key"] == row["asset_key"]
    html_again = (target / "workspace" / "index.html").read_text(encoding="utf-8")
    assert f"/media/{project_id}/assets/a.png?k={row['asset_key']}" in html_again
