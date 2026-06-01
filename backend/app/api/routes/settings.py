from pydantic import BaseModel
from fastapi import APIRouter
from app.services.settings_service import discover_jianying_draft_dirs, get_app_settings, save_user_config

router = APIRouter(prefix="/settings", tags=["settings"])


class AppSettingsUpdate(BaseModel):
    jianying_drafts_dir: str = ""
    fallback_export_dir: str = ""
    ai_enabled: bool = False
    ai_provider: str = "openai_compatible"
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_text_model: str = ""
    ai_vision_model: str = ""
    ai_text_base_url: str = ""
    ai_text_api_key: str = ""
    ai_vision_base_url: str = ""
    ai_vision_api_key: str = ""


@router.get("")
def read_settings():
    return get_app_settings()


@router.get("/draft-dir-candidates")
def read_draft_dir_candidates():
    return discover_jianying_draft_dirs()


@router.put("")
def update_settings(payload: AppSettingsUpdate):
    save_user_config(payload.model_dump())
    return get_app_settings()
