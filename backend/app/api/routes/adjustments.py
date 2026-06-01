from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Project, Storyboard, Subtitle, Timeline
from app.db.session import get_db
from app.schemas.common import AiEditInstruction
from app.services.adjustment_service import apply_edit_instruction
from app.services.ai_service import dumps_json as dumps_storyboard_json, loads_json as loads_storyboard_json
from app.services.timeline_service import dumps_json as dumps_timeline_json, loads_json as loads_timeline_json

router = APIRouter(prefix="/projects/{project_id}/adjustments", tags=["adjustments"])


@router.post("/apply")
def apply_adjustment(project_id: int, payload: AiEditInstruction, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    storyboard_record = db.query(Storyboard).filter(Storyboard.project_id == project_id).first()
    timeline_record = db.query(Timeline).filter(Timeline.project_id == project_id).first()
    if not storyboard_record or not timeline_record:
        raise HTTPException(status_code=400, detail="请先生成分镜表和 Timeline，再让 AI 按要求修改。")

    subtitle_record = db.query(Subtitle).filter(Subtitle.project_id == project_id).order_by(Subtitle.created_at.desc()).first()
    try:
        result = apply_edit_instruction(
            project=project,
            instruction=payload.instruction,
            storyboard=loads_storyboard_json(storyboard_record.data) or {},
            timeline=loads_timeline_json(timeline_record.data) or {},
            subtitle_content=subtitle_record.content if subtitle_record else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    storyboard_record.data = dumps_storyboard_json(result["storyboard"])
    timeline_record.data = dumps_timeline_json(result["timeline"])
    if subtitle_record and result.get("subtitle_text"):
        subtitle_record.content = result["subtitle_text"]
    db.commit()

    return {
        "storyboard": result["storyboard"],
        "timeline": result["timeline"],
        "summary": result.get("summary", []),
        "notes": result.get("notes", []),
        "source": result.get("source", "unknown"),
    }
