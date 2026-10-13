"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes.tasks import router as tasks_router
from app.core.config import get_settings

app = FastAPI(title=get_settings().app_name, version="1.0.0")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(tasks_router)

# Serve the browser UI at /; API and documentation routes are registered above it.
app.mount("/", StaticFiles(directory="public", html=True), name="web")
