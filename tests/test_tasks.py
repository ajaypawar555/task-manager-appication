from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import tasks as task_routes
from app.api.routes.tasks import get_task_service, require_api_token
from app.core.config import Settings
from app.main import app
from app.schemas.task import TaskCreate, TaskUpdate

NOW = datetime(2025, 1, 1, tzinfo=UTC)


def task_row(task_id: int, **values: Any) -> dict[str, Any]:
    return {
        "id": task_id,
        "title": values.get("title", "Write tests"),
        "description": values.get("description"),
        "status": values.get("status", "pending"),
        "priority": values.get("priority", "medium"),
        "due_date": values.get("due_date"),
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
    }


class FakeService:
    def __init__(self) -> None:
        self.tasks = {1: task_row(1)}
        self.list_args: dict[str, Any] = {}
        self.fail = False

    def _maybe_fail(self) -> None:
        if self.fail:
            raise RuntimeError("private database detail")

    def create(self, payload: TaskCreate) -> dict[str, Any]:
        self._maybe_fail()
        row = task_row(2, **payload.model_dump(mode="json"))
        self.tasks[2] = row
        return row

    def list(self, **kwargs: Any) -> list[dict[str, Any]]:
        self._maybe_fail()
        self.list_args = kwargs
        return list(self.tasks.values())

    def get(self, task_id: int) -> dict[str, Any]:
        self._maybe_fail()
        if task_id not in self.tasks:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Task not found")
        return self.tasks[task_id]

    def update(self, task_id: int, payload: TaskUpdate) -> dict[str, Any]:
        self._maybe_fail()
        row = self.get(task_id)
        row.update(payload.model_dump(mode="json", exclude_unset=True))
        return row

    def delete(self, task_id: int) -> None:
        self._maybe_fail()
        self.tasks.pop(task_id, None)


@pytest.fixture
def fake_service() -> FakeService:
    service = FakeService()
    app.dependency_overrides[get_task_service] = lambda: service
    app.dependency_overrides[require_api_token] = lambda: None
    yield service
    app.dependency_overrides.clear()


@pytest.fixture
def client(fake_service: FakeService) -> TestClient:
    return TestClient(app)


def test_create_task(client: TestClient) -> None:
    response = client.post("/api/v1/tasks", json={"title": "New task"})
    assert response.status_code == 201
    assert response.json()["title"] == "New task"
    assert response.json()["status"] == "pending"


def test_list_tasks_and_query_filters(client: TestClient, fake_service: FakeService) -> None:
    response = client.get(
        "/api/v1/tasks?status=completed&priority=high&search=report&limit=5&offset=10"
    )
    assert response.status_code == 200
    assert fake_service.list_args == {
        "status_filter": "completed",
        "priority": "high",
        "search": "report",
        "limit": 5,
        "offset": 10,
    }


def test_get_existing_task(client: TestClient) -> None:
    response = client.get("/api/v1/tasks/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_get_missing_task(client: TestClient) -> None:
    response = client.get("/api/v1/tasks/999")
    assert response.status_code == 404


def test_update_task(client: TestClient) -> None:
    response = client.patch("/api/v1/tasks/1", json={"status": "completed"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_delete_task(client: TestClient) -> None:
    response = client.delete("/api/v1/tasks/1")
    assert response.status_code == 204
    assert client.get("/api/v1/tasks/1").status_code == 404


@pytest.mark.parametrize(
    "payload",
    [{"title": ""}, {"title": "x" * 201}, {"title": "Task", "status": "blocked"}],
)
def test_invalid_task_input_returns_422(client: TestClient, payload: dict[str, Any]) -> None:
    response = client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 422


def test_empty_patch_returns_422(client: TestClient) -> None:
    assert client.patch("/api/v1/tasks/1", json={}).status_code == 422


def test_database_failure_is_sanitized(client: TestClient, fake_service: FakeService) -> None:
    fake_service.fail = True
    response = client.get("/api/v1/tasks")
    assert response.status_code == 503
    assert response.json() == {"detail": "Task storage is temporarily unavailable"}
    assert "private database detail" not in response.text


def test_supabase_client_initialization_failure_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_client() -> Any:
        raise RuntimeError("private Supabase configuration detail")

    monkeypatch.setattr(task_routes, "get_supabase_client", fail_client)
    app.dependency_overrides.clear()
    app.dependency_overrides[require_api_token] = lambda: None

    response = TestClient(app).get("/api/v1/tasks")

    assert response.status_code == 503
    assert response.json() == {"detail": "Task storage is temporarily unavailable"}
    assert "private Supabase configuration detail" not in response.text
    app.dependency_overrides.clear()


def test_task_routes_require_token_when_not_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_routes, "get_settings", lambda: Settings(api_auth_enabled=True))
    app.dependency_overrides.clear()
    response = TestClient(app).get("/api/v1/tasks")
    assert response.status_code == 401
    app.dependency_overrides.clear()


def test_auth_can_be_disabled_for_local_testing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task_routes, "get_settings", lambda: Settings(api_auth_enabled=False))
    assert require_api_token() is None


def test_auth_is_disabled_by_default() -> None:
    assert Settings().api_auth_enabled is False
