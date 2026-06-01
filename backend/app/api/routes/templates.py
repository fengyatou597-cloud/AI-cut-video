from fastapi import APIRouter
from app.services.style_templates import PACING_OPTIONS, PLATFORMS, STYLE_TEMPLATES, TARGET_DURATIONS

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("")
def get_templates():
    return {
        "platforms": PLATFORMS,
        "target_durations": TARGET_DURATIONS,
        "pacing_options": PACING_OPTIONS,
        "style_templates": STYLE_TEMPLATES,
    }
