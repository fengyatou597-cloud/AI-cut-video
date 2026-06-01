from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models import Asset, DraftExport, Project, Script, Storyboard, Timeline
from app.db.session import get_db
from app.schemas.common import ProjectCreate, ProjectRead

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/overview")
def list_project_overview(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return [_project_overview(project, db) for project in projects]


@router.get("/{project_id}/overview")
def get_project_overview(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return _project_overview(project, db)


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.post("", response_model=ProjectRead)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _project_overview(project: Project, db: Session) -> dict:
    script_count = db.query(func.count(Script.id)).filter(Script.project_id == project.id).scalar() or 0
    asset_count = db.query(func.count(Asset.id)).filter(Asset.project_id == project.id).scalar() or 0
    storyboard = db.query(Storyboard).filter(Storyboard.project_id == project.id).first()
    timeline = db.query(Timeline).filter(Timeline.project_id == project.id).first()
    export_count = db.query(func.count(DraftExport.id)).filter(DraftExport.project_id == project.id).scalar() or 0

    steps = [
        {"key": "script", "label": "文稿", "done": script_count > 0, "href": f"/projects/{project.id}/script"},
        {"key": "storyboard", "label": "分镜", "done": storyboard is not None, "href": f"/projects/{project.id}/storyboard"},
        {"key": "assets", "label": "素材", "done": asset_count > 0, "href": f"/projects/{project.id}/assets"},
        {"key": "timeline", "label": "Timeline", "done": timeline is not None, "href": f"/projects/{project.id}/timeline"},
        {"key": "draft", "label": "导出", "done": export_count > 0, "href": f"/projects/{project.id}/draft"},
    ]
    next_step = next((step for step in steps if not step["done"]), steps[-1])

    return {
        "id": project.id,
        "title": project.title,
        "platform": project.platform,
        "target_duration": project.target_duration,
        "style": project.style,
        "pacing": project.pacing,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "script_count": script_count,
        "asset_count": asset_count,
        "has_storyboard": storyboard is not None,
        "has_timeline": timeline is not None,
        "export_count": export_count,
        "progress": round(sum(1 for step in steps if step["done"]) / len(steps), 2),
        "steps": steps,
        "next_step": next_step,
    }
