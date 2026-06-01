import json
import mimetypes
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException, UploadFile
from app.core.config import settings

VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac"}


def classify_asset(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in VIDEO_SUFFIXES:
        return "video"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in AUDIO_SUFFIXES:
        return "audio"
    guessed, _ = mimetypes.guess_type(filename)
    if guessed and guessed.startswith("video/"):
        return "video"
    if guessed and guessed.startswith("image/"):
        return "image"
    if guessed and guessed.startswith("audio/"):
        return "audio"
    raise HTTPException(status_code=400, detail="仅支持 mp4/mov、png/jpg/webp、mp3/wav 等常见素材格式")


def save_upload(project_id: int, file: UploadFile, category: str) -> Path:
    original = Path(file.filename or "asset").name
    suffix = Path(original).suffix.lower()
    safe_name = f"{uuid4().hex}{suffix}"
    target_dir = settings.storage_path / "projects" / str(project_id) / category
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / safe_name
    with target_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return target_path


def inspect_asset(path: Path, asset_type: str) -> dict:
    metadata = {"duration": None, "width": None, "height": None, "thumbnail_path": None, "keyframe_paths": []}
    probe = _ffprobe(path)
    if probe:
        streams = probe.get("streams", [])
        format_data = probe.get("format", {})
        if format_data.get("duration"):
            metadata["duration"] = round(float(format_data["duration"]), 3)
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        if video_stream:
            metadata["width"] = video_stream.get("width")
            metadata["height"] = video_stream.get("height")

    if asset_type == "video":
        metadata["keyframe_paths"] = extract_keyframes(path, metadata.get("duration") or 0)
        metadata["thumbnail_path"] = metadata["keyframe_paths"][0] if metadata["keyframe_paths"] else None
    elif asset_type == "image":
        metadata["thumbnail_path"] = str(path)
    return metadata


def extract_keyframes(video_path: Path, duration: float, count: int = 5) -> list[str]:
    thumb_dir = video_path.parent / f"{video_path.stem}_thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    if duration <= 0:
        timestamps = [0]
    else:
        actual_count = 3 if duration < 20 else count
        timestamps = [round(duration * (i + 1) / (actual_count + 1), 2) for i in range(actual_count)]

    outputs: list[str] = []
    for index, timestamp in enumerate(timestamps, start=1):
        output = thumb_dir / f"keyframe_{index:02d}.jpg"
        command = [
            "ffmpeg",
            "-y",
            "-ss",
            str(timestamp),
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(output),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            outputs.append(str(output))
        except (FileNotFoundError, subprocess.CalledProcessError):
            break
    return outputs


def public_media_path(path: str | None) -> str | None:
    if not path:
        return None
    try:
        relative = Path(path).resolve().relative_to(settings.storage_path)
        return "/media/" + relative.as_posix()
    except ValueError:
        return path


def serialize_asset(asset) -> dict:
    ai_tags = json.loads(asset.ai_tags or "[]")
    if isinstance(ai_tags, list):
        ai_tags = {"tags": ai_tags}
    return {
        "id": asset.id,
        "project_id": asset.project_id,
        "filename": asset.filename,
        "path": asset.path,
        "asset_type": asset.asset_type,
        "duration": asset.duration,
        "width": asset.width,
        "height": asset.height,
        "thumbnail_path": public_media_path(asset.thumbnail_path),
        "keyframe_paths": [public_media_path(p) for p in json.loads(asset.keyframe_paths or "[]")],
        "user_tags": json.loads(asset.user_tags or "[]"),
        "ai_tags": ai_tags,
        "created_at": asset.created_at,
    }


def delete_asset_files(asset) -> None:
    paths = [asset.path, asset.thumbnail_path]
    try:
        paths.extend(json.loads(asset.keyframe_paths or "[]"))
    except json.JSONDecodeError:
        pass

    for raw_path in paths:
        if not raw_path:
            continue
        path = Path(raw_path)
        _safe_unlink(path)

    if asset.asset_type == "video" and asset.path:
        thumb_dir = Path(asset.path).parent / f"{Path(asset.path).stem}_thumbs"
        _safe_remove_empty_tree(thumb_dir)


def _safe_unlink(path: Path) -> None:
    try:
        resolved = path.resolve()
        resolved.relative_to(settings.storage_path.resolve())
    except (OSError, ValueError):
        return
    if resolved.is_file():
        try:
            resolved.unlink()
        except OSError:
            pass


def _safe_remove_empty_tree(path: Path) -> None:
    try:
        resolved = path.resolve()
        resolved.relative_to(settings.storage_path.resolve())
    except (OSError, ValueError):
        return
    if not resolved.is_dir():
        return
    try:
        shutil.rmtree(resolved)
    except OSError:
        pass


def _ffprobe(path: Path) -> dict | None:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return json.loads(result.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError):
        return None
