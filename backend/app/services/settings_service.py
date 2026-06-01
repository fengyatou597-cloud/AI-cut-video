import json
import os
from pathlib import Path
from app.core.config import settings

CONFIG_PATH = settings.storage_path / "app_settings.json"

DEFAULT_CONFIG = {
    "jianying_drafts_dir": "",
    "fallback_export_dir": "",
    "ai_enabled": False,
    "ai_provider": "openai_compatible",
    "ai_base_url": "",
    "ai_api_key": "",
    "ai_text_model": "",
    "ai_vision_model": "",
    "ai_text_base_url": "",
    "ai_text_api_key": "",
    "ai_vision_base_url": "",
    "ai_vision_api_key": "",
}

DRAFT_DIR_NAMES = {
    "com.lveditor.draft",
    "com.lemon.lvpro.draft",
    "com.lveditor.draft.root",
}


def load_user_config() -> dict:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DEFAULT_CONFIG.copy()
    return {**DEFAULT_CONFIG, **data}


def save_user_config(payload: dict) -> dict:
    current = load_user_config()
    incoming = {key: value for key, value in payload.items() if key in DEFAULT_CONFIG}
    for secret_key in ("ai_api_key", "ai_text_api_key", "ai_vision_api_key"):
        if secret_key in incoming and not str(incoming[secret_key]).strip():
            incoming.pop(secret_key)
    updated = {**current, **incoming}
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    return updated


def get_jianying_drafts_dir() -> str:
    user_value = load_user_config().get("jianying_drafts_dir") or ""
    return user_value.strip() or (settings.jianying_drafts_dir or "")


def get_fallback_export_root() -> Path:
    configured = (load_user_config().get("fallback_export_dir") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return settings.storage_path / "draft_exports"


def get_project_fallback_export_dir(project_id: int, safe_title: str) -> Path:
    return get_fallback_export_root() / f"project_{project_id}" / safe_title


def get_app_settings() -> dict:
    config = load_user_config()
    effective_drafts_dir = get_jianying_drafts_dir()
    fallback_root = get_fallback_export_root()
    return {
        **{key: value for key, value in config.items() if key not in {"ai_api_key", "ai_text_api_key", "ai_vision_api_key"}},
        "ai_api_key_configured": bool((config.get("ai_api_key") or "").strip()),
        "ai_text_api_key_configured": bool((config.get("ai_text_api_key") or config.get("ai_api_key") or "").strip()),
        "ai_vision_api_key_configured": bool((config.get("ai_vision_api_key") or config.get("ai_api_key") or "").strip()),
        "effective_ai_text_model": _effective_model(config, "text"),
        "effective_ai_vision_model": _effective_model(config, "vision"),
        "effective_jianying_drafts_dir": effective_drafts_dir,
        "effective_fallback_export_dir": str(fallback_root),
        "fallback_export_dir_exists": fallback_root.exists() and fallback_root.is_dir(),
        "storage_dir": str(settings.storage_path),
    }


def _effective_model(config: dict, kind: str) -> str:
    if kind == "vision":
        configured = (config.get("ai_vision_model") or "").strip()
        if configured:
            return configured
        base_url = (config.get("ai_vision_base_url") or config.get("ai_base_url") or config.get("ai_text_base_url") or "").lower()
        if "dashscope.aliyuncs.com" in base_url:
            return "qwen-vl-plus"
        return ""
    configured = (config.get("ai_text_model") or "").strip()
    if configured:
        return configured
    base_url = (config.get("ai_text_base_url") or config.get("ai_base_url") or config.get("ai_vision_base_url") or "").lower()
    if "dashscope.aliyuncs.com" in base_url:
        return "qwen-plus"
    return ""


def discover_jianying_draft_dirs() -> dict:
    candidates = []
    for path in _candidate_paths():
        candidates.append(_candidate_payload(path, source="known_path"))

    for base in _search_bases():
        if not base.exists():
            continue
        for found in _safe_find_draft_dirs(base, max_depth=5):
            candidates.append(_candidate_payload(found, source="limited_scan"))

    deduped = {}
    for candidate in candidates:
        key = candidate["path"].lower()
        if key not in deduped or candidate["exists"]:
            deduped[key] = candidate

    sorted_candidates = sorted(
        deduped.values(),
        key=lambda item: (not item["exists"], -item["score"], item["path"]),
    )
    return {
        "candidates": sorted_candidates[:20],
        "recommended": next((item for item in sorted_candidates if item["exists"]), None),
        "searched_roots": [str(path) for path in _search_bases() if path.exists()],
        "tips": [
            "如果没有候选路径，请先打开剪映并创建一个空草稿，再回到这里重新扫描。",
            "不同剪映版本和安装渠道路径不同，本工具只扫描用户目录下的常见位置，不做全盘搜索。",
        ],
    }


def _candidate_paths() -> list[Path]:
    local_app_data = Path(os.environ.get("LOCALAPPDATA", "")) if os.environ.get("LOCALAPPDATA") else None
    app_data = Path(os.environ.get("APPDATA", "")) if os.environ.get("APPDATA") else None
    user_profile = Path(os.environ.get("USERPROFILE", "")) if os.environ.get("USERPROFILE") else None
    extra_roots = [Path("D:/"), Path("D:/JianyingPro"), Path("D:/CapCut"), Path("D:/剪映")]
    roots = [path for path in [local_app_data, app_data, user_profile, *extra_roots] if path]

    relative_patterns = [
        Path("JianyingPro") / "User Data" / "Projects" / "com.lveditor.draft",
        Path("JianyingPro") / "User Data" / "Projects" / "com.lemon.lvpro.draft",
        Path("CapCut") / "User Data" / "Projects" / "com.lveditor.draft",
        Path("CapCut") / "User Data" / "Projects" / "com.lemon.lvpro.draft",
        Path("剪映专业版") / "User Data" / "Projects" / "com.lveditor.draft",
        Path("User Data") / "Projects" / "com.lveditor.draft",
        Path("Projects") / "com.lveditor.draft",
        Path("com.lveditor.draft"),
    ]
    paths = []
    for root in roots:
        for pattern in relative_patterns:
            paths.append(root / pattern)
    return paths


def _search_bases() -> list[Path]:
    bases = []
    for env_name in ("LOCALAPPDATA", "APPDATA"):
        value = os.environ.get(env_name)
        if value:
            bases.append(Path(value))
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        bases.extend([Path(user_profile) / "AppData" / "Local", Path(user_profile) / "Documents"])
    for drive in ("D:/",):
        drive_path = Path(drive)
        if drive_path.exists():
            bases.extend([drive_path / "JianyingPro", drive_path / "CapCut", drive_path / "剪映"])
    return list(dict.fromkeys(bases))


def _safe_find_draft_dirs(base: Path, max_depth: int) -> list[Path]:
    found = []
    stack = [(base, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            continue
        try:
            children = list(current.iterdir())
        except (PermissionError, OSError):
            continue
        for child in children:
            if not child.is_dir():
                continue
            if child.name in DRAFT_DIR_NAMES:
                found.append(child)
                continue
            name_lower = child.name.lower()
            if depth < max_depth and _worth_descending(name_lower, depth):
                stack.append((child, depth + 1))
    return found


def _worth_descending(name_lower: str, depth: int) -> bool:
    if depth <= 1:
        return True
    keywords = ["jianying", "capcut", "lveditor", "lemon", "projects", "user data", "剪映"]
    return any(keyword in name_lower for keyword in keywords)


def _candidate_payload(path: Path, source: str) -> dict:
    exists = path.exists() and path.is_dir()
    score = 0
    if exists:
        score += 100
    lowered = str(path).lower()
    if "jianying" in lowered or "剪映" in lowered:
        score += 20
    if "projects" in lowered:
        score += 10
    if path.name == "com.lveditor.draft":
        score += 10
    return {
        "path": str(path),
        "exists": exists,
        "source": source,
        "score": score,
    }
