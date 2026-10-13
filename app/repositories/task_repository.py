"""Supabase-backed task data access."""

from datetime import UTC, datetime
from typing import Any

from supabase import Client

from app.models.task import TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate


class TaskRepository:
    """Encapsulate Supabase query construction for tasks."""

    def __init__(self, client: Client) -> None:
        self.client = client

    @staticmethod
    def _checked(response: Any) -> list[dict[str, Any]]:
        if response.data is None:
            return []
        return response.data

    def create(self, task: TaskCreate) -> dict[str, Any]:
        payload = task.model_dump(mode="json")
        return self._checked(self.client.table("tasks").insert(payload).execute())[0]

    def list(
        self,
        *,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        query = self.client.table("tasks").select("*")
        if status is not None:
            query = query.eq("status", status.value)
        if priority is not None:
            query = query.eq("priority", priority.value)
        if search:
            # Escape PostgREST pattern metacharacters so user text remains a literal search.
            literal = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.ilike("title", f"%{literal}%")
        response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return self._checked(response)

    def get(self, task_id: int) -> dict[str, Any] | None:
        rows = self._checked(
            self.client.table("tasks").select("*").eq("id", task_id).limit(1).execute()
        )
        return rows[0] if rows else None

    def update(self, task_id: int, task: TaskUpdate) -> dict[str, Any] | None:
        payload = task.model_dump(mode="json", exclude_unset=True)
        payload["updated_at"] = datetime.now(UTC).isoformat()
        rows = self._checked(self.client.table("tasks").update(payload).eq("id", task_id).execute())
        return rows[0] if rows else None

    def delete(self, task_id: int) -> bool:
        rows = self._checked(self.client.table("tasks").delete().eq("id", task_id).execute())
        return bool(rows)
