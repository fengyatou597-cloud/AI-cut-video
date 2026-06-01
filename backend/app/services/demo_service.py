from pathlib import Path
from sqlalchemy.orm import Session
from app.db.models import Project, Script, Storyboard, Timeline
from app.services.ai_service import build_mock_storyboard, dumps_json as dumps_storyboard
from app.services.timeline_service import build_mock_timeline, dumps_json as dumps_timeline

DEMO_SCRIPT = """为什么我们越努力，越容易陷入焦虑？

很多人以为，焦虑来自不够努力。只要再自律一点、再卷一点、再多学一点，就能把生活重新拉回掌控之中。但奇怪的是，很多时候我们越努力，越感觉自己被追着跑。

这背后有一个很重要的变化：我们面对的不是单一目标，而是一整套不断移动的评价系统。工作要有结果，生活要有质感，关系要经营，身体要管理，情绪还要稳定。每一项看起来都合理，但叠在一起，就变成一种无形的压力。

更麻烦的是，互联网让比较变得无处不在。你看到的不是一个完整的人，而是别人生活里最亮、最浓缩、最适合展示的片段。于是我们很容易把自己的后台，拿去和别人的高光时刻比较。

这种比较会制造一种错觉：好像所有人都在快速前进，只有自己站在原地。可是事实往往不是这样。大多数人也在试错、停顿、怀疑，只是这些部分通常不会被放到屏幕上。

所以，缓解焦虑的第一步，可能不是继续逼自己更快，而是重新分辨：哪些目标真的属于我，哪些只是外界塞给我的标准。一个人不可能同时优化人生的所有维度，选择本身就是一种能力。

当我们允许自己阶段性地只解决一两个真正重要的问题，生活反而会变得清楚。不是因为压力消失了，而是因为我们终于不再把每一种声音都当成命令。

最后想说的是，焦虑并不总是敌人。它有时候是在提醒我们：现在的节奏、目标或者关系，可能已经需要重新调整。真正重要的不是彻底消灭焦虑，而是学会听懂它在说什么。
"""


def create_demo_project(db: Session) -> dict:
    project = Project(
        title="Demo：为什么越努力越焦虑",
        platform="B站",
        target_duration="5分钟",
        style="社科解释型",
        pacing="中等",
        needs_hook=True,
        needs_broll=True,
        needs_research_visuals=True,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    script_path = Path("storage") / "projects" / str(project.id) / "scripts" / "demo_script.md"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(DEMO_SCRIPT, encoding="utf-8")

    script = Script(
        project_id=project.id,
        filename="demo_script.md",
        path=str(script_path.resolve()),
        content=DEMO_SCRIPT,
    )
    db.add(script)
    db.commit()

    storyboard = build_mock_storyboard(project, DEMO_SCRIPT)
    db.add(Storyboard(project_id=project.id, data=dumps_storyboard(storyboard)))
    db.commit()

    timeline = build_mock_timeline(storyboard, [])
    db.add(Timeline(project_id=project.id, data=dumps_timeline(timeline)))
    db.commit()

    return {
        "project_id": project.id,
        "project": {
            "id": project.id,
            "title": project.title,
            "platform": project.platform,
            "target_duration": project.target_duration,
            "style": project.style,
            "pacing": project.pacing,
        },
        "created": ["project", "script", "storyboard", "timeline"],
        "next_href": f"/projects/{project.id}/storyboard",
        "message": "示例项目已创建，已自动生成文稿、分镜和 timeline。素材为空，所以 timeline 使用 placeholder。",
    }
