STYLE_TEMPLATES = {
    "社科解释型": {
        "name": "社科解释型",
        "visual_language": "论文截图、新闻截图、数据图表、黑底白字段落转场",
        "subtitle_style": "干净克制，关键词高亮",
        "pacing_hint": "逻辑清晰，每 20-40 秒一个论点，每 5-8 秒视觉变化",
        "default_effects": ["keyword_highlight", "black_card_transition", "chart_callout"],
    },
    "情绪共鸣型": {
        "name": "情绪共鸣型",
        "visual_language": "生活化 B-roll、人物背影、城市夜景、慢推镜头",
        "subtitle_style": "更有文学感，留白多",
        "pacing_hint": "节奏稍慢，重视情绪递进和回扣",
        "default_effects": ["slow_zoom_in", "soft_fade", "ambient_broll"],
    },
    "B站知识型": {
        "name": "B站知识型",
        "visual_language": "知识点拆解、吐槽花字、截图标注、快速切镜",
        "subtitle_style": "关键词大字，适量花字",
        "pacing_hint": "节奏更快，每 5 秒左右有明显信息或画面变化",
        "default_effects": ["pop_text", "quick_cut", "zoom_punch"],
    },
    "小红书口播型": {
        "name": "小红书口播型",
        "visual_language": "竖屏口播、大字幕、封面感强、信息点明确",
        "subtitle_style": "大字号，每屏文字少",
        "pacing_hint": "短段落强信息密度，适合竖屏",
        "default_effects": ["big_caption", "cover_title", "clean_slide"],
    },
}

PLATFORMS = ["B站", "小红书", "抖音", "视频号", "其他"]
TARGET_DURATIONS = ["5分钟", "8分钟", "10分钟", "自定义"]
PACING_OPTIONS = ["稳重", "中等", "快节奏"]
