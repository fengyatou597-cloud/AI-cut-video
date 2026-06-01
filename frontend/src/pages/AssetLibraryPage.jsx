import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, apiBase } from "../api/client";
import { ProjectNav, StatusBox } from "../components/Layout";

export function AssetLibraryPage() {
  const { projectId } = useParams();
  const [assets, setAssets] = useState([]);
  const [file, setFile] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const result = await api.listAssets(projectId);
    setAssets(result);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, [projectId]);

  async function upload() {
    if (!file) return;
    setMessage("上传并分析素材中，如果是视频会尝试抽关键帧...");
    setError("");
    try {
      await api.uploadAsset(projectId, file);
      setFile(null);
      await refresh();
      setMessage("素材已加入素材库。");
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  async function uploadAudio() {
    if (!audioFile) return;
    setMessage("上传旁白/音频中...");
    setError("");
    try {
      await api.uploadAsset(projectId, audioFile);
      setAudioFile(null);
      await refresh();
      setMessage("音频已加入素材库。第一个音频会作为旁白轨，第二个音频会作为背景音乐占位。");
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  async function analyze(assetId) {
    setMessage("AI 正在识别素材...");
    setError("");
    try {
      await api.analyzeAsset(projectId, assetId);
      await refresh();
      setMessage("素材 AI 标签已更新。");
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  async function analyzeAll() {
    setMessage("AI 正在批量识别素材，这一步会调用你配置的 API...");
    setError("");
    try {
      const result = await api.analyzeAllAssets(projectId);
      setAssets(result.assets || []);
      setMessage(`批量识别完成：成功 ${result.updated} 个，失败 ${result.failed} 个。识别后请重新生成 Timeline。`);
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  async function deleteAsset(asset) {
    const confirmed = window.confirm(`确定删除这个素材吗？\n\n${asset.filename}\n\n删除后需要重新生成 Timeline 和剪映草稿。`);
    if (!confirmed) return;
    setMessage("正在删除素材...");
    setError("");
    try {
      await api.deleteAsset(projectId, asset.id);
      await refresh();
      setMessage("素材已删除，旧 Timeline 已清空。请重新生成 Timeline 后再导出剪映草稿。");
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  return (
    <section>
      <ProjectNav />
      <p className="eyebrow">Step 3</p>
      <h1>素材库</h1>
      <div className="card workflow-note">
        <h3>素材上传建议</h3>
        <p>把你录好的旁白音频也上传到这里。第一个音频素材会作为主旁白轨，第二个音频素材会作为低音量背景音乐占位。视频和图片识别后，Timeline 会优先根据 AI 标签匹配分镜镜头。</p>
        <button onClick={analyzeAll} disabled={!assets.length}>一键 AI 识别全部素材</button>
      </div>
      <StatusBox>{message}</StatusBox>
      <StatusBox type="error">{error}</StatusBox>
      <div className="asset-upload-grid">
        <div className="form-card">
          <h3>上传画面素材</h3>
          <p className="muted">视频、图片、B-roll、截图都放这里。</p>
          <input type="file" accept="video/*,image/*,.mov,.mp4,.png,.jpg,.jpeg,.webp" onChange={(e) => setFile(e.target.files?.[0])} />
          <button className="primary" disabled={!file} onClick={upload}>上传视频 / 图片</button>
        </div>
        <div className="form-card audio-upload-card">
          <h3>上传旁白/音频</h3>
          <p className="muted">你录好的旁白音频放这里。第一个音频会进入剪映主音频轨。</p>
          <input type="file" accept="audio/*,.mp3,.wav,.m4a,.aac" onChange={(e) => setAudioFile(e.target.files?.[0])} />
          <button className="primary" disabled={!audioFile} onClick={uploadAudio}>上传旁白 / 音频</button>
        </div>
      </div>
      <div className="grid assets-grid">
        {assets.map((asset) => (
          <article className="card asset-card" key={asset.id}>
            {asset.thumbnail_path ? <img src={`${apiBase}${asset.thumbnail_path}`} alt={asset.filename} /> : <div className="asset-placeholder">{asset.asset_type}</div>}
            <h3>{asset.filename}</h3>
            <p>{asset.asset_type} {asset.duration ? ` / ${asset.duration}s` : ""}</p>
            <p>{asset.width && asset.height ? `${asset.width} x ${asset.height}` : "等待 ffprobe 元信息"}</p>
            {asset.ai_tags?.summary && <p className="asset-ai-summary">{asset.ai_tags.summary}</p>}
            {!!asset.ai_tags?.tags?.length && (
              <div className="tag-strip">{asset.ai_tags.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
            )}
            <div className="asset-actions">
              <button onClick={() => analyze(asset.id)}>AI 识别素材</button>
              <button className="danger-button" onClick={() => deleteAsset(asset)}>删除素材</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
