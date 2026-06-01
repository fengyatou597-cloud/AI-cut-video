from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.models import Asset, Storyboard, Subtitle, Timeline
from app.db.session import get_db
from app.schemas.common import JsonDocument
from app.services.ai_service import loads_json as load_storyboard_json
from app.services.timeline_service import build_mock_timeline, dumps_json, loads_json

router = APIRouter(prefix="/projects/{project_id}/timeline", tags=["timeline"])


@router.get("")
def get_timeline(project_id: int, db: Session = Depends(get_db)):
    timeline = db.query(Timeline).filter(Timeline.project_id == project_id).first()
    if not timeline:
        raise HTTPException(status_code=404, detail="还没有生成 timeline")
    return loads_json(timeline.data)


@router.post("/generate")
def generate_timeline(project_id: int, db: Session = Depends(get_db)):
    storyboard = db.query(Storyboard).filter(Storyboard.project_id == project_id).first()
    if not storyboard:
        raise HTTPException(status_code=400, detail="请先生成分镜表")
    assets = db.query(Asset).filter(Asset.project_id == project_id).order_by(Asset.created_at.asc()).all()
    subtitles = db.query(Subtitle).filter(Subtitle.project_id == project_id).order_by(Subtitle.created_at.desc()).first()
    data = build_mock_timeline(load_storyboard_json(storyboard.data) or {}, assets, subtitles.content if subtitles else None)
    existing = db.query(Timeline).filter(Timeline.project_id == project_id).first()
    if existing:
        existing.data = dumps_json(data)
    else:
        db.add(Timeline(project_id=project_id, data=dumps_json(data)))
    db.commit()
    return data


@router.put("")
def update_timeline(project_id: int, payload: JsonDocument, db: Session = Depends(get_db)):
    timeline = db.query(Timeline).filter(Timeline.project_id == project_id).first()
    if not timeline:
        timeline = Timeline(project_id=project_id, data=dumps_json(payload.data))
        db.add(timeline)
    else:
        timeline.data = dumps_json(payload.data)
    db.commit()
    return payload.data
