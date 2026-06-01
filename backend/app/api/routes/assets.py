import json
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.db.models import Asset, Project, Timeline
from app.db.session import get_db
from app.services.ai_service import ai_status, analyze_asset_with_ai
from app.services.asset_service import classify_asset, delete_asset_files, inspect_asset, save_upload, serialize_asset

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["assets"])


@router.get("")
def list_assets(project_id: int, db: Session = Depends(get_db)):
    assets = db.query(Asset).filter(Asset.project_id == project_id).order_by(Asset.created_at.desc()).all()
    return [serialize_asset(asset) for asset in assets]


@router.post("/analyze-all")
def analyze_all_assets(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    assets = db.query(Asset).filter(Asset.project_id == project_id).order_by(Asset.created_at.asc()).all()
    if not assets:
        return {"updated": 0, "failed": 0, "assets": []}

    status = ai_status()
    if not status["text_ready"] and not status["vision_ready"]:
        raise HTTPException(status_code=400, detail="AI 配置不完整：" + "；".join(status["blockers"]))

    updated = 0
    failed = 0
    for asset in assets:
        if _try_update_ai_tags(asset, db):
            updated += 1
        else:
            failed += 1
    refreshed = db.query(Asset).filter(Asset.project_id == project_id).order_by(Asset.created_at.desc()).all()
    return {"updated": updated, "failed": failed, "assets": [serialize_asset(asset) for asset in refreshed]}


@router.post("/upload")
def upload_asset(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    asset_type = classify_asset(file.filename or "asset")
    path = save_upload(project_id, file, "assets")
    metadata = inspect_asset(path, asset_type)
    asset = Asset(
        project_id=project_id,
        filename=file.filename or path.name,
        path=str(path),
        asset_type=asset_type,
        duration=metadata["duration"],
        width=metadata["width"],
        height=metadata["height"],
        thumbnail_path=metadata["thumbnail_path"],
        keyframe_paths=json.dumps(metadata["keyframe_paths"], ensure_ascii=False),
        user_tags="[]",
        ai_tags="[]",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    _try_update_ai_tags(asset, db)
    return serialize_asset(asset)


@router.post("/{asset_id}/analyze")
def analyze_asset(project_id: int, asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset or asset.project_id != project_id:
        raise HTTPException(status_code=404, detail="素材不存在")
    result = _try_update_ai_tags(asset, db)
    if not result:
        status = ai_status()
        if not status["text_ready"] and not status["vision_ready"]:
            raise HTTPException(status_code=400, detail="AI 配置不完整：" + "；".join(status["blockers"]))
        raise HTTPException(status_code=400, detail="AI 识别失败。请检查模型名是否支持当前接口；视频素材还需要 ffmpeg 生成关键帧后，视觉模型才能看到画面。")
    return serialize_asset(asset)


@router.delete("/{asset_id}")
def delete_asset(project_id: int, asset_id: int, db: Session = Depends(get_db)):
    return _delete_asset_record(project_id, asset_id, db)


@router.post("/{asset_id}/delete")
def delete_asset_by_post(project_id: int, asset_id: int, db: Session = Depends(get_db)):
    return _delete_asset_record(project_id, asset_id, db)


def _delete_asset_record(project_id: int, asset_id: int, db: Session) -> dict:
    asset = db.get(Asset, asset_id)
    if not asset or asset.project_id != project_id:
        raise HTTPException(status_code=404, detail="素材不存在")

    delete_asset_files(asset)
    db.delete(asset)

    # 素材变化后旧 timeline 可能还引用已删除文件，直接清掉更安全。
    timeline = db.query(Timeline).filter(Timeline.project_id == project_id).first()
    if timeline:
        db.delete(timeline)

    db.commit()
    return {"deleted": True, "asset_id": asset_id, "timeline_invalidated": bool(timeline)}


def _try_update_ai_tags(asset: Asset, db: Session) -> dict | None:
    result = analyze_asset_with_ai(asset)
    if not result:
        return None
    tags = result.get("tags") or []
    summary = result.get("summary") or ""
    payload = {
        "summary": summary,
        "tags": tags,
        "best_use": result.get("best_use") or [],
        "mood": result.get("mood") or "",
        "pace": result.get("pace") or "",
        "visual_quality": result.get("visual_quality") or "",
        "suggested_effects": result.get("suggested_effects") or [],
    }
    asset.ai_tags = json.dumps(payload, ensure_ascii=False)
    db.commit()
    db.refresh(asset)
    return payload
