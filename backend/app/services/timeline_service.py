import json
import re
from app.db.models import Asset
from app.services.subtitle_service import SubtitleCue, parse_srt


def build_mock_timeline(storyboard: dict, assets: list[Asset], subtitle_content: str | None = None) -> dict:
    video_assets = [asset for asset in assets if asset.asset_type in {"video", "image"}]
    audio_assets = [asset for asset in assets if asset.asset_type == "audio"]
    subtitle_cues = parse_srt(subtitle_content or "") if subtitle_content else []

    tracks = [
        {"type": "video", "items": []},
        {"type": "text", "items": []},
        {"type": "subtitle", "items": []},
        {"type": "audio", "items": []},
    ]

    cursor = 0.0
    asset_index = 0
    used_asset_ids: list[int] = []
    target_duration = _subtitle_total_duration(subtitle_cues)

    for section in storyboard.get("sections", []):
        if target_duration and cursor >= target_duration:
            break
        section_start = cursor
        shots = section.get("shots") or [{"start": 0, "duration": section.get("estimated_duration", 8), "effect": "slow_zoom_in"}]
        for shot in shots:
            if target_duration and cursor >= target_duration:
                break
            duration = float(shot.get("duration", 5))
            if target_duration:
                duration = min(duration, max(0.8, target_duration - cursor))
            selected = _select_visual_asset(video_assets, asset_index, section, shot, used_asset_ids)
            if selected:
                asset_index += 1
                used_asset_ids.append(selected.id)
            effect_plan = _visual_effect_plan(storyboard.get("style", ""), asset_index)
            ai_tags = _asset_ai_tags(selected)
            ai_effect = _first_text(ai_tags.get("suggested_effects"))
            tracks[0]["items"].append(
                {
                    "section_id": section.get("id"),
                    "shot_id": shot.get("id"),
                    "asset_id": f"asset_{selected.id:03d}" if selected else None,
                    "asset_name": selected.filename if selected else "未匹配素材",
                    "asset_path": selected.path if selected else None,
                    "asset_type": selected.asset_type if selected else "placeholder",
                    "start": round(cursor, 3),
                    "duration": round(duration, 3),
                    "source_start": _source_start(selected, cursor, duration) if selected else 0,
                    "source_duration": round(duration, 3),
                    "effect": ai_effect or effect_plan["effect"],
                    "transition": effect_plan["transition"],
                    "animation": effect_plan["animation"],
                    "motion": effect_plan["motion"],
                    "note": shot.get("visual_change", section.get("visual_plan", "")),
                    "match_reason": _match_reason(selected, section, shot),
                    "track_label": f"{section.get('id')} / {shot.get('id', 'shot')}",
                }
            )
            cursor += duration

        title = section.get("title", "")
        if title:
            tracks[1]["items"].append(
                {
                    "start": round(section_start + 0.4, 3),
                    "duration": min(3.5, max(2.0, section.get("estimated_duration", 8) / 4)),
                    "text": title,
                    "style": _text_style(storyboard.get("style", "")),
                    "animation": _text_animation(storyboard.get("style", ""), len(tracks[1]["items"])),
                    "section_id": section.get("id"),
                    "track_label": f"{section.get('id')} 标题花字",
                }
            )

        if not subtitle_cues:
            narration = section.get("narration", "")
            subtitle_chunks = _subtitle_chunks(narration)
            subtitle_cursor = section_start
            subtitle_duration = max(2.0, section.get("estimated_duration", 8) / max(1, len(subtitle_chunks)))
            for chunk in subtitle_chunks:
                tracks[2]["items"].append(
                    {
                        "start": round(subtitle_cursor, 3),
                        "duration": round(subtitle_duration, 3),
                        "text": chunk,
                        "source": "script",
                        "section_id": section.get("id"),
                        "track_label": f"{section.get('id')} 字幕",
                    }
                )
                subtitle_cursor += subtitle_duration

    if subtitle_cues:
        tracks[2]["items"] = [_subtitle_item(cue) for cue in subtitle_cues]
        cursor = max(cursor, target_duration or 0)

    _extend_video_track(tracks[0]["items"], cursor, target_duration, video_assets, storyboard.get("style", ""), asset_index, used_asset_ids)
    final_duration = round(target_duration or max(cursor, _max_track_end(tracks)), 3)

    if audio_assets:
        voiceover = audio_assets[0]
        tracks[3]["items"].append(
            {
                "asset_id": f"asset_{voiceover.id:03d}",
                "asset_name": voiceover.filename,
                "asset_path": voiceover.path,
                "role": "voiceover",
                "start": 0,
                "duration": final_duration,
                "source_start": 0,
                "volume": 1.0,
                "note": "默认将第一个音频素材作为旁白/主录音轨",
                "track_label": "旁白录音",
            }
        )
        for bgm in audio_assets[1:2]:
            tracks[3]["items"].append(
                {
                    "asset_id": f"asset_{bgm.id:03d}",
                    "asset_name": bgm.filename,
                    "asset_path": bgm.path,
                    "role": "bgm",
                    "start": 0,
                    "duration": final_duration,
                    "source_start": 0,
                    "volume": 0.18,
                    "note": "第二个音频素材作为低音量背景音乐占位",
                    "track_label": "背景音乐",
                }
            )

    return {
        "project_title": storyboard.get("project_title", ""),
        "duration": final_duration,
        "asset_signature": _asset_signature(assets),
        "subtitle_source": "uploaded_srt" if subtitle_cues else "script_narration",
        "edit_style": _edit_style_summary(storyboard.get("style", "")),
        "tracks": tracks,
        "warnings": _warnings(video_assets, audio_assets, subtitle_cues),
    }


def dumps_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def loads_json(data: str | None) -> dict | None:
    return json.loads(data) if data else None


def _subtitle_chunks(text: str, limit: int = 28) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    current = ""
    for char in text:
        current += char
        if len(current) >= limit and char in "，。！？!?；; ":
            chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks[:12]


def _text_style(style: str) -> str:
    if style == "小红书口播型":
        return "big_title_vertical"
    if style == "社科解释型":
        return "black_card_clean"
    if style == "情绪共鸣型":
        return "literary_caption"
    return "bilibili_pop_title"


def _warnings(video_assets: list[Asset], audio_assets: list[Asset], subtitle_cues: list[SubtitleCue]) -> list[str]:
    warnings = []
    if not video_assets:
        warnings.append("当前没有视频/图片素材，timeline 使用 placeholder。")
    if not audio_assets:
        warnings.append("当前没有音频素材。上传旁白录音后，导出剪映草稿会自动加入主音频轨。")
    if not subtitle_cues:
        warnings.append("当前没有上传 SRT，字幕由文稿粗略切分；上传 SRT 后会优先使用精确字幕时间轴。")
    return warnings


def _subtitle_total_duration(cues: list[SubtitleCue]) -> float | None:
    if not cues:
        return None
    return round(max(cue.end for cue in cues), 3)


def _subtitle_item(cue: SubtitleCue) -> dict:
    return {
        "start": round(cue.start, 3),
        "duration": round(cue.duration, 3),
        "text": cue.text,
        "source": "uploaded_srt",
        "track_label": f"SRT 字幕 {cue.index}",
    }


def _extend_video_track(items: list[dict], cursor: float, target_duration: float | None, video_assets: list[Asset], style: str, asset_index: int, used_asset_ids: list[int]) -> None:
    if not target_duration:
        return
    while cursor < target_duration:
        duration = min(_default_shot_length(style), target_duration - cursor)
        selected = _select_visual_asset(video_assets, asset_index, {"title": "SRT 补齐", "visual_plan": "按字幕时间轴补齐画面"}, {"visual_change": "B-roll 补充镜头"}, used_asset_ids)
        asset_index += 1
        if selected:
            used_asset_ids.append(selected.id)
        effect_plan = _visual_effect_plan(style, asset_index)
        ai_tags = _asset_ai_tags(selected)
        ai_effect = _first_text(ai_tags.get("suggested_effects"))
        items.append(
            {
                "section_id": "srt_fill",
                "shot_id": f"srt_fill_{len(items) + 1:02d}",
                "asset_id": f"asset_{selected.id:03d}" if selected else None,
                "asset_name": selected.filename if selected else "未匹配素材",
                "asset_path": selected.path if selected else None,
                "asset_type": selected.asset_type if selected else "placeholder",
                "start": round(cursor, 3),
                "duration": round(duration, 3),
                "source_start": _source_start(selected, cursor, duration) if selected else 0,
                "source_duration": round(duration, 3),
                "effect": ai_effect or effect_plan["effect"],
                "transition": effect_plan["transition"],
                "animation": effect_plan["animation"],
                "motion": effect_plan["motion"],
                "note": "按 SRT 时长自动补齐的 B-roll 镜头",
                "match_reason": _match_reason(selected, {"title": "SRT 补齐"}, {"visual_change": "B-roll 补充镜头"}),
                "track_label": "SRT 补齐镜头",
            }
        )
        cursor += duration


def _visual_effect_plan(style: str, index: int) -> dict:
    if style == "社科解释型":
        plans = [
            {"effect": "slow_zoom_in", "transition": "叠化", "animation": "放大", "motion": "ken_burns_in"},
            {"effect": "clean_slide", "transition": "向左", "animation": "向左滑动", "motion": "slide_left"},
            {"effect": "black_card_cut", "transition": "叠加", "animation": "渐隐", "motion": "hold"},
        ]
    elif style == "情绪共鸣型":
        plans = [
            {"effect": "slow_zoom_in", "transition": "叠化", "animation": "放大", "motion": "ken_burns_in"},
            {"effect": "soft_fade", "transition": "回忆", "animation": "渐隐", "motion": "ken_burns_out"},
            {"effect": "gentle_pan", "transition": "向右", "animation": "向右滑动", "motion": "pan_right"},
        ]
    elif style == "小红书口播型":
        plans = [
            {"effect": "pop_zoom", "transition": "卡片弹出", "animation": "弹近", "motion": "punch_in"},
            {"effect": "vertical_slide", "transition": "向上", "animation": "向上滑动", "motion": "slide_up"},
            {"effect": "quick_cut", "transition": "叠化", "animation": "放大", "motion": "hold"},
        ]
    else:
        plans = [
            {"effect": "quick_cut", "transition": "信号故障", "animation": "抖动变焦", "motion": "punch_in"},
            {"effect": "snap_zoom", "transition": "叠化", "animation": "放大", "motion": "ken_burns_in"},
            {"effect": "meme_slide", "transition": "向左", "animation": "向左滑动", "motion": "slide_left"},
            {"effect": "glitch_flash", "transition": "闪白", "animation": "曝光放射", "motion": "shake_light"},
        ]
    return plans[index % len(plans)]


def _text_animation(style: str, index: int) -> str:
    if style == "社科解释型":
        return ["居中打字", "向上露出", "渐隐"][index % 3]
    if style == "情绪共鸣型":
        return ["慢速放大", "向上露出", "打字机_I"][index % 3]
    if style == "小红书口播型":
        return ["弹入", "放大震动", "向上弹入"][index % 3]
    return ["故障打字机", "弹入跳动", "放大震动"][index % 3]


def _default_shot_length(style: str) -> float:
    if style in {"B站知识型", "小红书口播型"}:
        return 4.0
    if style == "情绪共鸣型":
        return 7.0
    return 6.0


def _max_track_end(tracks: list[dict]) -> float:
    return max(
        [0.0]
        + [
            float(item.get("start", 0)) + float(item.get("duration", 0))
            for track in tracks
            for item in track.get("items", [])
        ]
    )


def _edit_style_summary(style: str) -> dict:
    if style == "社科解释型":
        return {"cut_rule": "5-7 秒换画面，章节处用黑卡/叠化", "subtitle_rule": "干净字幕 + 关键词标题"}
    if style == "情绪共鸣型":
        return {"cut_rule": "6-8 秒换画面，慢推和叠化更多", "subtitle_rule": "字幕保留呼吸感，花字少"}
    if style == "小红书口播型":
        return {"cut_rule": "3-5 秒换画面，竖屏大字和弹入更多", "subtitle_rule": "每屏信息点明确"}
    return {"cut_rule": "4-6 秒换画面，快切/闪切/吐槽花字更多", "subtitle_rule": "关键词放大和节奏提示"}


def _select_visual_asset(video_assets: list[Asset], index: int, section: dict | None = None, shot: dict | None = None, used_asset_ids: list[int] | None = None) -> Asset | None:
    if not video_assets:
        return None
    section = section or {}
    shot = shot or {}
    used_asset_ids = used_asset_ids or []
    scored = [(_asset_match_score(asset, section, shot, used_asset_ids), asset) for asset in video_assets]
    best_score = max(score for score, _asset in scored)
    if best_score > 0:
        best_assets = [asset for score, asset in scored if score == best_score]
        return best_assets[index % len(best_assets)]
    if len(video_assets) <= 2:
        return video_assets[index % len(video_assets)]
    # 用一个步长打散顺序，避免素材总是 1,2,3,1,2,3 机械循环。
    return video_assets[(index * 2 + index // 3) % len(video_assets)]


def _asset_match_score(asset: Asset, section: dict, shot: dict, used_asset_ids: list[int]) -> float:
    ai_tags = _asset_ai_tags(asset)
    haystack = " ".join(
        [
            asset.filename,
            " ".join(_as_text_list(ai_tags.get("tags"))),
            " ".join(_as_text_list(ai_tags.get("best_use"))),
            str(ai_tags.get("summary") or ""),
            str(ai_tags.get("mood") or ""),
            str(ai_tags.get("pace") or ""),
            str(ai_tags.get("visual_quality") or ""),
        ]
    ).lower()
    need_text = " ".join(
        [
            str(section.get("title") or ""),
            str(section.get("purpose") or ""),
            str(section.get("core_message") or ""),
            str(section.get("emotion") or ""),
            str(section.get("visual_plan") or ""),
            " ".join(_as_text_list(section.get("required_assets"))),
            " ".join(_as_text_list(section.get("subtitle_keywords"))),
            str(shot.get("visual_change") or ""),
            str(shot.get("suggested_asset_type") or ""),
        ]
    ).lower()
    score = 0.0
    for token in _keyword_tokens(need_text):
        if token in haystack:
            score += 3.0 if len(token) >= 3 else 1.0
    if shot.get("suggested_asset_type") and asset.asset_type == shot.get("suggested_asset_type"):
        score += 1.5
    if asset.id in used_asset_ids[-2:]:
        score -= 2.0
    recent_repeat_count = used_asset_ids[-6:].count(asset.id)
    score -= recent_repeat_count * 0.8
    if ai_tags.get("summary") or ai_tags.get("tags"):
        score += 0.5
    return score


def _match_reason(asset: Asset | None, section: dict, shot: dict) -> str:
    if not asset:
        return "没有可用素材，使用 placeholder。"
    ai_tags = _asset_ai_tags(asset)
    tags = _as_text_list(ai_tags.get("tags"))[:4]
    summary = ai_tags.get("summary")
    if summary or tags:
        tag_text = "、".join(tags)
        return f"根据 AI 素材标签匹配：{summary or tag_text}"
    return "素材尚未 AI 识别，先按素材顺序和镜头节奏轮换。"


def _asset_ai_tags(asset: Asset | None) -> dict:
    if not asset or not asset.ai_tags:
        return {}
    try:
        data = json.loads(asset.ai_tags)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _as_text_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _first_text(value) -> str:
    items = _as_text_list(value)
    return items[0] if items else ""


def _keyword_tokens(text: str) -> list[str]:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text.lower())
    chunks = [part.strip() for part in cleaned.split() if len(part.strip()) >= 2]
    tokens: list[str] = []
    for chunk in chunks:
        tokens.append(chunk)
        if re.search(r"[\u4e00-\u9fff]", chunk) and len(chunk) > 4:
            tokens.extend(chunk[i : i + 2] for i in range(0, len(chunk) - 1, 2))
    return list(dict.fromkeys(tokens))[:80]


def _source_start(asset: Asset | None, cursor: float, duration: float) -> float:
    if not asset:
        return 0
    if not asset.duration:
        # 没有 ffprobe 元信息时，仍然错开取素材开头，避免每次都重复同一秒。
        # 若素材本身很短，建议安装 ffmpeg 后重新生成 timeline 以获得精确时长。
        return round((cursor * 0.61) % 30, 3) if asset.asset_type == "video" else 0
    if asset.duration <= duration + 0.5:
        return 0
    usable = max(0.0, float(asset.duration) - duration - 0.2)
    return round((cursor * 0.73) % usable, 3)


def _asset_signature(assets: list[Asset]) -> str:
    parts = [
        f"{asset.id}:{asset.asset_type}:{asset.filename}:{asset.path}:{asset.duration or ''}"
        for asset in sorted(assets, key=lambda item: item.id)
    ]
    return "|".join(parts)


