import importlib.util
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from app.core.config import settings
from app.services.settings_service import get_fallback_export_root, get_jianying_drafts_dir, get_project_fallback_export_dir


class DraftGenerationResult(dict):
    pass


def inspect_draft_environment() -> dict:
    drafts_dir = get_jianying_drafts_dir()
    drafts_path = Path(drafts_dir) if drafts_dir else None
    has_drafts_dir = bool(drafts_dir)
    drafts_dir_exists = bool(drafts_path and drafts_path.exists() and drafts_path.is_dir())
    pyjianying_available = importlib.util.find_spec("pyJianYingDraft") is not None
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")

    can_generate_direct = has_drafts_dir and drafts_dir_exists and pyjianying_available
    blockers = []
    if not has_drafts_dir:
        blockers.append("未配置 JIANYING_DRAFTS_DIR，所以会输出 timeline fallback 包。")
    elif not drafts_dir_exists:
        blockers.append("已配置 JIANYING_DRAFTS_DIR，但目录不存在或不可访问。")
    if not pyjianying_available:
        blockers.append("当前 Python 环境未安装 pyJianYingDraft。")
    if not ffmpeg_path:
        blockers.append("未在 PATH 中找到 ffmpeg，视频素材元信息和关键帧提取会受限。")
    if not ffprobe_path:
        blockers.append("未在 PATH 中找到 ffprobe，素材时长和分辨率提取会受限。")

    return {
        "configured_drafts_dir": drafts_dir,
        "fallback_export_dir": str(get_fallback_export_root()),
        "has_drafts_dir": has_drafts_dir,
        "drafts_dir_exists": drafts_dir_exists,
        "pyjianying_available": pyjianying_available,
        "ffmpeg_available": ffmpeg_path is not None,
        "ffmpeg_path": ffmpeg_path,
        "ffprobe_available": ffprobe_path is not None,
        "ffprobe_path": ffprobe_path,
        "direct_draft_available": can_generate_direct,
        "export_mode": "pyjianyingdraft" if can_generate_direct else "fallback_timeline_package",
        "expected_outputs": expected_export_outputs(can_generate_direct),
        "blockers": blockers,
        "notes": [
            "本项目不会自动点击或控制剪映。",
            "直接草稿生成依赖 pyJianYingDraft 和可访问的剪映草稿目录。",
            "fallback 模式仍会输出 storyboard.json、timeline.json、subtitles.srt 和说明文件。",
        ],
    }


def expected_export_outputs(direct_draft_available: bool = False) -> list[dict]:
    outputs = [
        {"name": "storyboard.json", "description": "确认后的分镜表"},
        {"name": "timeline.json", "description": "剪映草稿生成器可消费的中间 timeline"},
        {"name": "subtitles.srt", "description": "由字幕轨道生成的 SRT 字幕"},
        {"name": "draft_generation_notes.md", "description": "导出说明和剪映版本限制"},
    ]
    if direct_draft_available:
        outputs.insert(0, {"name": "剪映草稿文件夹", "description": "pyJianYingDraft 生成的 Jianying / CapCut 草稿"})
    return outputs


def generate_draft_package(project, storyboard: dict, timeline: dict, preferred_draft_title: str | None = None) -> DraftGenerationResult:
    safe_title = _safe_name(project.title)
    work_dir = _unique_output_dir(settings.storage_path / "draft_work" / f"project_{project.id}" / safe_title)
    work_dir.mkdir(parents=True, exist_ok=True)
    _write_package_files(work_dir, storyboard, timeline)

    py_result = _try_pyjianying(project, safe_title, timeline, work_dir, preferred_draft_title)
    if py_result:
        return py_result

    fallback_dir = _unique_output_dir(get_project_fallback_export_dir(project.id, safe_title))
    try:
        fallback_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        fallback_dir = _unique_output_dir(settings.storage_path / "draft_exports" / f"project_{project.id}" / safe_title)
        fallback_dir.mkdir(parents=True, exist_ok=True)

    _write_package_files(fallback_dir, storyboard, timeline)
    error_file = work_dir / "pyjianying_error.txt"
    if error_file.exists():
        (fallback_dir / "pyjianying_error.txt").write_text(error_file.read_text(encoding="utf-8"), encoding="utf-8")

    return DraftGenerationResult(
        output_path=str(fallback_dir),
        mode="fallback_timeline_package",
        message="????????????????? storyboard.json?timeline.json?subtitles.srt ????????? pyjianying_error.txt ????????????",
    )


def _try_pyjianying(project, safe_title: str, timeline: dict, fallback_dir: Path, preferred_draft_title: str | None = None) -> DraftGenerationResult | None:
    drafts_dir = get_jianying_drafts_dir()
    if not drafts_dir:
        return None
    try:
        import pyJianYingDraft as draft  # type: ignore
    except Exception:
        return None

    try:
        draft_folder = draft.DraftFolder(drafts_dir)
        draft_title = _safe_name(preferred_draft_title) if preferred_draft_title else _stable_draft_title(safe_title)
        _backup_existing_draft(Path(drafts_dir), draft_title)
        width, height = _canvas_size(project.platform, timeline)
        script = draft_folder.create_draft(draft_title, width, height)
        script.add_track(draft.TrackType.video, "video")
        script.add_track(draft.TrackType.text, "title_text", relative_index=2)
        script.add_track(draft.TrackType.text, "subtitle", relative_index=1)
        script.add_track(draft.TrackType.audio, "audio")

        for item in _track_items(timeline, "video"):
            if not item.get("asset_path"):
                continue
            target_range = draft.trange(_sec(item.get("start", 0)), _sec(item.get("duration", 1)))
            source_range = draft.trange(_sec(item.get("source_start", 0)), _sec(item.get("source_duration", item.get("duration", 1))))
            segment = draft.VideoSegment(
                item["asset_path"],
                target_range,
                source_timerange=source_range,
                clip_settings=_clip_settings_for_motion(draft, item.get("motion")),
            )
            _apply_video_motion(draft, segment, item)
            script.add_segment(segment, "video")

        _add_text_segments(draft, script, _track_items(timeline, "text"))

        srt_path = fallback_dir / "subtitles.srt"
        if srt_path.exists():
            script.import_srt(str(srt_path), track_name="subtitle")

        for item in _track_items(timeline, "audio"):
            if not item.get("asset_path"):
                continue
            target_range = draft.trange(_sec(item.get("start", 0)), _sec(item.get("duration", timeline.get("duration", 1))))
            source_range = draft.trange(_sec(item.get("source_start", 0)), _sec(item.get("duration", timeline.get("duration", 1))))
            segment = draft.AudioSegment(item["asset_path"], target_range, source_timerange=source_range, volume=float(item.get("volume", 1.0)))
            segment.add_fade("0.300s", "0.500s")
            script.add_segment(segment, "audio")

        script.save()
        return DraftGenerationResult(
            output_path=str(Path(drafts_dir) / draft_title),
            mode="pyjianyingdraft",
            message=f"已更新同名剪映草稿：{draft_title}。若剪映列表未刷新，请进入/退出一次已有草稿或重启剪映。",
        )
    except Exception as exc:
        error_file = fallback_dir / "pyjianying_error.txt"
        error_file.write_text(str(exc), encoding="utf-8")
        return DraftGenerationResult(
            output_path=str(fallback_dir),
            mode="pyjianyingdraft_failed_fallback",
            message=f"pyJianYingDraft 调用失败，已降级输出 timeline 包。错误已写入 {error_file}",
        )


def _track_items(timeline: dict, track_type: str) -> list[dict]:
    for track in timeline.get("tracks", []):
        if track.get("type") == track_type:
            return track.get("items", [])
    return []


def _add_text_segments(draft, script, items: list[dict]) -> None:
    track_ends = {"title_text": 0.0}
    for item in sorted(items, key=lambda value: float(value.get("start", 0))):
        start = float(item.get("start", 0))
        duration = float(item.get("duration", 2))
        target_range = draft.trange(_sec(start), _sec(duration))
        segment = draft.TextSegment(
            item.get("text", ""),
            target_range,
            style=draft.TextStyle(size=_text_size(item), color=(1.0, 1.0, 1.0), auto_wrapping=True, max_line_width=0.82),
            clip_settings=draft.ClipSettings(transform_y=_text_y(item)),
        )
        _apply_text_animation(draft, segment, item)
        track_name = _available_text_track(draft, script, track_ends, start)
        script.add_segment(segment, track_name)
        track_ends[track_name] = max(track_ends.get(track_name, 0.0), start + duration)


def _available_text_track(draft, script, track_ends: dict[str, float], start: float) -> str:
    for track_name, end in track_ends.items():
        if start >= end - 0.001:
            return track_name
    track_name = f"title_text_{len(track_ends) + 1}"
    script.add_track(draft.TrackType.text, track_name, relative_index=2 + len(track_ends))
    track_ends[track_name] = 0.0
    return track_name


def _text_size(item: dict) -> float:
    style = str(item.get("style") or "")
    if "big" in style or "keyword" in style:
        return 10.5
    if "quote" in style:
        return 8.2
    return 9.0


def _text_y(item: dict) -> float:
    style = str(item.get("style") or "")
    if "keyword" in style:
        return -0.48
    if "quote" in style:
        return -0.58
    return -0.72


def _clip_settings_for_motion(draft, motion: str | None):
    if motion == "slide_left":
        return draft.ClipSettings(scale_x=1.06, scale_y=1.06, transform_x=0.03)
    if motion == "pan_right":
        return draft.ClipSettings(scale_x=1.08, scale_y=1.08, transform_x=-0.03)
    if motion == "slide_up":
        return draft.ClipSettings(scale_x=1.06, scale_y=1.06, transform_y=-0.03)
    if motion == "punch_in":
        return draft.ClipSettings(scale_x=1.08, scale_y=1.08)
    if motion == "shake_light":
        return draft.ClipSettings(scale_x=1.05, scale_y=1.05, rotation=-1.0)
    return draft.ClipSettings(scale_x=1.03, scale_y=1.03)


def _apply_video_motion(draft, segment, item: dict) -> None:
    duration = float(item.get("duration", 1))
    motion = item.get("motion")
    try:
        intro = _enum_value(draft.IntroType, item.get("animation"))
        if intro and duration >= 2:
            segment.add_animation(intro, duration="0.500s")
    except Exception:
        pass
    try:
        transition = _enum_value(draft.TransitionType, item.get("transition"))
        if transition and duration >= 2.5:
            segment.add_transition(transition, duration="0.350s")
    except Exception:
        pass
    try:
        if motion == "ken_burns_in":
            segment.add_keyframe(draft.KeyframeProperty.uniform_scale, "0.000s", 1.0)
            segment.add_keyframe(draft.KeyframeProperty.uniform_scale, _sec(duration), 1.12)
        elif motion == "ken_burns_out":
            segment.add_keyframe(draft.KeyframeProperty.uniform_scale, "0.000s", 1.12)
            segment.add_keyframe(draft.KeyframeProperty.uniform_scale, _sec(duration), 1.0)
        elif motion == "slide_left":
            segment.add_keyframe(draft.KeyframeProperty.position_x, "0.000s", 0.03)
            segment.add_keyframe(draft.KeyframeProperty.position_x, _sec(duration), -0.03)
        elif motion == "pan_right":
            segment.add_keyframe(draft.KeyframeProperty.position_x, "0.000s", -0.03)
            segment.add_keyframe(draft.KeyframeProperty.position_x, _sec(duration), 0.03)
        elif motion == "punch_in":
            segment.add_keyframe(draft.KeyframeProperty.uniform_scale, "0.000s", 1.0)
            segment.add_keyframe(draft.KeyframeProperty.uniform_scale, "0.250s", 1.09)
        elif motion == "shake_light":
            segment.add_keyframe(draft.KeyframeProperty.rotation, "0.000s", -1.0)
            segment.add_keyframe(draft.KeyframeProperty.rotation, "0.200s", 1.0)
            segment.add_keyframe(draft.KeyframeProperty.rotation, "0.400s", 0.0)
    except Exception:
        pass


def _apply_text_animation(draft, segment, item: dict) -> None:
    try:
        intro = _enum_value(draft.TextIntro, item.get("animation"))
        if intro:
            segment.add_animation(intro, duration="0.450s")
    except Exception:
        pass


def _enum_value(enum_cls, name: str | None):
    if not name:
        return None
    return getattr(enum_cls, name, None)


def _write_package_files(path: Path, storyboard: dict, timeline: dict) -> None:
    _write_json(path / "storyboard.json", storyboard)
    _write_json(path / "timeline.json", timeline)
    _write_srt(path / "subtitles.srt", timeline)
    _write_notes(path / "draft_generation_notes.md")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_srt(path: Path, timeline: dict) -> None:
    lines = []
    index = 1
    previous_end = 0.0
    for item in _track_items(timeline, "subtitle"):
        start = max(float(item.get("start", 0)), previous_end)
        end = start + float(item.get("duration", 1))
        if end <= start:
            end = start + 0.5
        text = item.get("text", "").strip()
        if not text:
            continue
        lines.extend([str(index), f"{_srt_time(start)} --> {_srt_time(end)}", text, ""])
        previous_end = end
        index += 1
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_notes(path: Path) -> None:
    path.write_text(
        "# 剪映草稿生成说明\n\n"
        "本目录是 MVP fallback 输出包。它至少包含：\n\n"
        "- `storyboard.json`：分镜表。\n"
        "- `timeline.json`：可供草稿生成器消费的中间 timeline。\n"
        "- `subtitles.srt`：由 timeline 字幕轨道生成的字幕文件。\n\n"
        "## 版本限制\n\n"
        "- 本项目不通过鼠标/GUI 自动操作剪映。\n"
        "- 若安装 `pyJianYingDraft` 并配置 `JIANYING_DRAFTS_DIR`，后端会尝试直接生成剪映草稿文件夹。\n"
        "- `pyJianYingDraft` 的模板模式受剪映版本限制：剪映 6+ 对 `draft_content.json` 加密，加载 6+ 模板草稿会受限。\n"
        "- 草稿生成功能本身通常支持剪映 5+，但需要在本机剪映版本中实际验证。\n"
        "- 自动导出视频不是本 MVP 范围，且 pyJianYingDraft 的批量导出会涉及 GUI 自动化，本项目第一版不采用。\n",
        encoding="utf-8",
    )


def _srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours, remainder = divmod(ms, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _sec(value: float | int) -> str:
    return f"{float(value):.3f}s"


def _safe_name(name: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]", "_", name).strip()
    return value[:80] or "ai_rough_cut_draft"


def _stable_draft_title(base_title: str) -> str:
    return base_title[:100]


def _backup_existing_draft(drafts_dir: Path, draft_title: str) -> None:
    draft_path = drafts_dir / draft_title
    if not draft_path.exists():
        return
    backup_root = settings.storage_path / "draft_backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = backup_root / f"{draft_title}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"[:120]
    try:
        draft_path.rename(backup_path)
    except OSError:
        shutil.rmtree(draft_path)


def _unique_output_dir(base_dir: Path) -> Path:
    if not base_dir.exists():
        return base_dir
    suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    return base_dir.parent / f"{base_dir.name}_{suffix}"


def _canvas_size(platform: str, timeline: dict | None = None) -> tuple[int, int]:
    canvas = (timeline or {}).get("canvas") or {}
    width = int(canvas.get("width") or 0)
    height = int(canvas.get("height") or 0)
    if width > 0 and height > 0:
        return width, height
    if platform in {"小红书", "抖音", "视频号"}:
        return 1080, 1920
    return 1920, 1080
