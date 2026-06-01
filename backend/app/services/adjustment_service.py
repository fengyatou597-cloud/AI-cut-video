import json
import re
from copy import deepcopy

from app.db.models import Project
from app.services.ai_service import _ai_ready, _chat_json
from app.services.subtitle_service import parse_srt
from app.services.timeline_service import dumps_json


def apply_edit_instruction(
    project: Project,
    instruction: str,
    storyboard: dict,
    timeline: dict,
    subtitle_content: str | None = None,
) -> dict:
    instruction = instruction.strip()
    if not instruction:
        raise ValueError("请先输入你希望 AI 修改什么。")

    before = {
        "storyboard": deepcopy(storyboard or {}),
        "timeline": deepcopy(timeline or {}),
        "subtitle_content": subtitle_content or "",
    }

    if _ai_ready():
        try:
            result = _apply_with_ai(project, instruction, before)
            return _normalize_result(project, instruction, before, result, source="ai")
        except Exception as exc:
            fallback = _apply_with_rules(project, instruction, before)
            fallback["notes"].insert(0, f"真实 AI 修改失败，已使用本地审美规则兜底：{exc}")
            return fallback

    return _apply_with_rules(project, instruction, before)


def _apply_with_ai(project: Project, instruction: str, before: dict) -> dict:
    prompt = f"""
你是一个克制、有审美的中文视频粗剪助理。请按用户要求修改已有工程数据，但不要炫技。

审美原则：
- 少即是多。不要为了“更丰富”就堆满转场、闪白、抖动和花字。
- 5-10 分钟中长视频优先保证可看、清楚、稳定。
- 花字只用于关键词、转折、结论金句；平均 20-35 秒最多 1 个。
- 字幕校正要保持 SRT 条数、开始时间、时长不变。
- 如果用户只是要修字幕，不要擅自重排素材或加特效。
- 如果用户要增强画面，优先慢推、轻微横移、干净叠化、章节标题卡。
- 不要修改 asset_path，不要删除 tracks，不要大幅重写 timeline。

项目：
- 标题：{project.title}
- 平台：{project.platform}
- 风格：{project.style}
- 节奏：{project.pacing}

用户要求：
{instruction}

只输出严格 JSON：
{{
  "storyboard": 完整 storyboard JSON,
  "timeline": 完整 timeline JSON,
  "subtitle_text": "完整 SRT 文本；如果没改字幕就原样返回",
  "summary": ["简短说明改了什么"]
}}

当前 storyboard 摘要：
{json.dumps(_compact_storyboard(before["storyboard"]), ensure_ascii=False)}

当前 timeline 摘要：
{json.dumps(_compact_timeline(before["timeline"]), ensure_ascii=False)}

当前 SRT：
{_compact_subtitles(before["subtitle_content"])}
"""
    return _chat_json([{"role": "user", "content": prompt}], model_key="ai_text_model")


def _apply_with_rules(project: Project, instruction: str, before: dict) -> dict:
    storyboard = deepcopy(before["storyboard"])
    timeline = deepcopy(before["timeline"])
    subtitle_text = before["subtitle_content"]
    summary: list[str] = []

    aspect = _aspect_from_instruction(instruction)
    if aspect:
        timeline["canvas"] = _canvas_payload(aspect)
        summary.append(f"画面比例已调整为 {timeline['canvas']['label']}。")

    if _wants_subtitle_cleanup(instruction):
        subtitle_text = _cleanup_srt_text(subtitle_text)
        _cleanup_timeline_subtitles(timeline)
        summary.append("已清理字幕中的多余空格、口癖词和重复标点，并保留原时间轴。")

    if _wants_more_effects(instruction):
        _apply_tasteful_motion(project, timeline)
        summary.append("已按克制风格增强画面运动和转场，避免过度闪白/抖动。")

    if _wants_more_text(instruction):
        added = _add_limited_text_overlays(storyboard, timeline)
        summary.append(f"已补充 {added} 个关键词花字，控制频率避免满屏乱飞。")

    if not summary:
        _apply_tasteful_motion(project, timeline)
        summary.append("未识别到具体指令，已做轻量视觉整理，不重排素材。")

    _add_note(storyboard, "由 AI 修改要求页面应用修改：" + instruction[:120])
    return {
        "storyboard": storyboard,
        "timeline": timeline,
        "subtitle_text": subtitle_text,
        "summary": summary,
        "notes": ["当前按克制审美规则执行；如果配置真实 AI，会先理解你的自然语言，再经过同样的审美护栏。"],
        "source": "rules",
    }


def _normalize_result(project: Project, instruction: str, before: dict, result: dict, source: str) -> dict:
    storyboard = result.get("storyboard") if isinstance(result.get("storyboard"), dict) else before["storyboard"]
    timeline = result.get("timeline") if isinstance(result.get("timeline"), dict) else before["timeline"]
    subtitle_text = result.get("subtitle_text") if isinstance(result.get("subtitle_text"), str) else before["subtitle_content"]
    summary = result.get("summary") if isinstance(result.get("summary"), list) else []

    timeline = _apply_guardrails(project, instruction, before["timeline"], timeline)
    _add_note(storyboard, "由 AI 修改要求页面应用修改：" + instruction[:120])
    return {
        "storyboard": storyboard,
        "timeline": timeline,
        "subtitle_text": subtitle_text,
        "summary": [str(item) for item in summary] or ["AI 已应用修改要求，并经过克制审美护栏。"],
        "notes": result.get("notes", []),
        "source": source,
    }


def _apply_guardrails(project: Project, instruction: str, original_timeline: dict, timeline: dict) -> dict:
    guarded = deepcopy(timeline)
    _keep_asset_paths(original_timeline, guarded)
    _limit_overlays(guarded)
    if _wants_more_effects(instruction):
        _apply_tasteful_motion(project, guarded)
    if not _wants_more_text(instruction):
        _avoid_new_overlay_spam(original_timeline, guarded)
    return guarded


def _keep_asset_paths(original: dict, timeline: dict) -> None:
    original_video = _track_items(original, "video")
    new_video = _track_items(timeline, "video")
    for old, new in zip(original_video, new_video):
        if old.get("asset_path"):
            new["asset_path"] = old["asset_path"]


def _avoid_new_overlay_spam(original: dict, timeline: dict) -> None:
    old_count = len(_track_items(original, "text"))
    text_track = _track(timeline, "text")
    text_track["items"] = text_track.get("items", [])[: max(old_count, 1)]


def _limit_overlays(timeline: dict) -> None:
    text_track = _track(timeline, "text")
    items = sorted(text_track.get("items", []), key=lambda item: float(item.get("start", 0)))
    kept = []
    last_start = -999.0
    for item in items:
        start = float(item.get("start", 0))
        if start - last_start < 12 and len(kept) >= 1:
            continue
        item["duration"] = min(float(item.get("duration", 2.5)), 3.0)
        kept.append(item)
        last_start = start
    text_track["items"] = kept[:24]


def _apply_tasteful_motion(project: Project, timeline: dict) -> None:
    style = project.style or ""
    if style == "情绪共鸣型":
        plans = [
            ("slow_zoom_in", "叠化", "渐隐", "ken_burns_in"),
            ("gentle_pan", "叠化", "渐隐", "pan_right"),
            ("soft_fade", "叠化", "渐隐", "ken_burns_out"),
        ]
    elif style == "社科解释型":
        plans = [
            ("hold_clean", "叠化", "渐隐", "hold"),
            ("slow_zoom_in", "向左", "向左滑动", "ken_burns_in"),
            ("clean_slide", "叠化", "渐隐", "slide_left"),
        ]
    else:
        plans = [
            ("clean_cut", "叠化", "放大", "hold"),
            ("slow_zoom_in", "叠化", "放大", "ken_burns_in"),
            ("gentle_pan", "向左", "向左滑动", "slide_left"),
            ("keyword_punch", "叠化", "放大", "punch_in"),
        ]

    for index, item in enumerate(_track_items(timeline, "video")):
        effect, transition, animation, motion = plans[index % len(plans)]
        item.update({"effect": effect, "transition": transition, "animation": animation, "motion": motion})

    for item in _track_items(timeline, "text"):
        item["style"] = _text_style_for_project(project)
        item["animation"] = "渐隐" if style in {"情绪共鸣型", "社科解释型"} else "弹入"


def _add_limited_text_overlays(storyboard: dict, timeline: dict) -> int:
    text_track = _track(timeline, "text")
    existing_starts = [float(item.get("start", 0)) for item in text_track.get("items", [])]
    added = 0
    for section in storyboard.get("sections", [])[:12]:
        if added >= 6:
            break
        if added % 2 == 1:
            continue
        keywords = [str(item) for item in section.get("subtitle_keywords") or [] if str(item).strip()]
        if not keywords:
            continue
        start = _section_start(timeline, section.get("id")) + 3.0
        if any(abs(start - old) < 10 for old in existing_starts):
            continue
        text_track.setdefault("items", []).append(
            {
                "start": round(start, 3),
                "duration": 2.4,
                "text": " / ".join(keywords[:2]),
                "style": "keyword_clean",
                "animation": "弹入",
                "section_id": section.get("id"),
                "track_label": "AI 关键词花字",
            }
        )
        existing_starts.append(start)
        added += 1
    return added


def _cleanup_srt_text(subtitle_text: str) -> str:
    cues = parse_srt(subtitle_text or "")
    if not cues:
        return subtitle_text
    lines = []
    for cue in cues:
        lines.extend([str(cue.index), f"{_srt_time(cue.start)} --> {_srt_time(cue.end)}", _cleanup_text(cue.text), ""])
    return "\n".join(lines)


def _cleanup_timeline_subtitles(timeline: dict) -> None:
    for item in _track_items(timeline, "subtitle"):
        item["text"] = _cleanup_text(str(item.get("text") or ""))
        item["style"] = "clean_subtitle"


def _cleanup_text(text: str) -> str:
    value = re.sub(r"\s+", "", text.strip())
    for source, target in {"嗯": "", "呃": "", "然后然后": "然后", "就是就是": "就是"}.items():
        value = value.replace(source, target)
    value = re.sub(r"([，。！？、,.!?])\1+", r"\1", value)
    return value


def _aspect_from_instruction(instruction: str) -> str | None:
    text = instruction.lower()
    if any(word in text for word in ["竖屏", "9:16", "916", "抖音", "小红书"]):
        return "vertical_9_16"
    if any(word in text for word in ["方形", "1:1"]):
        return "square_1_1"
    if any(word in text for word in ["横屏", "16:9", "169", "b站", "bilibili"]):
        return "horizontal_16_9"
    return None


def _canvas_payload(aspect: str) -> dict:
    if aspect == "vertical_9_16":
        return {"aspect": aspect, "width": 1080, "height": 1920, "label": "竖屏 9:16"}
    if aspect == "square_1_1":
        return {"aspect": aspect, "width": 1080, "height": 1080, "label": "方形 1:1"}
    return {"aspect": "horizontal_16_9", "width": 1920, "height": 1080, "label": "横屏 16:9"}


def _wants_more_effects(instruction: str) -> bool:
    return any(word in instruction for word in ["特效", "动效", "转场", "丰富", "高级", "不单调", "节奏", "快切", "慢推"])


def _wants_subtitle_cleanup(instruction: str) -> bool:
    return any(word in instruction.lower() for word in ["字幕", "srt", "错字", "错别字", "标点", "断句", "语音识别"])


def _wants_more_text(instruction: str) -> bool:
    return any(word in instruction for word in ["花字", "大字", "关键词", "标题", "强调", "屏幕文字"])


def _text_style_for_project(project: Project) -> str:
    if project.style == "情绪共鸣型":
        return "literary_caption"
    if project.style == "社科解释型":
        return "black_card_clean"
    if project.style == "小红书口播型":
        return "big_title_vertical"
    return "bilibili_clean_pop"


def _compact_storyboard(storyboard: dict) -> dict:
    return {
        "project_title": storyboard.get("project_title"),
        "style": storyboard.get("style"),
        "sections": [
            {
                "id": section.get("id"),
                "title": section.get("title"),
                "purpose": section.get("purpose"),
                "visual_plan": section.get("visual_plan"),
                "subtitle_keywords": section.get("subtitle_keywords"),
                "text_overlays": section.get("text_overlays"),
                "shots": section.get("shots", [])[:6],
            }
            for section in storyboard.get("sections", [])[:16]
        ],
    }


def _compact_timeline(timeline: dict) -> dict:
    tracks = []
    for track in timeline.get("tracks", []):
        items = []
        for item in track.get("items", [])[:80]:
            items.append(
                {
                    key: item.get(key)
                    for key in [
                        "section_id", "shot_id", "asset_id", "asset_name", "start", "duration",
                        "effect", "transition", "animation", "motion", "text", "style", "track_label",
                    ]
                    if item.get(key) not in (None, "")
                }
            )
        tracks.append({"type": track.get("type"), "items": items})
    return {
        "duration": timeline.get("duration"),
        "canvas": timeline.get("canvas"),
        "subtitle_source": timeline.get("subtitle_source"),
        "tracks": tracks,
    }


def _compact_subtitles(subtitle_content: str) -> str:
    return subtitle_content[:12000] if subtitle_content else ""


def _track(timeline: dict, track_type: str) -> dict:
    for track in timeline.setdefault("tracks", []):
        if track.get("type") == track_type:
            return track
    track = {"type": track_type, "items": []}
    timeline["tracks"].append(track)
    return track


def _track_items(timeline: dict, track_type: str) -> list[dict]:
    return _track(timeline, track_type).get("items", [])


def _section_start(timeline: dict, section_id: str | None) -> float:
    for track in timeline.get("tracks", []):
        for item in track.get("items", []):
            if item.get("section_id") == section_id:
                return float(item.get("start", 0))
    return 0.0


def _add_note(storyboard: dict, note: str) -> None:
    notes = storyboard.setdefault("notes", [])
    if note not in notes:
        notes.insert(0, note)


def _srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours, remainder = divmod(ms, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def serialize_adjusted_timeline(timeline: dict) -> str:
    return dumps_json(timeline)
