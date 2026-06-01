# 本地 AI 视频粗剪助手 MVP

这是一个本地优先的 AI 视频粗剪助手原型，目标服务 5-10 分钟中长视频，而不是几十秒短视频。当前主要在 Windows 上验证，macOS 已提供基础安装/启动脚本，剪映草稿直写能力仍需在 macOS 剪映/CapCut 上实机验证。

如果你不懂代码，优先看：

```text
使用说明.md
```

当前第一阶段支持：

- 创建视频项目。
- 上传 `txt` / `md` / `docx` 文稿。
- 上传 `.srt` 字幕，生成 timeline 时优先使用 SRT 的精确时间轴。
- 使用 mock AI service 生成 `storyboard.json`。
- 上传视频、图片、音频素材并建立素材库。
- 使用 `ffmpeg` / `ffprobe` 提取视频时长、分辨率和关键帧缩略图。
- 根据分镜、素材、旁白音频和 SRT 生成 `timeline.json`。
- 优先尝试使用 `pyJianYingDraft` 生成剪映草稿；不可用时输出 fallback 草稿生成包。
- 可在“本地设置”里配置 OpenAI-compatible AI API，用真实模型生成分镜和识别素材。

> 第一版不会自动操作鼠标或点击剪映，也不会自动导出成片。

## 项目结构

```text
backend/
  app/
    api/routes/          FastAPI 路由
    core/                配置
    db/                  SQLite 模型与 session
    services/            文稿、AI、素材、timeline、剪映草稿服务
  requirements.txt
  .env.example
frontend/
  src/
    api/                 API client
    components/          布局组件
    pages/               7 个 MVP 页面
docs/
  ARCHITECTURE_AND_PLAN.md
```

## 环境要求

- Windows 10/11，或 macOS 13+。
- Python 3.11+ 推荐。
- Node.js 20+ 可选：普通使用 release 包时不需要；只有需要重新构建前端页面时才需要。
- ffmpeg / ffprobe。
- 可选：剪映/CapCut 客户端。
- `pyJianYingDraft`：已写入后端依赖，用于尝试直接生成剪映草稿。

## 非技术用户快速启动

Windows 第一次使用：

```text
1. 双击 check_environment.bat
2. 双击 install_windows.bat
3. 双击 start_windows.bat
```

Windows 以后使用：

```text
双击 start_windows.bat
```

macOS 第一次使用：

```bash
cd 项目目录
chmod +x check_environment_mac.sh install_mac.sh start_mac.sh
./check_environment_mac.sh
./install_mac.sh
./start_mac.sh
```

macOS 以后使用：

```bash
cd 项目目录
./start_mac.sh
```

浏览器会打开：

```text
http://localhost:8000
```

release 包会自带已经构建好的前端页面。启动时只需要一个本地服务：FastAPI 后端会同时提供 API 和网页，不需要同事理解“前端端口/后端端口”两个窗口。

建议把项目放在英文路径里，例如：

```text
D:\AI_RoughCut_Assistant
~/AI_RoughCut_Assistant
```

避免放在含中文、特殊符号或云盘同步目录里，Python 虚拟环境在这些路径下更容易出问题。

首页可以点击“生成示例项目”快速试跑。

## 发给同事 / 上传 GitHub 前必看

这个项目是“本地运行”的工具。每个人下载后都应该拥有自己的空数据库、自己的素材库、自己的剪映路径和自己的 AI API Key。

不要上传这些本机运行数据：

```text
backend/storage/
backend/.venv/
frontend/node_modules/
logs/
backend/.env
```

这些目录/文件已经写入 `.gitignore`，正常用 Git 或 GitHub Desktop 提交时不会被上传。

注意：`frontend/dist/` 需要保留。它是已经构建好的网页页面，release 包靠它做到“同事不装 Node 也能打开网页”。

更稳的方式是先生成一份干净发布副本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\make_release_copy.ps1
```

脚本会生成：

```text
release/ai-video-rough-cut-assistant/
release/ai-video-rough-cut-assistant.zip
```

这个副本不包含你的：

- SQLite 数据库。
- 上传过的文稿、素材、音频、字幕。
- 剪映草稿输出和备份。
- API Key。
- 本机剪映目录配置。
- Python 虚拟环境和 Node 依赖目录。

如果你要发给同事，优先发 `release/ai-video-rough-cut-assistant.zip`。同事解压后按说明运行即可。

如果对方电脑没有 Python，轻量 zip 仍然打不开。可以生成 Windows 便携版：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\make_windows_portable_release.ps1
```

它会生成：

```text
release/ai-video-rough-cut-assistant-windows-portable.zip
```

这个包会带 Python 运行环境和后端依赖，Windows 同事通常解压后双击 `start_windows.bat` 就能打开。缺点是体积会明显更大。

上传前可以再跑一次检查：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\preflight_github.ps1
```

如果检查通过，再上传到 GitHub。

同事下载后第一次使用：

```text
1. 双击 check_environment.bat
2. 双击 install_windows.bat
3. 双击 start_windows.bat
4. 打开网页左侧“本地设置”
5. 扫描/填写他自己电脑上的剪映草稿目录
6. 填写他自己的 AI API 配置
```

每个同事的配置会保存在他自己电脑的：

```text
backend/storage/app_settings.json
```

这个文件不会进入 GitHub。

## 安装 ffmpeg

推荐使用 winget：

```powershell
winget install Gyan.FFmpeg
```

macOS 推荐使用 Homebrew：

```bash
brew install ffmpeg
```

安装后确认：

```powershell
ffmpeg -version
ffprobe -version
```

如果没有安装 ffmpeg，素材上传仍可保存文件，但视频时长、分辨率和关键帧缩略图可能为空。

## 运行后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

也可以使用脚本：

```powershell
.\scripts\start_backend.ps1
```

后端健康检查：

```text
http://localhost:8000/api/health
```

SQLite 数据库默认写入：

```text
backend/storage/app.db
```

上传文件和草稿输出默认写入：

```text
backend/storage/projects/
```

## 运行前端

```powershell
cd frontend
npm install
npm run dev
```

如果 PowerShell 因执行策略拦截 `npm.ps1`，可改用：

```powershell
npm.cmd install
npm.cmd run dev
```

也可以使用脚本：

```powershell
.\scripts\start_frontend.ps1
```

打开：

```text
http://localhost:5173
```

开发模式可以继续使用 `5173`。普通同事日常使用请双击根目录的 `start_windows.bat`，它会打开：

```text
http://localhost:8000
```

如需修改后端地址，可设置：

```powershell
$env:VITE_API_BASE_URL="http://localhost:8000"
```

## 配置剪映草稿路径

如果只想先跑通 MVP，不需要配置剪映路径。点击“生成剪映草稿”时，系统会输出 fallback 包：

```text
storyboard.json
timeline.json
subtitles.srt
draft_generation_notes.md
```

如要尝试直接生成剪映草稿：

1. 安装 `pyJianYingDraft`。
2. 在 `backend/.env` 配置 `JIANYING_DRAFTS_DIR`。

示例：

```env
JIANYING_DRAFTS_DIR=C:\Users\你的用户名\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft
```

不同剪映版本和安装渠道的路径可能不同。现在可以在网页左侧“本地设置”里点击“扫描候选路径”，优先使用系统找到的推荐目录。

macOS 说明：

- 网页、文稿、素材库、AI、timeline、fallback 包都可以按本地方式运行。
- 直接写入 macOS 剪映/CapCut 草稿目录尚未充分验证。
- 如果网页扫描不到 macOS 草稿目录，可以先使用 fallback 包；后续需要在一台装了剪映/CapCut 的 Mac 上确认实际草稿目录和 pyJianYingDraft 兼容性。

## 配置 AI API

网页左侧进入：

```text
本地设置
```

填写：

- `API Base URL`：兼容 OpenAI `/chat/completions` 的国内模型网关地址。
- `API Key`：你的本地 key。页面不会回显完整 key，留空保存会保留原 key。
- `文本模型`：用于理解文稿、生成 storyboard。
- `视觉模型`：用于识别图片和视频关键帧，给素材打标签。没有视觉模型可以先留空。

如果文本模型和视觉模型来自同一个平台，只填“通用 API 配置”即可；如果来自不同平台，可以分别填写“文本模型配置”和“视觉模型配置”。专用配置优先级高于通用配置。

当前调用方式是 OpenAI-compatible：

```text
POST {API Base URL}/v1/chat/completions
Authorization: Bearer <API Key>
```

如果你的平台给的地址已经是 `/v1` 或 `/chat/completions`，系统会自动拼接/识别。

AI 启用后：

- 生成 storyboard 会优先调用真实文本模型，失败时自动回退 mock。
- 素材库里的“AI 识别素材”会调用视觉模型或文本模型，为素材生成 summary、tags、适用场景和建议动效。
- 视频素材需要 ffmpeg 抽关键帧后，视觉模型才能真正看到画面；否则只能根据文件名和元信息粗略判断。

## 剪映版本限制

当前实现遵循“优先直接生成草稿，失败则输出中间格式”的策略。

- 本项目不做 GUI 自动化，不自动点击剪映。
- `pyJianYingDraft` 可用于生成 Jianying / CapCut 草稿文件夹。
- `pyJianYingDraft` 项目说明中提到草稿生成功能通常支持剪映 5+。
- 但模板读取功能受版本影响：剪映 6+ 的 `draft_content.json` 加密会限制加载 6+ 模板草稿。
- 本 MVP 只尝试基础轨道、视频/图片、文本、字幕、音频写入；复杂模板、自动导出、自动打开剪映不在第一阶段。
- 如果 `pyJianYingDraft` 未安装、路径未配置、API 变化或本机剪映版本不兼容，后端会降级输出 `timeline.json` 包。

## 从文稿生成 storyboard

接口：

```http
POST /api/projects/{project_id}/script/generate-storyboard
```

页面路径：

```text
/projects/{project_id}/script
```

当前逻辑位于：

```text
backend/app/services/ai_service.py
backend/app/services/script_service.py
```

第一版是 mock AI：

- 按段落/长段落拆分，而不是按单句切分。
- 每段估算 12-45 秒。
- 每段内部自动拆出 5-8 秒左右的 shots。
- 生成段落标题、旁白、目的、核心信息、情绪、画面建议、素材需求、关键词、花字、动效、转场。

后续接真实模型时，只需要替换 `ai_service.py`，不要把 OpenAI API 写死到路由里。

## 从 storyboard 生成 timeline

接口：

```http
POST /api/projects/{project_id}/timeline/generate
```

页面路径：

```text
/projects/{project_id}/timeline
```

当前逻辑位于：

```text
backend/app/services/timeline_service.py
```

生成结果包含：

- video track
- text track
- subtitle track
- audio track

如果没有上传视频/图片素材，timeline 会使用 placeholder，并在 `warnings` 中说明。

timeline 页面现在提供轨道式预览：

- 顶部显示总时长、视频镜头数、花字数、字幕条数和已匹配素材数。
- 按视频/图片、花字/标题、字幕、音频分层展示。
- 点击任意片段可查看开始时间、时长、段落、shot、素材名、效果/样式和备注。
- 新生成的 video item 会包含 `shot_id`、`asset_name`、`track_label`，方便排查 storyboard shots 到 timeline clips 的映射。

## 分镜表编辑器

页面路径：

```text
/projects/{project_id}/storyboard
```

当前支持：

- 手动修改段落标题、旁白、目的、核心信息、画面建议、素材需求、缺失素材、字幕重点词、花字、动效、转场、节奏和估算时长。
- 新增、复制、删除段落。
- 按旁白重新估算单段或全部段落时长。
- 按段落时长和风格模板重建内部 shots。
- 展开编辑每个 shot 的开始时间、时长、素材类型、动效和画面变化说明。

保存后的 storyboard 会被 timeline 生成器直接使用。也就是说，如果你手动调整了 shots，下一次生成 `timeline.json` 会按这些 shots 来切镜。

## 生成剪映草稿

接口：

```http
GET /api/projects/{project_id}/draft/environment
```

```http
POST /api/projects/{project_id}/draft/generate
```

页面路径：

```text
/projects/{project_id}/draft
```

当前逻辑位于：

```text
backend/app/services/jianying_service.py
```

导出页会先做环境检查：

- 是否已有 storyboard。
- 是否已有 timeline。
- 是否配置 `JIANYING_DRAFTS_DIR`。
- 剪映草稿目录是否存在。
- 当前 Python 环境是否能导入 `pyJianYingDraft`。
- 是否能在 PATH 中找到 `ffmpeg`。
- 是否能在 PATH 中找到 `ffprobe`。
- 当前导出模式是 `pyjianyingdraft` 还是 `fallback_timeline_package`。
- 点击生成后预计输出哪些文件。

输出模式：

- `pyjianyingdraft`：已调用 `pyJianYingDraft` 生成基础剪映草稿，并写入剪映草稿目录。成功后不用导入 ZIP，直接打开剪映，在本地草稿列表里找同名草稿。
- `pyjianyingdraft_failed_fallback`：尝试失败，已输出 fallback 包，并写入错误文件。
- `fallback_timeline_package`：未配置或未安装 `pyJianYingDraft`，输出 timeline 包。

如果导出历史显示 `pyjianyingdraft`，说明已经生成了可被剪映识别的草稿文件夹。页面上的“备份 ZIP”只是备份用，不是剪映导入入口。剪映列表没立刻刷新时，退出当前草稿页再进入一次，或重启剪映。

## 内置风格模板

- 社科解释型：逻辑清晰、关键词高亮、论文/新闻/图表、黑底白字段落转场。
- 情绪共鸣型：节奏稍慢、生活化 B-roll、慢推、文学感字幕。
- B站知识型：节奏更快、花字更多、吐槽提示、画面频繁变化。
- 小红书口播型：大字幕、封面感强、信息点明确、竖屏友好。

模板定义在：

```text
backend/app/services/style_templates.py
```

## 当前还没实现的功能

- 真实 AI 模型调用。
- docx 文稿解析。
- 语义级素材匹配。
- 自动配音。
- 自动配乐与节奏点匹配。
- 自动生成封面。
- 可播放的 timeline 预览器。
- 复杂剪映模板。
- 自动打开剪映、自动点击、自动导出。
- 多用户权限、登录、云同步。

## 推荐使用流程

1. 创建项目。
2. 上传文稿。
3. 上传你提前准备好的 `.srt` 字幕。没有 SRT 时，系统会从文稿粗略切字幕。
4. 生成 storyboard mock。
5. 到分镜表编辑页人工确认旁白、画面、素材、花字、动效、节奏和时长。
6. 上传视频、图片、旁白录音、音乐素材。第一个音频会作为主旁白轨，第二个音频会作为低音量背景音乐占位。
7. 生成 timeline mock。timeline 会优先使用 SRT 时间轴、旁白音频和素材库，并给镜头分配基础动效/转场策略。
8. 生成剪映草稿或 fallback 输出包。
9. 在剪映中人工微调和导出。

## 项目工作台

首页使用：

```http
GET /api/projects/overview
```

它会汇总每个项目的流程状态：

- 是否上传过文稿。
- 是否生成过分镜表。
- 素材数量。
- 是否生成过 timeline。
- 导出次数。
- 总进度百分比。
- 下一步应该进入哪个页面。

这样用户回到项目列表时，可以直接看到项目卡在哪一步，而不是逐页点进去猜。

## 快速演示

如果只是想快速看到完整链路，可以在首页点击“生成示例项目”。它会调用：

```http
POST /api/demo/seed
```

系统会自动创建：

- 一个 B站/社科解释型示例项目。
- 一篇内置 demo 文稿。
- `storyboard.json`。
- `timeline.json`。

示例项目没有素材，所以 timeline 的视频轨会使用 placeholder。你可以随后进入素材库上传视频/图片，再重新生成 timeline。

示例文稿也放在：

```text
docs/demo_script.md
```

## 本地检查

```powershell
.\scripts\run_checks.ps1
```

该脚本会执行后端 Python 语法检查和前端 Vite 构建。



