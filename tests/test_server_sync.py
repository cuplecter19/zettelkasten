"""클라우드 동기화 서버(FastAPI) 엔드포인트 테스트.

서버 모듈은 최상위 이름(main_server, auth, database_server, api)으로 import 되므로
import 전에 ``server/`` 를 ``sys.path`` 에 추가하고 환경변수로 임시 DB 를 지정한다.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

SERVER_DIR = Path(__file__).resolve().parent.parent / "server"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ZK_SERVER_DIR", str(tmp_path))
    monkeypatch.setenv("ZK_SERVER_DB", str(tmp_path / "server.db"))
    monkeypatch.setenv("ZK_SERVER_PDF_DIR", str(tmp_path / "pdfs"))
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    monkeypatch.setenv("ALLOWED_DEVICES", "main-pc,laptop")
    monkeypatch.syspath_prepend(str(SERVER_DIR))

    # 환경변수를 반영하기 위해 서버 모듈을 새로 로드한다.
    for name in ["main_server", "auth", "database_server", "config_server",
                 "api.notes", "api.tags", "api.pdfs", "api.sync", "api"]:
        sys.modules.pop(name, None)

    main_server = importlib.import_module("main_server")
    from fastapi.testclient import TestClient

    with TestClient(main_server.app) as c:
        yield c


def _auth(client, device_id="main-pc"):
    token = client.post("/api/auth/token",
                        json={"device_id": device_id}).json()["access_token"]
    return {"Authorization": "Bearer " + token}


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_token_rejects_unknown_device(client):
    resp = client.post("/api/auth/token", json={"device_id": "intruder"})
    assert resp.status_code == 403


def test_notes_require_auth(client):
    assert client.get("/api/notes").status_code == 401


def test_note_crud_and_soft_delete(client):
    h = _auth(client)
    created = client.post("/api/notes",
                          json={"title": "T", "body": "B", "note_type": "IDEA"},
                          headers=h)
    assert created.status_code == 201
    nid = created.json()["id"]

    assert len(client.get("/api/notes", headers=h).json()) == 1

    assert client.delete(f"/api/notes/{nid}", headers=h).status_code == 204
    assert client.get("/api/notes", headers=h).json() == []


def test_sync_push_last_write_wins(client):
    h = _auth(client)
    nid = client.post("/api/notes",
                      json={"title": "서버최신", "body": "x", "note_type": "IDEA"},
                      headers=h).json()["id"]

    # 더 오래된 로컬 버전을 push → 서버가 더 최신이므로 충돌(서버 유지).
    push = {
        "device_id": "main-pc",
        "last_sync_at": None,
        "changes": {"notes": [{
            "id": nid, "title": "오래된로컬", "body": "y",
            "note_type": "IDEA", "updated_at": "2000-01-01T00:00:00",
            "deleted": False,
        }]},
    }
    result = client.post("/api/sync/push", json=push, headers=h).json()
    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["record"]["title"] == "서버최신"


def test_sync_push_newer_local_wins(client):
    h = _auth(client)
    nid = client.post("/api/notes",
                      json={"title": "초기", "body": "x", "note_type": "IDEA"},
                      headers=h).json()["id"]

    push = {
        "device_id": "main-pc",
        "last_sync_at": None,
        "changes": {"notes": [{
            "id": nid, "title": "새로운로컬", "body": "z",
            "note_type": "IDEA", "updated_at": "2099-01-01T00:00:00",
            "deleted": False,
        }]},
    }
    result = client.post("/api/sync/push", json=push, headers=h).json()
    assert result["conflicts"] == []

    notes = client.get("/api/notes", headers=h).json()
    assert notes[0]["title"] == "새로운로컬"


def test_sync_pull_returns_records(client):
    h = _auth(client)
    client.post("/api/notes",
                json={"title": "풀테스트", "body": "x", "note_type": "IDEA"},
                headers=h)
    pulled = client.post("/api/sync/pull",
                         json={"device_id": "main-pc", "last_sync_at": None},
                         headers=h).json()
    assert len(pulled["notes"]) == 1
    assert "server_time" in pulled
