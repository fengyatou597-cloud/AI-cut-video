import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ProjectNav, StatusBox } from "../components/Layout";

const stepHelp = {
  script: "上传文稿和 SRT。文稿负责理解内容，SRT 负责精确字幕时间轴。",
  storyboard: "把文稿拆成开头、主体、转折、总结和每段镜头建议。",
  assets: "上传视频、图片、旁白录音、音乐等素材。第一个音频会作为主旁白轨。",
  timeline: "把分镜、素材、录音、SRT 拼成粗剪时间线，能看到每个轨道放了什么。",
  draft: "输出剪映草稿或下载 ZIP 粗剪包。",
};

export function ProjectOverviewPage() {
  const { projectId } = useParams();
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getProjectOverview(projectId).then(setOverview).catch((err) => setError(err.message));
  }, [projectId]);

  if (error) return <StatusBox type="error">{error}</StatusBox>;
  if (!overview) return <p className="muted">正在加载项目总览...</p>;

  const percent = Math.round((overview.progress || 0) * 100);

  return (
    <section>
      <ProjectNav />
      <p className="eyebrow">Project map</p>
      <h1>{overview.title}</h1>

      <div className="project-map-hero card">
        <div>
          <span className="pill">这个网站到底做什么？</span>
          <h2>它不是自动成片工具，而是把你从“文稿和素材”推进到“剪映可继续编辑的粗剪结构”。</h2>
          <p>最终你会拿到分镜表、timeline、字幕文件、粗剪包 ZIP；如果剪映草稿目录配置成功，还会尝试生成剪映草稿。</p>
        </div>
        <div className="progress-dial large" style={{ "--progress": `${percent}%` }}><strong>{percent}%</strong></div>
      </div>

      <div className="truth-grid">
        <div className="card"><h3>现在可以完成</h3><p>拆文稿、做分镜、编辑 shots、上传素材、生成 timeline、下载粗剪包 ZIP、尝试剪映草稿。</p></div>
        <div className="card"><h3>现在不能完成</h3><p>不会自动找素材、不会自动精剪、不会自动导出成片，也不能保证每个剪映版本都能直接打开草稿。</p></div>
        <div className="card"><h3>你最终要做什么</h3><p>把粗剪包或剪映草稿带进剪映，人工微调画面、节奏、字幕和音乐，然后导出成片。</p></div>
      </div>

      <div className="workflow-roadmap">
        {(overview.steps || []).map((step, index) => (
          <Link className={`workflow-step ${step.done ? "done" : "todo"}`} key={step.key} to={step.href}>
            <span>{index + 1}</span>
            <div>
              <strong>{step.label}</strong>
              <p>{stepHelp[step.key]}</p>
            </div>
            <em>{step.done ? "已完成" : "待处理"}</em>
          </Link>
        ))}
      </div>

      <div className="toolbar next-action-bar">
        <Link className="primary" to={overview.next_step?.href || `/projects/${projectId}/script`}>去下一步：{overview.next_step?.label}</Link>
        <Link to={`/projects/${projectId}/draft`}>直接看导出</Link>
      </div>
    </section>
  );
}
