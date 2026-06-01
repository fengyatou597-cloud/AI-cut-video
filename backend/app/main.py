from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import adjustments, assets, demo, drafts, projects, scripts, settings as settings_routes, storyboards, templates, timelines
from app.core.config import settings
from app.db.init_db import init_db

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


app.include_router(projects.router, prefix="/api")
app.include_router(demo.router, prefix="/api")
app.include_router(scripts.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(storyboards.router, prefix="/api")
app.include_router(timelines.router, prefix="/api")
app.include_router(adjustments.router, prefix="/api")
app.include_router(drafts.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(templates.router, prefix="/api")
app.mount("/media", StaticFiles(directory=str(settings.storage_path)), name="media")

if FRONTEND_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS)), name="frontend-assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Frontend build not found. Run npm.cmd run build in the frontend directory."}
