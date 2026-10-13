"""Pydantic models for task API payloads."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.task import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title must not be blank")
        return value


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None

    @field_validator("title", mode="before")
    @classmethod
    def supplied_title_must_not_be_blank_or_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Title cannot be null")
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Title must not be blank")
        return value

    @field_validator("status", "priority", mode="before")
    @classmethod
    def supplied_enum_fields_cannot_be_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class TaskRead(BaseModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
