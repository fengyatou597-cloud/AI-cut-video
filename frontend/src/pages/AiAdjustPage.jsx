import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { JsonPanel, ProjectNav, StatusBox } from "../components/Layout";

const examples = [
  "只检查 SRT 字幕错字、口癖和标点，保持原时间轴不变，不要改画面。",
  "改成竖屏 9:16，画面保持克制，只做必要裁切和少量标题花字。",
  "画面有点单调，做克制增强：慢推、轻微横移、干净叠化，不要闪白抖动。",
  "整体更像 B 站知识型，但不要堆特效，只加少量关键词强调。",
];

export function AiAdjustPage() {
  const { projectId } = useParams();
  const [instruction, setInstruction] = useState("");
  const [result, setResult] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [showJson, setShowJson] = useState(false);

  async function apply() {
    if (!instruction.trim()) {
      setError("先写一句你想让 AI 修改什么。");
      return;
    }
    setMessage("AI 正在按克制审美修改当前工程...");
    setError("");
    setResult(null);
    try {
      const response = await api.applyAiAdjustment(projectId, instruction);
      setResult(response);
      setMessage("修改已应用。建议先去 Timeline 预览检查，再去剪映草稿页更新同名草稿。");
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  return (
    <section>
      <ProjectNav />
      <p className="eyebrow">AI Edit</p>
      <h1>AI 修改要求</h1>

      <div className="card ai-edit-hero">
        <h3>这次改得更克制</h3>
        <p>这里不是让 AI 乱炫技，而是让它像剪辑助理一样按你的要求修当前工程。默认会少加特效、少加花字，优先保证清楚、稳定、可继续人工微调。</p>
      </div>

      <StatusBox>{message}</StatusBox>
      <StatusBox type="error">{error}</StatusBox>

      <div className="ai-edit-layout">
        <div className="form-card">
          <label>
            写下你希望 AI 修改什么
            <textarea
              className="ai-edit-textarea"
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
              placeholder="例如：只检查字幕错字，别改画面；或者：画面有点单调，帮我做克制增强，慢推和干净叠化即可，不要乱加闪白和抖动。"
            />
          </label>
          <div className="toolbar">
            <button className="primary" onClick={apply}>应用 AI 修改</button>
            <Link className="ghost" to={`/projects/${projectId}/timeline`}>去 Timeline 检查</Link>
            <Link className="ghost" to={`/projects/${projectId}/draft`}>去更新剪映草稿</Link>
          </div>
        </div>

        <div className="card prompt-examples">
          <h3>更推荐这样提要求</h3>
          {examples.map((item) => (
            <button key={item} onClick={() => setInstruction(item)}>{item}</button>
          ))}
        </div>
      </div>

      {result && (
        <div className="card adjustment-result">
          <span className="pill">{result.source === "ai" ? "真实 AI 已修改" : "本地规则已修改"}</span>
          <h3>本次改动</h3>
          <ul>
            {(result.summary || []).map((item) => <li key={item}>{item}</li>)}
          </ul>
          {!!result.notes?.length && <p className="muted">{result.notes.join(" ")}</p>}
          <button onClick={() => setShowJson((old) => !old)}>{showJson ? "隐藏结果 JSON" : "查看结果 JSON"}</button>
          {showJson && <JsonPanel data={result} />}
        </div>
      )}
    </section>
  );
}
