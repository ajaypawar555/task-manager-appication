"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes.tasks import router as tasks_router
from app.core.config import get_settings

app = FastAPI(title=get_settings().app_name, version="1.0.0")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(tasks_router)

# Vercel serves files in `public/` from its CDN and may omit them from the Python
# function bundle. Mount the UI for local development only when that directory exists.
public_dir = Path(__file__).resolve().parent.parent / "public"
if public_dir.is_dir():
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="web")
