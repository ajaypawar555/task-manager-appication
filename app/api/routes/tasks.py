"""Task endpoints."""

import hmac
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from supabase import Client

from app.core.config import get_settings
from app.db.supabase import get_supabase_client
from app.models.task import TaskPriority, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def require_api_token(authorization: Annotated[str | None, Header()] = None) -> None:
    settings = get_settings()
    if not settings.api_auth_enabled:
        return
    expected = settings.api_access_token.get_secret_value()
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
        )


def get_task_service(client: Annotated[Client, Depends(get_supabase_client)]) -> TaskService:
    return TaskService(TaskRepository(client))


ServiceDep = Annotated[TaskService, Depends(get_task_service)]


def database_error() -> HTTPException:
    logger.exception("Task database operation failed")
    return HTTPException(status_code=503, detail="Task storage is temporarily unavailable")


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_token)],
)
def create_task(payload: TaskCreate, service: ServiceDep) -> TaskRead:
    try:
        return service.create(payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise database_error() from exc


@router.get("", response_model=list[TaskRead], dependencies=[Depends(require_api_token)])
def list_tasks(
    service: ServiceDep,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TaskRead]:
    try:
        return service.list(
            status_filter=status_filter,
            priority=priority,
            search=search,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        raise database_error() from exc


@router.get("/{task_id}", response_model=TaskRead, dependencies=[Depends(require_api_token)])
def get_task(task_id: int, service: ServiceDep) -> TaskRead:
    try:
        return service.get(task_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise database_error() from exc


@router.patch("/{task_id}", response_model=TaskRead, dependencies=[Depends(require_api_token)])
def update_task(task_id: int, payload: TaskUpdate, service: ServiceDep) -> TaskRead:
    if not payload.model_fields_set:
        raise HTTPException(status_code=422, detail="At least one field must be provided")
    try:
        return service.update(task_id, payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise database_error() from exc


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_token)],
)
def delete_task(task_id: int, service: ServiceDep) -> Response:
    try:
        service.delete(task_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as exc:
        raise database_error() from exc
