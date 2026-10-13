"""Task use cases and not-found handling."""

from typing import Any

from fastapi import HTTPException, status

from app.models.task import TaskPriority, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def create(self, task: TaskCreate) -> dict[str, Any]:
        return self.repository.create(task)

    def list(
        self,
        *,
        status_filter: TaskStatus | None,
        priority: TaskPriority | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        return self.repository.list(
            status=status_filter,
            priority=priority,
            search=search,
            limit=limit,
            offset=offset,
        )

    def get(self, task_id: int) -> dict[str, Any]:
        task = self.repository.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    def update(self, task_id: int, task: TaskUpdate) -> dict[str, Any]:
        updated = self.repository.update(task_id, task)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return updated

    def delete(self, task_id: int) -> None:
        if not self.repository.delete(task_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
