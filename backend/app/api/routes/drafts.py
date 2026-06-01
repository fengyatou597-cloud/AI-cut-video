import json
import shutil
import subprocess
import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.models import DraftExport, Project, Storyboard, Timeline
from app.db.session import get_db
from app.services.jianying_service import inspect_draft_environment

router = APIRouter(prefix="/projects/{project_id}/draft", tags=["drafts"])


@router.get("/environment")
def get_draft_environment(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    storyboard = db.query(Storyboard).filter(Storyboard.project_id == project_id).first()
    timeline = db.query(Timeline).filter(Timeline.project_id == project_id).first()
    environment = inspect_draft_environment()
    environment["has_storyboard"] = storyboard is not None
    environment["has_timeline"] = timeline is not None
    environment["ready_to_export"] = storyboard is not None and timeline is not None
    if not environment["ready_to_export"]:
        environment["blockers"] = [
            *environment["blockers"],
            "还没有生成 storyboard 或 timeline，暂不能导出草稿。",
        ]
    return environment


@router.post("/generate")
def generate_draft(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    storyboard = db.query(Storyboard).filter(Storyboard.project_id == project_id).first()
    timeline = db.query(Timeline).filter(Timeline.project_id == project_id).first()
    if not storyboard or not timeline:
        raise HTTPException(status_code=400, detail="请先生成 storyboard 和 timeline")

    result = _run_draft_job(project_id)
    export = DraftExport(project_id=project_id, output_path=result["output_path"], mode=result["mode"], message=result["message"])
    db.add(export)
    db.commit()
    db.refresh(export)
    return export


@router.get("/exports")
def list_exports(project_id: int, db: Session = Depends(get_db)):
    exports = db.query(DraftExport).filter(DraftExport.project_id == project_id).order_by(DraftExport.created_at.desc()).all()
    return [_export_payload(item) for item in exports]


@router.get("/exports/{export_id}/download")
def download_export(project_id: int, export_id: int, db: Session = Depends(get_db)):
    export = db.get(DraftExport, export_id)
    if not export or export.project_id != project_id:
        raise HTTPException(status_code=404, detail="导出记录不存在")

    output_path = Path(export.output_path)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="导出目录不存在，可能已被移动或删除")

    downloads_dir = settings.storage_path / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    zip_base = downloads_dir / f"project_{project_id}_export_{export_id}"
    zip_path = Path(str(zip_base) + ".zip")
    if zip_path.exists():
        zip_path.unlink()

    if output_path.is_dir():
        shutil.make_archive(str(zip_base), "zip", root_dir=str(output_path))
    else:
        temp_dir = downloads_dir / f"project_{project_id}_export_{export_id}_single"
        temp_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output_path, temp_dir / output_path.name)
        shutil.make_archive(str(zip_base), "zip", root_dir=str(temp_dir))

    return FileResponse(path=str(zip_path), filename=zip_path.name, media_type="application/zip")


def _run_draft_job(project_id: int) -> dict:
    backend_dir = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, "-m", "app.jobs.generate_draft_job", str(project_id)],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    output = (result.stdout or "").strip().splitlines()
    if result.returncode != 0 or not output:
        detail = result.stderr or result.stdout or "草稿生成任务没有返回结果"
        raise HTTPException(status_code=500, detail=detail[-2000:])
    try:
        payload = json.loads(output[-1])
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"无法解析草稿生成结果：{exc}; output={output[-1][-1000:]}") from exc
    if payload.get("error"):
        raise HTTPException(status_code=500, detail=payload["error"])
    return payload


def _export_payload(export: DraftExport) -> dict:
    output_path = Path(export.output_path)
    return {
        "id": export.id,
        "project_id": export.project_id,
        "output_path": export.output_path,
        "output_exists": output_path.exists(),
        "mode": export.mode,
        "message": export.message,
        "created_at": export.created_at,
        "download_url": f"/api/projects/{export.project_id}/draft/exports/{export.id}/download",
    }
