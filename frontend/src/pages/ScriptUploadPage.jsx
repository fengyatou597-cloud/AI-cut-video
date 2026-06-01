import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ProjectNav, StatusBox } from "../components/Layout";

export function ScriptUploadPage() {
  const { projectId } = useParams();
  const [file, setFile] = useState(null);
  const [subtitleFile, setSubtitleFile] = useState(null);
  const [script, setScript] = useState(null);
  const [subtitles, setSubtitles] = useState(null);
  const [storyboard, setStoryboard] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.getLatestScript(projectId).then(setScript).catch(() => null);
    api.getLatestSubtitles(projectId).then(setSubtitles).catch(() => null);
  }, [projectId]);

  async function upload() {
    if (!file) return;
    setError("");
    setMessage("上传中...");
    try {
      const result = await api.uploadScript(projectId, file);
      setScript(result);
      setMessage("文稿已上传，可以生成 mock 分镜表了。");
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  async function uploadSubtitles() {
    if (!subtitleFile) return;
    setError("");
    setMessage("上传 SRT 字幕中...");
    try {
      const result = await api.uploadSubtitles(projectId, subtitleFile);
      setSubtitles(result);
      setSubtitleFile(null);
      setMessage(`SRT 已上传：${result.cue_count} 条字幕，约 ${formatDuration(result.duration || 0)}。生成 timeline 时会优先使用它。`);
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  async function generateStoryboard() {
    setError("");
    setMessage("生成分镜中...");
    try {
      const result = await api.generateStoryboard(projectId);
      setStoryboard(result);
      setMessage("分镜表已生成。建议去分镜表页人工微调。")
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  return (
    <section>
      <ProjectNav />
      <p className="eyebrow">Step 2</p>
      <h1>上传文稿</h1>
      <div className="card workflow-note">
        <h3>推荐真实工作流</h3>
        <p>文稿支持 txt / md / docx，用于理解内容和生成分镜；你提前录好的旁白音频请在“素材库”上传；你从录音生成的 SRT 字幕在这里上传。后续 timeline 会优先按 SRT 的时间轴做字幕和粗剪节奏。</p>
      </div>
      <StatusBox>{message}</StatusBox>
      <StatusBox type="error">{error}</StatusBox>
      <div className="two-col">
        <div className="form-card">
          <label>选择 txt / md / docx 文稿<input type="file" accept=".txt,.md,.docx" onChange={(e) => setFile(e.target.files?.[0])} /></label>
          <button className="primary" onClick={upload} disabled={!file}>上传文稿</button>
          <hr />
          <label>选择 SRT 字幕<input type="file" accept=".srt" onChange={(e) => setSubtitleFile(e.target.files?.[0])} /></label>
          <button onClick={uploadSubtitles} disabled={!subtitleFile}>上传 SRT 字幕</button>
          <button onClick={generateStoryboard} disabled={!script}>生成 storyboard mock</button>
          <Link className="ghost" to={`/projects/${projectId}/storyboard`}>查看/编辑分镜表</Link>
        </div>
        <div className="card">
          <h3>当前文稿</h3>
          {script ? <pre className="script-preview">{script.content.slice(0, 1800)}</pre> : <p className="muted">还没有上传文稿。</p>}
          <div className="subtitle-status">
            <h3>当前 SRT 字幕</h3>
            {subtitles ? (
              <p>{subtitles.filename} / {subtitles.cue_count} 条 / 约 {formatDuration(subtitles.duration || 0)}</p>
            ) : (
              <p className="muted">还没有上传 SRT。未上传时会用文稿粗略切字幕。</p>
            )}
          </div>
        </div>
      </div>
      {storyboard && <div className="card"><h3>生成概览</h3><p>{storyboard.sections?.length || 0} 个段落，已包含内部镜头拆分。</p></div>}
    </section>
  );
}

function formatDuration(seconds) {
  const total = Math.round(Number(seconds || 0));
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${String(secs).padStart(2, "0")}`;
}
