import json
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.models import Project, Script, Storyboard, Subtitle
from app.db.session import get_db
from app.schemas.common import ScriptRead, SubtitleRead
from app.services.ai_service import build_storyboard, dumps_json, loads_json
from app.services.asset_service import save_upload
from app.services.script_service import read_script_upload
from app.services.subtitle_service import parse_srt, read_srt_upload, srt_duration

router = APIRouter(prefix="/projects/{project_id}/script", tags=["scripts"])


@router.post("/upload", response_model=ScriptRead)
def upload_script(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    content = read_script_upload(file)
    path = save_upload(project_id, file, "scripts")
    path.write_text(content, encoding="utf-8")
    script = Script(project_id=project_id, filename=file.filename or "script.txt", path=str(path), content=content)
    db.add(script)
    db.commit()
    db.refresh(script)
    return script


@router.get("/latest", response_model=ScriptRead | None)
def get_latest_script(project_id: int, db: Session = Depends(get_db)):
    return db.query(Script).filter(Script.project_id == project_id).order_by(Script.created_at.desc()).first()


@router.post("/subtitles/upload", response_model=SubtitleRead)
def upload_subtitles(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    content = read_srt_upload(file)
    cues = parse_srt(content)
    if not cues:
        raise HTTPException(status_code=400, detail="没有识别到有效 SRT 字幕时间轴")
    path = save_upload(project_id, file, "subtitles")
    path.write_text(content, encoding="utf-8")
    subtitle = Subtitle(
        project_id=project_id,
        filename=file.filename or "subtitles.srt",
        path=str(path),
        content=content,
        cue_count=len(cues),
        duration=srt_duration(content),
    )
    db.add(subtitle)
    db.commit()
    db.refresh(subtitle)
    return subtitle


@router.get("/subtitles/latest", response_model=SubtitleRead | None)
def get_latest_subtitles(project_id: int, db: Session = Depends(get_db)):
    return db.query(Subtitle).filter(Subtitle.project_id == project_id).order_by(Subtitle.created_at.desc()).first()


@router.post("/generate-storyboard")
def generate_storyboard(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    script = db.query(Script).filter(Script.project_id == project_id).order_by(Script.created_at.desc()).first()
    if not script:
        raise HTTPException(status_code=400, detail="请先上传文稿")
    data = build_storyboard(project, script.content)
    existing = db.query(Storyboard).filter(Storyboard.project_id == project_id).first()
    if existing:
        existing.data = dumps_json(data)
    else:
        db.add(Storyboard(project_id=project_id, data=dumps_json(data)))
    db.commit()
    return data
