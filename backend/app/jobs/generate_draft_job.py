import json
import sys
from pathlib import Path

from app.db.models import Asset, DraftExport, Project, Storyboard, Subtitle, Timeline
from app.db.session import SessionLocal
from app.services.ai_service import loads_json as load_storyboard_json
from app.services.jianying_service import generate_draft_package
from app.services.settings_service import get_jianying_drafts_dir
from app.services.timeline_service import _asset_signature, build_mock_timeline, dumps_json as dump_timeline_json, loads_json as load_timeline_json


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "missing project_id"}, ensure_ascii=True))
        return 2
    project_id = int(sys.argv[1])
    db = SessionLocal()
    try:
        project = db.get(Project, project_id)
        storyboard = db.query(Storyboard).filter(Storyboard.project_id == project_id).first()
        timeline = db.query(Timeline).filter(Timeline.project_id == project_id).first()
        if not project or not storyboard or not timeline:
            print(json.dumps({"error": "missing project/storyboard/timeline"}, ensure_ascii=True))
            return 3

        draft_dir = get_jianying_drafts_dir()
        debug_path = Path("storage") / "draft_job_debug.json"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(
            json.dumps(
                {
                    "project_id": project_id,
                    "cwd": str(Path.cwd()),
                    "sys_executable": sys.executable,
                    "draft_dir": draft_dir,
                    "draft_dir_exists": bool(draft_dir and Path(draft_dir).exists()),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        storyboard_data = load_storyboard_json(storyboard.data) or {}
        timeline_data = load_timeline_json(timeline.data) or {}
        assets = db.query(Asset).filter(Asset.project_id == project_id).all()
        subtitles = db.query(Subtitle).filter(Subtitle.project_id == project_id).order_by(Subtitle.created_at.desc()).first()
        subtitle_content = subtitles.content if subtitles else None
        if (
            _timeline_needs_asset_refresh(timeline_data, assets)
            or _timeline_asset_signature_changed(timeline_data, assets)
            or _timeline_needs_audio_refresh(timeline_data, assets)
            or _timeline_needs_subtitle_refresh(timeline_data, subtitle_content)
        ):
            timeline_data = build_mock_timeline(storyboard_data, assets, subtitle_content)
            timeline.data = dump_timeline_json(timeline_data)
            db.commit()

        result = generate_draft_package(project, storyboard_data, timeline_data, _latest_successful_draft_title(db, project_id))
        print(json.dumps(dict(result), ensure_ascii=True))
        return 0
    finally:
        db.close()


def _timeline_needs_asset_refresh(timeline: dict, assets: list[Asset]) -> bool:
    has_visual_assets = any(asset.asset_type in {"video", "image"} for asset in assets)
    if not has_visual_assets:
        return False
    video_items = []
    for track in timeline.get("tracks", []):
        if track.get("type") == "video":
            video_items = track.get("items", [])
            break
    return bool(video_items) and not any(item.get("asset_path") for item in video_items)


def _timeline_asset_signature_changed(timeline: dict, assets: list[Asset]) -> bool:
    return timeline.get("asset_signature") != _asset_signature(assets)


def _timeline_needs_audio_refresh(timeline: dict, assets: list[Asset]) -> bool:
    has_audio_assets = any(asset.asset_type == "audio" for asset in assets)
    if not has_audio_assets:
        return False
    for track in timeline.get("tracks", []):
        if track.get("type") == "audio":
            return not any(item.get("asset_path") for item in track.get("items", []))
    return True


def _timeline_needs_subtitle_refresh(timeline: dict, subtitle_content: str | None) -> bool:
    return bool(subtitle_content) and timeline.get("subtitle_source") != "uploaded_srt"


def _latest_successful_draft_title(db, project_id: int) -> str | None:
    export = (
        db.query(DraftExport)
        .filter(DraftExport.project_id == project_id, DraftExport.mode == "pyjianyingdraft")
        .order_by(DraftExport.created_at.desc())
        .first()
    )
    if not export:
        return None
    title = Path(export.output_path).name.strip()
    return title or None


if __name__ == "__main__":
    raise SystemExit(main())
