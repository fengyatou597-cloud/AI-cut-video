import base64
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.db.models import Project
from app.services.script_service import estimate_duration_seconds, split_script_into_blocks
from app.services.settings_service import load_user_config
from app.services.style_templates import STYLE_TEMPLATES


def build_storyboard(project: Project, script_text: str) -> dict:
    if _ai_ready():
        try:
            return build_ai_storyboard(project, script_text)
        except Exception as exc:
            fallback = build_mock_storyboard(project, script_text)
            fallback["notes"].insert(0, f"真实 AI 生成失败，已回退 mock：{exc}")
            return fallback
    return build_mock_storyboard(project, script_text)


def build_ai_storyboard(project: Project, script_text: str) -> dict:
    template = STYLE_TEMPLATES.get(project.style, STYLE_TEMPLATES["B站知识型"])
    prompt = f"""
你是一个中文中长视频粗剪导演和分镜策划。请理解用户文稿，为 5-10 分钟视频生成可执行 storyboard JSON。

项目设置：
- 标题：{project.title}
- 平台：{project.platform}
- 目标时长：{project.target_duration}
- 风格：{project.style}
- 剪辑节奏：{project.pacing}
- 是否强钩子：{project.needs_hook}
- 是否需要 B-roll：{project.needs_broll}
- 是否需要论文/新闻/数据图：{project.needs_research_visuals}
- 风格模板：{json.dumps(template, ensure_ascii=False)}

要求：
- 每 20-40 秒一个 section。
- 每个 section 内部拆成 4-8 秒一个 shot。
- 不要只复述文稿，要指出画面策略、素材需求、缺失素材、字幕关键词、花字和转场。
- 开头 15 秒要强一点，结尾要总结或回扣。
- 只输出 JSON，不要 Markdown。

JSON 结构：
{{
  "project_title": "",
  "target_duration": "",
  "style": "",
  "platform": "",
  "notes": [],
  "sections": [
    {{
      "id": "s001",
      "title": "",
      "narration": "",
      "estimated_duration": 20,
      "purpose": "",
      "core_message": "",
      "emotion": "",
      "visual_plan": "",
      "required_assets": [],
      "missing_assets": [],
      "subtitle_keywords": [],
      "text_overlays": [],
      "effects": [],
      "transition": "",
      "pacing": "fast|medium|steady",
      "shots": [
        {{"id":"s001_shot_01", "start":0, "duration":5, "visual_change":"", "suggested_asset_type":"video|image", "effect":""}}
      ]
    }}
  ]
}}

文稿：
{script_text[:24000]}
"""
    data = _chat_json([{"role": "user", "content": prompt}], model_key="ai_text_model")
    data.setdefault("project_title", project.title)
    data.setdefault("target_duration", project.target_duration)
    data.setdefault("style", project.style)
    data.setdefault("platform", project.platform)
    data.setdefault("notes", [])
    data["notes"].insert(0, "由真实 AI API 生成。请人工检查后再生成 timeline。")
    return data


def analyze_asset_with_ai(asset) -> dict | None:
    if not _ai_base_ready():
        return None
    image_paths = _asset_image_paths(asset)
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "你是视频剪辑素材编目助手。请根据文件名、类型、元信息和关键帧/缩略图，输出严格 JSON："
                "{\"summary\":\"画面一句话描述\",\"tags\":[\"标签\"],\"best_use\":[\"适合放在哪类段落\"],"
                "\"mood\":\"情绪\",\"pace\":\"slow|medium|fast\",\"visual_quality\":\"low|medium|high\","
                "\"suggested_effects\":[\"建议动效\"]}。"
                "tags 尽量包含具体可匹配词，例如：人物、街景、家庭、焦虑、怀旧、数据图、新闻截图、"
                "书本、办公室、夜晚、远景、特写、空镜、情绪低落、解释说明。"
                f"文件名：{asset.filename}；类型：{asset.asset_type}；时长：{asset.duration}；分辨率：{asset.width}x{asset.height}。"
            ),
        }
    ]
    for path in image_paths[:3]:
        data_url = _image_data_url(path)
        if data_url:
            content.append({"type": "image_url", "image_url": {"url": data_url}})
    try:
        if len(content) > 1:
            return _chat_json([{"role": "user", "content": content}], model_key="ai_vision_model")
        return _chat_json([{"role": "user", "content": content[0]["text"]}], model_key="ai_text_model")
    except Exception:
        return None


def ai_status() -> dict:
    config = load_user_config()
    text_endpoint = _endpoint_config(config, "text")
    vision_endpoint = _endpoint_config(config, "vision")
    text_model = _model_name(config, "ai_text_model")
    vision_model = _model_name(config, "ai_vision_model")
    blockers = []
    if not config.get("ai_enabled"):
        blockers.append("未勾选启用真实 AI")
    if not text_endpoint["base_url"]:
        blockers.append("缺少文本/通用 API Base URL")
    if not text_endpoint["api_key"]:
        blockers.append("缺少文本/通用 API Key")
    if not text_model:
        blockers.append("缺少文本模型名")
    return {
        "enabled": bool(config.get("ai_enabled")),
        "text_ready": bool(config.get("ai_enabled") and text_endpoint["base_url"] and text_endpoint["api_key"] and text_model),
        "vision_ready": bool(config.get("ai_enabled") and vision_endpoint["base_url"] and vision_endpoint["api_key"] and vision_model),
        "text_model": text_model,
        "vision_model": vision_model,
        "blockers": blockers,
    }


def build_mock_storyboard(project: Project, script_text: str) -> dict:
    blocks = split_script_into_blocks(script_text)
    template = STYLE_TEMPLATES.get(project.style, STYLE_TEMPLATES["B站知识型"])
    sections = []

    if project.needs_hook:
        hook_text = blocks[0] if blocks else f"今天我们聊聊：{project.title}。"
        sections.append(
            {
                "id": "s001",
                "title": "开头钩子",
                "narration": _trim(hook_text, 140),
                "estimated_duration": min(20, estimate_duration_seconds(hook_text)),
                "purpose": "制造问题感，给观众一个继续看下去的理由",
                "core_message": _core_message(hook_text),
                "emotion": "强钩子 / 好奇 / 问题感",
                "visual_plan": _visual_plan(project.style, "hook"),
                "required_assets": _required_assets(project, "hook"),
                "missing_assets": _missing_assets(project, "hook"),
                "subtitle_keywords": _keywords(hook_text, project.title),
                "text_overlays": ["先抛出反常识问题", "用 1 句大字标题压住注意力"],
                "effects": template["default_effects"][:2],
                "transition": "黑底白字快速切入" if project.style == "社科解释型" else "快速淡入 + 轻微推近",
                "pacing": "fast",
                "shots": _shots_for_section("s001", min(20, estimate_duration_seconds(hook_text)), project.style),
            }
        )
        content_blocks = blocks[1:] or blocks
    else:
        content_blocks = blocks

    next_id = len(sections) + 1
    for index, block in enumerate(content_blocks):
        section_id = f"s{next_id:03d}"
        duration = estimate_duration_seconds(block)
        purpose = _purpose_for_index(index, len(content_blocks))
        sections.append(
            {
                "id": section_id,
                "title": _section_title(block, index),
                "narration": block,
                "estimated_duration": duration,
                "purpose": purpose,
                "core_message": _core_message(block),
                "emotion": _emotion_for_project(project.style, index),
                "visual_plan": _visual_plan(project.style, "body"),
                "required_assets": _required_assets(project, "body"),
                "missing_assets": _missing_assets(project, "body"),
                "subtitle_keywords": _keywords(block, project.title),
                "text_overlays": _text_overlays(project.style),
                "effects": template["default_effects"],
                "transition": "章节黑卡" if index % 3 == 0 else "自然切 / 叠化",
                "pacing": _pacing(project.pacing),
                "shots": _shots_for_section(section_id, duration, project.style),
            }
        )
        next_id += 1

    if sections:
        sections[-1]["purpose"] = "总结观点，并回扣开头问题"
        sections[-1]["transition"] = "收束淡出"
        sections[-1]["text_overlays"] = list(dict.fromkeys(sections[-1]["text_overlays"] + ["结论金句", "回扣开头" ]))

    return {
        "project_title": project.title,
        "target_duration": project.target_duration,
        "style": project.style,
        "platform": project.platform,
        "template": template,
        "notes": [
            "MVP 使用 mock AI 生成，可在 backend/app/services/ai_service.py 替换为真实模型。",
            "每个 section 内部已经拆出 shots，方便后续生成 timeline。",
            "建议人工确认 storyboard 后再生成 timeline 和剪映草稿。",
        ],
        "sections": sections,
    }


def dumps_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def loads_json(data: str | None) -> dict | None:
    if not data:
        return None
    return json.loads(data)


def _ai_ready() -> bool:
    config = load_user_config()
    return bool(config.get("ai_enabled") and _endpoint_config(config, "text")["base_url"] and _endpoint_config(config, "text")["api_key"] and _model_name(config, "ai_text_model"))


def _ai_base_ready() -> bool:
    config = load_user_config()
    return bool(config.get("ai_enabled") and _endpoint_config(config, "text")["base_url"] and _endpoint_config(config, "text")["api_key"])


def _chat_json(messages: list[dict], model_key: str) -> dict:
    config = load_user_config()
    model = _model_name(config, model_key)
    if not model:
        raise RuntimeError("未配置 AI 模型名")
    endpoint = _endpoint_config(config, "vision" if model_key == "ai_vision_model" else "text")
    if not endpoint["base_url"] or not endpoint["api_key"]:
        raise RuntimeError("未配置对应 AI API Base URL 或 API Key")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        _chat_url(endpoint["base_url"]),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {endpoint['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[-1000:]
        raise RuntimeError(f"AI API HTTP {exc.code}: {detail}") from exc
    content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return _parse_json_content(content)


def _model_name(config: dict, model_key: str) -> str:
    if model_key == "ai_vision_model":
        configured = (config.get("ai_vision_model") or "").strip()
    else:
        configured = (config.get("ai_text_model") or "").strip()
    if configured:
        return configured
    base_url = (config.get("ai_vision_base_url") or config.get("ai_text_base_url") or config.get("ai_base_url") or "").lower()
    if "dashscope.aliyuncs.com" in base_url:
        return "qwen-vl-plus" if model_key == "ai_vision_model" else "qwen-plus"
    return ""


def _endpoint_config(config: dict, kind: str) -> dict:
    if kind == "vision":
        return {
            "base_url": (config.get("ai_vision_base_url") or config.get("ai_base_url") or "").strip(),
            "api_key": (config.get("ai_vision_api_key") or config.get("ai_api_key") or "").strip(),
        }
    return {
        "base_url": (config.get("ai_text_base_url") or config.get("ai_base_url") or "").strip(),
        "api_key": (config.get("ai_text_api_key") or config.get("ai_api_key") or "").strip(),
    }


def _chat_url(base_url: str) -> str:
    value = base_url.strip().rstrip("/")
    if value.endswith("/chat/completions"):
        return value
    if value.endswith("/v1"):
        return f"{value}/chat/completions"
    return f"{value}/v1/chat/completions"


def _parse_json_content(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            return json.loads(match.group(0))
        raise


def _asset_image_paths(asset) -> list[Path]:
    paths: list[Path] = []
    for raw in json.loads(asset.keyframe_paths or "[]"):
        path = Path(raw)
        if path.exists():
            paths.append(path)
    if asset.thumbnail_path and Path(asset.thumbnail_path).exists():
        paths.insert(0, Path(asset.thumbnail_path))
    if asset.asset_type == "image" and Path(asset.path).exists():
        paths.insert(0, Path(asset.path))
    return list(dict.fromkeys(paths))


def _image_data_url(path: Path) -> str | None:
    suffix = path.suffix.lower()
    mime = "image/jpeg"
    if suffix == ".png":
        mime = "image/png"
    elif suffix == ".webp":
        mime = "image/webp"
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return None
    return f"data:{mime};base64,{encoded}"


def _trim(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def _section_title(text: str, index: int) -> str:
    short = text.replace("，", " ").replace("。", " ").strip().split(" ")[0]
    return f"第 {index + 1} 段：{_trim(short, 18)}" if short else f"第 {index + 1} 段"


def _core_message(text: str) -> str:
    return _trim(text.replace("\n", " "), 80)


def _keywords(text: str, project_title: str) -> list[str]:
    candidates = [word.strip(" ，。！？、,.!?;；：:") for word in [project_title, *text[:80].split()]]
    keywords = [word for word in candidates if 2 <= len(word) <= 12]
    return list(dict.fromkeys(keywords))[:5] or [project_title]


def _visual_plan(style: str, stage: str) -> str:
    if style == "社科解释型":
        return "用论点黑卡开段，穿插论文/新闻/数据截图，关键句做高亮标注。"
    if style == "情绪共鸣型":
        return "用生活化 B-roll 和慢推镜头承接情绪，避免单一画面停留过久。"
    if style == "小红书口播型":
        return "竖屏大字幕为主，每屏只放一个信息点，配合封面感标题。"
    return "快切素材、截图标注、吐槽花字和关键词放大，保持信息密度。"


def _required_assets(project: Project, stage: str) -> list[str]:
    assets = ["主视觉素材", "字幕/花字"]
    if project.needs_broll:
        assets.append("生活化 B-roll 或影视感画面")
    if project.needs_research_visuals:
        assets.extend(["论文截图", "新闻截图", "数据图表"])
    if stage == "hook":
        assets.append("强情绪开场画面")
    return assets


def _missing_assets(project: Project, stage: str) -> list[str]:
    missing = []
    if project.needs_broll:
        missing.append("可补充 3-5 个与主题相关的 B-roll 片段")
    if project.needs_research_visuals:
        missing.append("可补充权威来源截图和一张可视化数据图")
    if stage == "hook":
        missing.append("建议准备一个 3 秒内能建立问题感的开场镜头")
    return missing


def _text_overlays(style: str) -> list[str]:
    if style == "社科解释型":
        return ["关键词高亮", "黑底白字论点卡"]
    if style == "情绪共鸣型":
        return ["低饱和金句字幕", "情绪关键词慢显"]
    if style == "小红书口播型":
        return ["大字幕信息点", "封面感标题"]
    return ["吐槽式花字", "知识点编号", "关键词放大"]


def _emotion_for_project(style: str, index: int) -> str:
    if style == "情绪共鸣型":
        return "共鸣 / 递进 / 留白" if index % 2 else "代入 / 低声部情绪"
    if style == "社科解释型":
        return "理性 / 清晰 / 稳定"
    return "信息密集 / 轻快 / 有梗"


def _purpose_for_index(index: int, total: int) -> str:
    if index == 0:
        return "承接开头，建立背景"
    if index >= total - 2:
        return "推进到结论，准备收束"
    if index % 3 == 0:
        return "制造转折或提出新问题"
    return "展开论点并给出例证"


def _pacing(project_pacing: str) -> str:
    return {"稳重": "steady", "中等": "medium", "快节奏": "fast"}.get(project_pacing, "medium")


def _shots_for_section(section_id: str, duration: int, style: str) -> list[dict]:
    shot_length = 5 if style in {"B站知识型", "小红书口播型"} else 7
    shots = []
    start = 0
    index = 1
    while start < duration:
        shot_duration = min(shot_length, duration - start)
        shots.append(
            {
                "id": f"{section_id}_shot_{index:02d}",
                "start": start,
                "duration": shot_duration,
                "visual_change": "切换素材或增加文字/标注",
                "suggested_asset_type": "video" if index % 2 else "image",
                "effect": "slow_zoom_in" if style in {"情绪共鸣型", "社科解释型"} else "quick_cut",
            }
        )
        start += shot_duration
        index += 1
    return shots
