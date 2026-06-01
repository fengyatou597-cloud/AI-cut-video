import { useEffect, useState } from "react";
import { api } from "../api/client";
import { StatusBox } from "../components/Layout";

export function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [candidates, setCandidates] = useState(null);
  const [draftsDir, setDraftsDir] = useState("");
  const [fallbackExportDir, setFallbackExportDir] = useState("D:\\AI视频粗剪输出");
  const [aiEnabled, setAiEnabled] = useState(false);
  const [aiBaseUrl, setAiBaseUrl] = useState("");
  const [aiApiKey, setAiApiKey] = useState("");
  const [aiTextBaseUrl, setAiTextBaseUrl] = useState("");
  const [aiTextApiKey, setAiTextApiKey] = useState("");
  const [aiTextModel, setAiTextModel] = useState("");
  const [aiVisionBaseUrl, setAiVisionBaseUrl] = useState("");
  const [aiVisionApiKey, setAiVisionApiKey] = useState("");
  const [aiVisionModel, setAiVisionModel] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    loadSettings();
    scanCandidates(false);
  }, []);

  async function loadSettings() {
    try {
      const data = await api.getSettings();
      setSettings(data);
      setDraftsDir(data.jianying_drafts_dir || data.effective_jianying_drafts_dir || "");
      setFallbackExportDir(data.fallback_export_dir || data.effective_fallback_export_dir || "D:\\AI视频粗剪输出");
      setAiEnabled(Boolean(data.ai_enabled));
      setAiBaseUrl(data.ai_base_url || "");
      setAiTextBaseUrl(data.ai_text_base_url || "");
      setAiTextModel(data.ai_text_model || "");
      setAiVisionBaseUrl(data.ai_vision_base_url || "");
      setAiVisionModel(data.ai_vision_model || "");
    } catch (err) {
      setError(err.message);
    }
  }

  async function scanCandidates(showMessage = true) {
    setError("");
    if (showMessage) setMessage("正在扫描常见剪映草稿目录...");
    try {
      const result = await api.getDraftDirCandidates();
      setCandidates(result);
      if (showMessage) {
        setMessage(result.recommended ? "已找到可用候选路径，可以一键套用。" : "没有找到可用候选路径。请先打开剪映创建一个空草稿，再重新扫描。")
      }
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  async function save(nextDraftsDir = draftsDir, nextFallbackExportDir = fallbackExportDir) {
    setError("");
    setMessage("保存设置中...");
    try {
      const result = await api.updateSettings({
        jianying_drafts_dir: nextDraftsDir,
        fallback_export_dir: nextFallbackExportDir,
        ai_enabled: aiEnabled,
        ai_provider: "openai_compatible",
        ai_base_url: aiBaseUrl,
        ai_api_key: aiApiKey,
        ai_text_base_url: aiTextBaseUrl,
        ai_text_api_key: aiTextApiKey,
        ai_text_model: aiTextModel,
        ai_vision_base_url: aiVisionBaseUrl,
        ai_vision_api_key: aiVisionApiKey,
        ai_vision_model: aiVisionModel,
      });
      setSettings(result);
      setDraftsDir(result.jianying_drafts_dir || result.effective_jianying_drafts_dir || "");
      setFallbackExportDir(result.fallback_export_dir || result.effective_fallback_export_dir || "D:\\AI视频粗剪输出");
      setAiApiKey("");
      setAiTextApiKey("");
      setAiVisionApiKey("");
      setMessage("设置已保存。粗剪包会保存到你设置的输出目录；剪映草稿页也会使用新的路径状态。")
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  function useCandidate(path) {
    setDraftsDir(path);
    save(path, fallbackExportDir);
  }

  function useDDriveOutput() {
    const path = "D:\\AI视频粗剪输出";
    setFallbackExportDir(path);
    save(draftsDir, path);
  }

  return (
    <section className="narrow">
      <p className="eyebrow">Local settings</p>
      <h1>本地设置</h1>
      <StatusBox>{message}</StatusBox>
      <StatusBox type="error">{error}</StatusBox>

      <div className="form-card settings-card">
        <h3>AI API 设置</h3>
        <label className="switch-row">
          <input type="checkbox" checked={aiEnabled} onChange={(event) => setAiEnabled(event.target.checked)} />
          启用真实 AI 生成分镜和素材识别
        </label>
        <div className="settings-subcard">
          <h3>通用 API 配置</h3>
          <p className="muted">如果文本模型和视觉模型来自同一个平台，只填这里即可；下面两个专用配置可以留空。</p>
          <label>
            通用 API Base URL
            <input
              value={aiBaseUrl}
              onChange={(event) => setAiBaseUrl(event.target.value)}
              placeholder="例如：https://api.deepseek.com 或 https://dashscope.aliyuncs.com/compatible-mode"
            />
          </label>
          <label>
            通用 API Key
            <input
              value={aiApiKey}
              type="password"
              onChange={(event) => setAiApiKey(event.target.value)}
              placeholder={settings?.ai_api_key_configured ? "已配置；留空则保持原 key" : "填你的本地 API key，不会回显"}
            />
          </label>
        </div>

        <div className="settings-subcard">
          <h3>文本模型配置</h3>
          <p className="muted">用于理解文稿、生成 storyboard。留空时使用通用 API Base URL 和通用 Key。</p>
          <label>
          文本 API Base URL
          <input
            value={aiTextBaseUrl}
            onChange={(event) => setAiTextBaseUrl(event.target.value)}
            placeholder="可选：文本模型平台地址；留空则用通用 Base URL"
          />
        </label>
        <label>
          文本 API Key
          <input
            value={aiTextApiKey}
            type="password"
            onChange={(event) => setAiTextApiKey(event.target.value)}
            placeholder={settings?.ai_text_api_key_configured ? "已配置；留空则保持原 key" : "可选：文本专用 key"}
          />
        </label>
        <label>
          文本模型
          <input
            value={aiTextModel}
            onChange={(event) => setAiTextModel(event.target.value)}
            placeholder="例如：deepseek-chat / qwen-plus / glm-4"
          />
        </label>
        </div>

        <div className="settings-subcard">
          <h3>视觉模型配置</h3>
          <p className="muted">用于识别图片、视频关键帧和素材标签。留空时使用通用 API Base URL 和通用 Key。</p>
          <label>
          视觉 API Base URL
          <input
            value={aiVisionBaseUrl}
            onChange={(event) => setAiVisionBaseUrl(event.target.value)}
            placeholder="可选：视觉模型平台地址；留空则用通用 Base URL"
          />
        </label>
        <label>
          视觉 API Key
          <input
            value={aiVisionApiKey}
            type="password"
            onChange={(event) => setAiVisionApiKey(event.target.value)}
            placeholder={settings?.ai_vision_api_key_configured ? "已配置；留空则保持原 key" : "可选：视觉专用 key"}
          />
        </label>
        <label>
          视觉模型
          <input
            value={aiVisionModel}
            onChange={(event) => setAiVisionModel(event.target.value)}
            placeholder="例如：qwen-vl-plus / glm-4v-plus；没有就先留空"
          />
        </label>
        </div>
        <p className="muted">
          这里按 OpenAI-compatible 的 /chat/completions 调用。Key 只保存在本机 storage/app_settings.json，页面不会回显完整 key。专用配置优先级高于通用配置。
        </p>
        <div className="toolbar">
          <button className="primary" onClick={() => save()}>保存 AI 设置</button>
        </div>
      </div>

      <div className="form-card settings-card">
        <label>
          粗剪包输出目录（可以放 D 盘）
          <input
            value={fallbackExportDir}
            onChange={(event) => setFallbackExportDir(event.target.value)}
            placeholder="例如：D:\\AI视频粗剪输出"
          />
        </label>
        <p className="muted">
          这里控制 fallback 粗剪包保存位置，包括 storyboard.json、timeline.json、subtitles.srt 和说明文件。你想保存到 D 盘，就填 D 盘路径。
        </p>
        <div className="toolbar">
          <button className="primary" onClick={() => save()}>保存全部设置</button>
          <button onClick={useDDriveOutput}>使用 D:\AI_RoughCut_Output</button>
        </div>
      </div>

      <div className="form-card settings-card">
        <label>
          剪映草稿目录（必须是剪映识别的目录）
          <input
            value={draftsDir}
            onChange={(event) => setDraftsDir(event.target.value)}
            placeholder="例如：C:\\Users\\你的用户名\\AppData\\Local\\JianyingPro\\User Data\\Projects\\com.lveditor.draft"
          />
        </label>
        <p className="muted">
          这个路径不是普通保存路径，而是剪映自己的草稿目录。只有填对它，剪映才可能直接看到生成的草稿。也可以点击“扫描候选路径”。
        </p>
        <div className="toolbar">
          <button onClick={() => scanCandidates(true)}>扫描候选路径</button>
        </div>
      </div>

      {candidates && (
        <div className="card settings-info">
          <h3>候选剪映草稿目录</h3>
          {candidates.recommended ? (
            <div className="recommended-path">
              <span className="pill">推荐</span>
              <strong>{candidates.recommended.path}</strong>
              <button className="primary" onClick={() => useCandidate(candidates.recommended.path)}>使用这个路径</button>
            </div>
          ) : (
            <p className="muted">暂时没有找到存在的候选目录。建议先打开剪映，创建一个空草稿，然后重新扫描。</p>
          )}
          <div className="candidate-list">
            {(candidates.candidates || []).map((item) => (
              <div className={`candidate-item ${item.exists ? "exists" : "missing"}`} key={item.path}>
                <div>
                  <strong>{item.exists ? "存在" : "未找到"}</strong>
                  <span>{item.path}</span>
                </div>
                <button disabled={!item.exists} onClick={() => useCandidate(item.path)}>使用</button>
              </div>
            ))}
          </div>
          {!!candidates.tips?.length && <p className="muted">{candidates.tips.join(" ")}</p>}
        </div>
      )}

      {settings && (
        <div className="card settings-info">
          <h3>当前有效配置</h3>
          <dl>
            <div><dt>粗剪包输出目录</dt><dd>{settings.effective_fallback_export_dir || "未配置"}</dd></div>
            <div><dt>剪映草稿目录</dt><dd>{settings.effective_jianying_drafts_dir || "未配置"}</dd></div>
            <div><dt>本地数据目录</dt><dd>{settings.storage_dir}</dd></div>
            <div><dt>AI 状态</dt><dd>{settings.ai_enabled ? (settings.ai_text_api_key_configured ? "已启用，文本 key 可用" : "已启用，但 key 未配置") : "未启用"}</dd></div>
            <div><dt>通用 AI Base URL</dt><dd>{settings.ai_base_url || "未配置"}</dd></div>
            <div><dt>文本 Base URL</dt><dd>{settings.ai_text_base_url || "使用通用配置"}</dd></div>
            <div><dt>文本模型</dt><dd>{settings.effective_ai_text_model || "未配置"}</dd></div>
            <div><dt>视觉 Base URL</dt><dd>{settings.ai_vision_base_url || "使用通用配置"}</dd></div>
            <div><dt>视觉模型</dt><dd>{settings.effective_ai_vision_model || "未配置"}</dd></div>
          </dl>
        </div>
      )}

      <div className="card">
        <h3>D 盘和剪映目录的区别</h3>
        <p className="muted">粗剪包输出目录可以随便放 D 盘。剪映草稿目录必须是剪映自己的草稿目录，如果剪映本身还在 C 盘，那这里大概率仍然是 C 盘路径。这是剪映的限制，不是本工具不让你选 D 盘。</p>
      </div>
    </section>
  );
}

