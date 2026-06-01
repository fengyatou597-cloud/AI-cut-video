import { NavLink, useParams } from "react-router-dom";

export function Layout({ children }) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">RC</span>
          <div>
            <strong>AI 粗剪助手</strong>
            <small>本地剪映草稿 MVP</small>
          </div>
        </div>
        <nav>
          <NavLink to="/">项目列表</NavLink>
          <NavLink to="/projects/new">创建项目</NavLink>
          <NavLink to="/settings">本地设置</NavLink>
        </nav>
        <p className="sidebar-note">先把流程跑通，再让 AI 变聪明。这个 MVP 不自动操作剪映。</p>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}

export function ProjectNav() {
  const { projectId } = useParams();
  if (!projectId) return null;
  const base = `/projects/${projectId}`;
  return (
    <div className="project-nav">
      <NavLink to={`${base}/overview`}>总览</NavLink>
      <NavLink to={`${base}/script`}>文稿</NavLink>
      <NavLink to={`${base}/assets`}>素材库</NavLink>
      <NavLink to={`${base}/storyboard`}>分镜表</NavLink>
      <NavLink to={`${base}/timeline`}>Timeline</NavLink>
      <NavLink to={`${base}/adjust`}>AI 修改</NavLink>
      <NavLink to={`${base}/draft`}>剪映草稿</NavLink>
    </div>
  );
}

export function StatusBox({ type = "info", children }) {
  if (!children) return null;
  return <div className={`status ${type}`}>{children}</div>;
}

export function JsonPanel({ data }) {
  return <pre className="json-panel">{JSON.stringify(data, null, 2)}</pre>;
}
