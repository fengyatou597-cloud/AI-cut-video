import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { StatusBox } from "../components/Layout";

export function ProjectListPage() {
  const [projects, setProjects] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.listProjectOverview().then(setProjects).catch((err) => setError(err.message));
  }, []);

  const stats = useMemo(() => summarizeProjects(projects), [projects]);

  async function createDemoProject() {
    setError("");
    setMessage("正在创建示例项目...");
    try {
      const result = await api.createDemoProject();
      setMessage(result.message);
      navigate(result.next_href || `/projects/${result.project_id}/storyboard`);
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  return (
    <section>
      <div className="hero-card dashboard-hero">
        <div>
          <p className="eyebrow">Local-first rough cut</p>
          <h1>把 5-10 分钟视频，从文稿推进到剪映草稿。</h1>
          <p>先生成制作方案和 timeline，再交给剪映人工微调。我们不碰鼠标自动化这条危险小路。</p>
          <div className="hero-actions">
            <Link className="primary" to="/projects/new">创建新项目</Link>
            <button onClick={createDemoProject}>生成示例项目</button>
          </div>
        </div>
        <div className="dashboard-stats">
          <div><strong>{stats.total}</strong><span>项目</span></div>
          <div><strong>{stats.inProgress}</strong><span>进行中</span></div>
          <div><strong>{stats.exported}</strong><span>已导出</span></div>
        </div>
      </div>

      <StatusBox>{message}</StatusBox>
      <StatusBox type="error">{error}</StatusBox>

      <div className="project-workbench-head">
        <div>
          <p className="eyebrow">Project workbench</p>
          <h2>项目进度</h2>
        </div>
        <p className="muted">每张卡片都显示下一步。让项目自己告诉我们它卡在哪，挺省脑子的。</p>
      </div>

      <div className="project-workbench">
        {projects.map((project) => (
          <ProjectProgressCard project={project} key={project.id} />
        ))}
        {!projects.length && <p className="muted">还没有项目。创建一个，或者先生成示例项目试跑完整链路。</p>}
      </div>
    </section>
  );
}

function ProjectProgressCard({ project }) {
  const percent = Math.round((project.progress || 0) * 100);
  return (
    <article className="card project-progress-card">
      <div className="project-card-top">
        <div>
          <span className="pill">{project.platform}</span>
          <h3>{project.title}</h3>
          <p>{project.style} / {project.target_duration} / {project.pacing}</p>
        </div>
        <div className="progress-dial" style={{ "--progress": `${percent}%` }}>
          <strong>{percent}%</strong>
        </div>
      </div>

      <div className="step-strip">
        {(project.steps || []).map((step) => (
          <Link className={`step-dot ${step.done ? "done" : "todo"}`} key={step.key} to={step.href}>
            <span>{step.done ? "✓" : "·"}</span>
            <small>{step.label}</small>
          </Link>
        ))}
      </div>

      <div className="project-card-meta">
        <span>文稿 {project.script_count}</span>
        <span>素材 {project.asset_count}</span>
        <span>导出 {project.export_count}</span>
      </div>

      <Link className="primary next-step" to={project.next_step?.href || `/projects/${project.id}/script`}>
        下一步：{project.next_step?.label || "文稿"}
      </Link>
    </article>
  );
}

function summarizeProjects(projects) {
  return {
    total: projects.length,
    inProgress: projects.filter((project) => (project.progress || 0) > 0 && (project.progress || 0) < 1).length,
    exported: projects.filter((project) => project.export_count > 0).length,
  };
}
