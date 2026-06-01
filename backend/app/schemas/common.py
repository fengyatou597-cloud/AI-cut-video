from datetime import datetime
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    title: str
    platform: str
    target_duration: str
    style: str
    pacing: str
    needs_hook: bool = True
    needs_broll: bool = True
    needs_research_visuals: bool = False


class ProjectUpdate(ProjectCreate):
    pass


class ProjectRead(ProjectCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScriptRead(BaseModel):
    id: int
    project_id: int
    filename: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SubtitleRead(BaseModel):
    id: int
    project_id: int
    filename: str
    content: str
    cue_count: int
    duration: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetRead(BaseModel):
    id: int
    project_id: int
    filename: str
    path: str
    asset_type: str
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    thumbnail_path: str | None = None
    keyframe_paths: list[str] = Field(default_factory=list)
    user_tags: list[str] = Field(default_factory=list)
    ai_tags: list[str] = Field(default_factory=list)
    created_at: datetime


class JsonDocument(BaseModel):
    data: dict


class AiEditInstruction(BaseModel):
    instruction: str


class DraftExportRead(BaseModel):
    id: int
    project_id: int
    output_path: str
    mode: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}
