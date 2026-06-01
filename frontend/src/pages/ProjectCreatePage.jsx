import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { StatusBox } from "../components/Layout";

const defaults = {
  title: "",
  platform: "B站",
  target_duration: "8分钟",
  style: "B站知识型",
  pacing: "中等",
  needs_hook: true,
  needs_broll: true,
  needs_research_visuals: false,
};

export function ProjectCreatePage() {
  const [form, setForm] = useState(defaults);
  const [templates, setTemplates] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.getTemplates().then(setTemplates).catch((err) => setError(err.message));
  }, []);

  function update(key, value) {
    setForm((old) => ({ ...old, [key]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const project = await api.createProject(form);
      navigate(`/projects/${project.id}/script`);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="narrow">
      <p className="eyebrow">Step 1</p>
      <h1>创建视频项目</h1>
      <StatusBox type="error">{error}</StatusBox>
      <form className="form-card" onSubmit={submit}>
        <label>视频标题<input value={form.title} onChange={(e) => update("title", e.target.value)} required /></label>
        <label>视频平台<select value={form.platform} onChange={(e) => update("platform", e.target.value)}>{(templates?.platforms || ["B站", "小红书", "抖音", "视频号", "其他"]).map((item) => <option key={item}>{item}</option>)}</select></label>
        <label>目标时长<select value={form.target_duration} onChange={(e) => update("target_duration", e.target.value)}>{(templates?.target_durations || ["5分钟", "8分钟", "10分钟", "自定义"]).map((item) => <option key={item}>{item}</option>)}</select></label>
        <label>视频风格<select value={form.style} onChange={(e) => update("style", e.target.value)}>{Object.keys(templates?.style_templates || { "社科解释型": {}, "情绪共鸣型": {}, "B站知识型": {}, "小红书口播型": {} }).map((item) => <option key={item}>{item}</option>)}</select></label>
        <label>剪辑节奏<select value={form.pacing} onChange={(e) => update("pacing", e.target.value)}>{(templates?.pacing_options || ["稳重", "中等", "快节奏"]).map((item) => <option key={item}>{item}</option>)}</select></label>
        <div className="checks">
          <label><input type="checkbox" checked={form.needs_hook} onChange={(e) => update("needs_hook", e.target.checked)} /> 需要开头强钩子</label>
          <label><input type="checkbox" checked={form.needs_broll} onChange={(e) => update("needs_broll", e.target.checked)} /> 需要影视片段或生活化 B-roll</label>
          <label><input type="checkbox" checked={form.needs_research_visuals} onChange={(e) => update("needs_research_visuals", e.target.checked)} /> 需要论文/新闻/数据图表</label>
        </div>
        <button className="primary" type="submit">创建并上传文稿</button>
      </form>
    </section>
  );
}
