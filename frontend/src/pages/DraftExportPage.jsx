import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, apiBase } from "../api/client";
import { ProjectNav, StatusBox } from "../components/Layout";

export function DraftExportPage() {
  const { projectId } = useParams();
  const [environment, setEnvironment] = useState(null);
  const [exportsList, setExportsList] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const [envResult, exportsResult] = await Promise.all([
      api.getDraftEnvironment(projectId),
      api.listDraftExports(projectId),
    ]);
    setEnvironment(envResult);
    setExportsList(exportsResult);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, [projectId]);

  async function generate() {
    setMessage(environment?.direct_draft_available ? "正在写入剪映草稿目录..." : "正在生成 fallback 粗剪包...");
    setError("");
    try {
      const result = await api.generateDraft(projectId);
      setMessage(result.message);
      await refresh();
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  return (
    <section>
      <ProjectNav />
      <p className="eyebrow">Step 6</p>
      <h1>生成剪映草稿</h1>
      <div className="card warning-card">
        <h3>这里真正做什么</h3>
        <p>环境满足时，点击按钮会把基础粗剪草稿直接写进剪映草稿目录。之后如果你在“AI 修改”里改了字幕、画幅、花字或动效，再点这里会更新同名草稿，不会每次新建一堆草稿。找不到剪映目录时，可以先去<Link to="/settings">本地设置</Link>扫描候选路径。</p>
      </div>

      <StatusBox>{message}</StatusBox>
      <StatusBox type="error">{error}</StatusBox>

      {environment ? (
        <>
          <EnvironmentPanel environment={environment} />
          <SuccessGuide exportsList={exportsList} />
          <ExportPlan environment={environment} />
          <div className="toolbar">
            <button className="primary" onClick={generate} disabled={!environment.ready_to_export}>
              {environment.direct_draft_available ? "生成 / 更新剪映草稿" : "生成 fallback 粗剪包"}
            </button>
            <button onClick={refresh}>重新检查环境</button>
          </div>
        </>
      ) : (
        <p className="muted">正在检查导出环境...</p>
      )}

      <div className="exports-list">
        <h2>导出历史</h2>
        {exportsList.map((item) => (
          <article className={`card export-card ${item.mode === "pyjianyingdraft" ? "direct-draft" : ""}`} key={item.id}>
            <span className="pill">{modeLabel(item.mode)}</span>
            <h3>{item.output_path}</h3>
            <p>{item.message}</p>
            {item.mode === "pyjianyingdraft" && (
              <p className="direct-tip">这是已经写入剪映的草稿文件夹。请打开剪映，在本地草稿列表里找：<strong>{draftName(item.output_path)}</strong></p>
            )}
            <div className="toolbar">
              <a className="primary" href={`${apiBase}${item.download_url}`}>{item.mode === "pyjianyingdraft" ? "备份 ZIP" : "下载 ZIP"}</a>
              <span className={item.output_exists ? "export-ok" : "export-missing"}>{item.output_exists ? "文件存在" : "文件不见了"}</span>
            </div>
          </article>
        ))}
        {!exportsList.length && <p className="muted">还没有导出记录。环境检查通过后，可以先生成一个 fallback 包试跑。</p>}
      </div>
    </section>
  );
}

function SuccessGuide({ exportsList }) {
  const latestDraft = exportsList.find((item) => item.mode === "pyjianyingdraft" && item.output_exists);
  if (!latestDraft) {
    return null;
  }
  return (
    <div className="success-guide card">
      <span className="pill">已生成可打开草稿</span>
      <h2>{draftName(latestDraft.output_path)}</h2>
      <p>这个草稿已经写入剪映草稿目录。下一步打开剪映专业版，如果列表没立刻刷新，退出当前草稿页再进入一次，或者重启剪映。</p>
      <div className="mini-steps">
        <span>1. 打开剪映</span>
        <span>2. 在本地草稿列表找这个名字</span>
        <span>3. 打开后人工微调并导出</span>
      </div>
    </div>
  );
}

function EnvironmentPanel({ environment }) {
  const checks = [
    {
      label: "Storyboard",
      ok: environment.has_storyboard,
      detail: environment.has_storyboard ? "已生成" : "缺少 storyboard",
    },
    {
      label: "Timeline",
      ok: environment.has_timeline,
      detail: environment.has_timeline ? "已生成" : "缺少 timeline",
    },
    {
      label: "剪映草稿目录",
      ok: environment.has_drafts_dir && environment.drafts_dir_exists,
      detail: environment.configured_drafts_dir || "未配置 JIANYING_DRAFTS_DIR",
    },
    {
      label: "粗剪包输出目录",
      ok: Boolean(environment.fallback_export_dir),
      detail: environment.fallback_export_dir || "使用默认 storage 目录",
    },
    {
      label: "pyJianYingDraft",
      ok: environment.pyjianying_available,
      detail: environment.pyjianying_available ? "当前 Python 环境可导入" : "未安装或不可导入",
    },
    {
      label: "ffmpeg",
      ok: environment.ffmpeg_available,
      detail: environment.ffmpeg_path || "未在 PATH 找到",
    },
    {
      label: "ffprobe",
      ok: environment.ffprobe_available,
      detail: environment.ffprobe_path || "未在 PATH 找到",
    },
  ];

  return (
    <div className="env-panel">
      <div className="env-mode-card">
        <span className="pill">当前导出模式</span>
        <h2>{environment.direct_draft_available ? "可直接生成剪映草稿" : "只能生成 fallback 粗剪包"}</h2>
        <p>{environment.direct_draft_available ? "点击生成后会写入剪映草稿目录，剪映里应出现一个新草稿。" : "将输出 storyboard、timeline、字幕和说明文件，暂不能直接在剪映里打开。"}</p>
      </div>
      <div className="env-check-grid">
        {checks.map((check) => (
          <article className={`env-check ${check.ok ? "ok" : "warn"}`} key={check.label}>
            <strong>{check.ok ? "可用" : "注意"}</strong>
            <h3>{check.label}</h3>
            <p>{check.detail}</p>
          </article>
        ))}
      </div>
      {!!environment.blockers?.length && (
        <div className="card blocker-card">
          <h3>当前提示</h3>
          <ul>
            {environment.blockers.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function ExportPlan({ environment }) {
  return (
    <div className="export-plan card">
      <div>
        <span className="pill">导出计划</span>
        <h3>点击生成后会产出这些内容</h3>
        <p>{environment.direct_draft_available ? "这次会优先生成剪映真实草稿，同时保留可排错的中间文件。" : "当前缺少直接生成条件，所以只会输出可排错、可交给草稿生成器消费的中间文件。"}</p>
      </div>
      <div className="output-list">
        {(environment.expected_outputs || []).map((item) => (
          <div className="output-item" key={item.name}>
            <strong>{item.name}</strong>
            <span>{item.description}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function draftName(outputPath = "") {
  return outputPath.split(/[\\/]/).filter(Boolean).pop() || outputPath;
}

function modeLabel(mode) {
  if (mode === "pyjianyingdraft") return "剪映草稿";
  if (mode === "pyjianyingdraft_failed_fallback") return "草稿失败，已降级";
  return mode || "导出记录";
}
