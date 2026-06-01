# 本地 AI 视频粗剪助手架构与开发计划

## 第一阶段 MVP 目标

做出一个 Windows 本地可运行原型，完成：

1. 创建视频项目。
2. 上传 txt / md 文稿并保存原文。
3. 按 5-10 分钟中长视频逻辑生成 mock 分镜表 `storyboard.json`。
4. 上传视频、图片、音频素材并建立素材库。
5. 使用 ffmpeg / ffprobe 提取素材元信息与视频关键帧缩略图。
6. 根据分镜与素材生成 mock `timeline.json`。
7. 优先尝试使用 `pyJianYingDraft` 生成剪映草稿；不可用时输出可供后续草稿生成器使用的 timeline/storyboard/说明文件。
8. 提供 React 页面让用户串完整流程。

## 技术架构

```text
frontend/ React + Vite
  src/pages
    ProjectListPage       项目列表
    ProjectCreatePage     项目创建
    ScriptUploadPage      文稿上传与生成分镜
    AssetLibraryPage      素材库
    StoryboardEditorPage  分镜表编辑
    TimelinePreviewPage   timeline 预览
    DraftExportPage       生成剪映草稿

backend/ FastAPI
  app/api/routes          API 路由
  app/db                  SQLite 模型与 session
  app/services
    ai_service.py         AI 抽象接口，第一版 mock
    script_service.py     文稿读取与段落切分
    asset_service.py      ffmpeg / ffprobe 素材处理
    storyboard_service.py storyboard 持久化与编辑
    timeline_service.py   素材匹配与 timeline 生成
    jianying_service.py   剪映草稿生成适配与 fallback
```

## 数据流

```text
项目设置
  -> 上传文稿
  -> mock AI 生成 storyboard.json
  -> 上传素材并提取元信息
  -> 根据 storyboard + assets 生成 timeline.json
  -> pyJianYingDraft 生成剪映草稿，或 fallback 输出草稿生成包
```

## 剪映草稿策略

- 不自动点击剪映，不做 GUI 自动化。
- `pyJianYingDraft` 用于直接生成草稿文件夹。
- 模板模式受剪映版本限制：剪映 6+ 的 `draft_content.json` 加密会影响加载 6+ 模板草稿。
- 草稿生成功能本身据项目 README 描述支持剪映 5+，但不同剪映版本仍可能需要实机验证。
- MVP 提供 fallback：即使本机没有安装 `pyJianYingDraft` 或未配置草稿目录，也会输出 `timeline.json`、`storyboard.json`、`draft_generation_notes.md`。

## 后续阶段

1. 接入真实 LLM，替换 mock AI service。
2. 强化素材匹配：标签、语义检索、镜头密度、素材复用策略。
3. 增加字幕 SRT、配音、音乐节奏点。
4. 增加可视化 timeline 播放预览。
5. 做剪映版本兼容矩阵与草稿导入验证。
