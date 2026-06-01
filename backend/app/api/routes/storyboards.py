from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.models import Storyboard
from app.db.session import get_db
from app.schemas.common import JsonDocument
from app.services.ai_service import dumps_json, loads_json

router = APIRouter(prefix="/projects/{project_id}/storyboard", tags=["storyboards"])


@router.get("")
def get_storyboard(project_id: int, db: Session = Depends(get_db)):
    storyboard = db.query(Storyboard).filter(Storyboard.project_id == project_id).first()
    if not storyboard:
        raise HTTPException(status_code=404, detail="还没有生成分镜表")
    return loads_json(storyboard.data)


@router.put("")
def update_storyboard(project_id: int, payload: JsonDocument, db: Session = Depends(get_db)):
    storyboard = db.query(Storyboard).filter(Storyboard.project_id == project_id).first()
    if not storyboard:
        storyboard = Storyboard(project_id=project_id, data=dumps_json(payload.data))
        db.add(storyboard)
    else:
        storyboard.data = dumps_json(payload.data)
    db.commit()
    return payload.data
