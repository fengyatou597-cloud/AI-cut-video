import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { ProjectNav, StatusBox } from "../components/Layout";

const pacingOptions = ["steady", "medium", "fast"];
const assetTypes = ["video", "image", "placeholder"];
const defaultEffects = ["slow_zoom_in", "quick_cut", "soft_fade", "zoom_punch", "keyword_highlight", "none"];

export function StoryboardEditorPage() {
  const { projectId } = useParams();
  const [storyboard, setStoryboard] = useState(null);
  const [expandedShots, setExpandedShots] = useState({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.getStoryboard(projectId).then(setStoryboard).catch((err) => setError(err.message));
  }, [projectId]);

  const summary = useMemo(() => summarize(storyboard), [storyboard]);

  function updateSection(index, key, value) {
    setStoryboard((old) => {
      const copy = structuredClone(old);
      copy.sections[index][key] = value;
      return copy;
    });
  }

  function updateListField(index, key, value) {
    updateSection(index, key, parseList(value));
  }

  function addSection(afterIndex = null) {
    setStoryboard((old) => {
      const copy = structuredClone(old);
      const insertAt = afterIndex === null ? copy.sections.length : afterIndex + 1;
      const sectionId = `s${insertAt + 1}`;
      const section = createBlankSection(sectionId, copy.style);
      copy.sections.splice(insertAt, 0, section);
      return renumberStoryboard(copy);
    });
  }

  function duplicateSection(index) {
    setStoryboard((old) => {
      const copy = structuredClone(old);
      const duplicated = structuredClone(copy.sections[index]);
      duplicated.title = `${duplicated.title || "未命名段落"} 副本`;
      copy.sections.splice(index + 1, 0, duplicated);
      return renumberStoryboard(copy);
    });
  }

  function deleteSection(index) {
    setStoryboard((old) => {
      const copy = structuredClone(old);
      if (copy.sections.length <= 1) {
        setMessage("至少保留一个段落。可以清空内容，但别把地基拆光。")
        return copy;
      }
      copy.sections.splice(index, 1);
      return renumberStoryboard(copy);
    });
  }

  function estimateSection(index) {
    setStoryboard((old) => {
      const copy = structuredClone(old);
      const section = copy.sections[index];
      const duration = estimateDuration(section.narration || "");
      section.estimated_duration = duration;
      section.shots = createShots(section.id, duration, copy.style, section.pacing);
      return copy;
    });
  }

  function rebuildSectionShots(index) {
    setStoryboard((old) => {
      const copy = structuredClone(old);
      const section = copy.sections[index];
      section.shots = createShots(section.id, Number(section.estimated_duration || 12), copy.style, section.pacing);
      return copy;
    });
  }

  function rebuildAllDurationsAndShots() {
    setStoryboard((old) => {
      const copy = structuredClone(old);
      copy.sections = copy.sections.map((section) => {
        const duration = estimateDuration(section.narration || "");
        return {
          ...section,
          estimated_duration: duration,
          shots: createShots(section.id, duration, copy.style, section.pacing),
        };
      });
      return copy;
    });
    setMessage("已按旁白重新估算所有段落时长，并重建内部镜头。")
  }

  function updateShot(sectionIndex, shotIndex, key, value) {
    setStoryboard((old) => {
      const copy = structuredClone(old);
      copy.sections[sectionIndex].shots[shotIndex][key] = value;
      if (key === "duration") {
        copy.sections[sectionIndex].shots[shotIndex][key] = Math.max(0.5, Number(value || 0));
        copy.sections[sectionIndex].estimated_duration = sumShots(copy.sections[sectionIndex].shots);
        copy.sections[sectionIndex].shots = recalcShotStarts(copy.sections[sectionIndex].shots);
      }
      return copy;
    });
  }

  function addShot(sectionIndex) {
    setStoryboard((old) => {
      const copy = structuredClone(old);
      const section = copy.sections[sectionIndex];
      const shots = section.shots || [];
      shots.push({
        id: `${section.id}_shot_${String(shots.length + 1).padStart(2, "0")}`,
        start: sumShots(shots),
        duration: 5,
        visual_change: "新增镜头：补充一次画面变化或文字强调",
        suggested_asset_type: "video",
        effect: section.pacing === "fast" ? "quick_cut" : "slow_zoom_in",
      });
      section.shots = normalizeShots(section.id, shots);
      section.estimated_duration = sumShots(section.shots);
      return copy;
    });
  }

  function deleteShot(sectionIndex, shotIndex) {
    setStoryboard((old) => {
      const copy = structuredClone(old);
      const section = copy.sections[sectionIndex];
      section.shots = normalizeShots(section.id, (section.shots || []).filter((_, index) => index !== shotIndex));
      if (!section.shots.length) section.shots = createShots(section.id, 5, copy.style, section.pacing);
      section.estimated_duration = sumShots(section.shots);
      return copy;
    });
  }

  function toggleShots(sectionId) {
    setExpandedShots((old) => ({ ...old, [sectionId]: !old[sectionId] }));
  }

  async function save() {
    setError("");
    setMessage("保存中...");
    try {
      const normalized = renumberStoryboard(storyboard);
      const result = await api.updateStoryboard(projectId, normalized);
      setStoryboard(result);
      setMessage("分镜表已保存。下一次生成 timeline 会使用这些段落和 shots。")
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  return (
    <section>
      <ProjectNav />
      <p className="eyebrow">Step 4</p>
      <h1>分镜表编辑</h1>
      <StatusBox>{message}</StatusBox>
      <StatusBox type="error">{error}</StatusBox>
      {!storyboard ? <p className="muted">请先在文稿页生成 storyboard。</p> : (
        <>
          <div className="storyboard-summary">
            <div><strong>{summary.sections}</strong><span>段落</span></div>
            <div><strong>{summary.shots}</strong><span>镜头</span></div>
            <div><strong>{formatDuration(summary.duration)}</strong><span>估算总时长</span></div>
            <div><strong>{storyboard.style}</strong><span>风格模板</span></div>
          </div>
          <div className="toolbar sticky-toolbar">
            <button className="primary" onClick={save}>保存分镜表</button>
            <button onClick={() => addSection()}>新增段落</button>
            <button onClick={rebuildAllDurationsAndShots}>全部重新估时并重建镜头</button>
          </div>
          <div className="storyboard-list">
            {storyboard.sections.map((section, index) => (
              <article className="story-card" key={section.id}>
                <div className="story-head expanded">
                  <span>{section.id}</span>
                  <input value={section.title || ""} onChange={(e) => updateSection(index, "title", e.target.value)} />
                  <div className="story-actions">
                    <button onClick={() => addSection(index)}>下方新增</button>
                    <button onClick={() => duplicateSection(index)}>复制</button>
                    <button className="danger" onClick={() => deleteSection(index)}>删除</button>
                  </div>
                </div>

                <label>旁白<textarea value={section.narration || ""} onChange={(e) => updateSection(index, "narration", e.target.value)} /></label>
                <div className="mini-grid three">
                  <label>估算时长<input type="number" min="1" value={section.estimated_duration || 0} onChange={(e) => updateSection(index, "estimated_duration", Number(e.target.value))} /></label>
                  <label>节奏<select value={section.pacing || "medium"} onChange={(e) => updateSection(index, "pacing", e.target.value)}>{pacingOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                  <label>情绪/节奏<input value={section.emotion || ""} onChange={(e) => updateSection(index, "emotion", e.target.value)} /></label>
                </div>
                <label>段落目的<input value={section.purpose || ""} onChange={(e) => updateSection(index, "purpose", e.target.value)} /></label>
                <label>核心信息<input value={section.core_message || ""} onChange={(e) => updateSection(index, "core_message", e.target.value)} /></label>
                <label>画面建议<textarea value={section.visual_plan || ""} onChange={(e) => updateSection(index, "visual_plan", e.target.value)} /></label>
                <div className="mini-grid">
                  <label>所需素材<input value={(section.required_assets || []).join("、")} onChange={(e) => updateListField(index, "required_assets", e.target.value)} /></label>
                  <label>缺失素材<input value={(section.missing_assets || []).join("、")} onChange={(e) => updateListField(index, "missing_assets", e.target.value)} /></label>
                </div>
                <div className="mini-grid">
                  <label>字幕重点词<input value={(section.subtitle_keywords || []).join("、")} onChange={(e) => updateListField(index, "subtitle_keywords", e.target.value)} /></label>
                  <label>花字建议<input value={(section.text_overlays || []).join("、")} onChange={(e) => updateListField(index, "text_overlays", e.target.value)} /></label>
                </div>
                <div className="mini-grid">
                  <label>动效<input value={(section.effects || []).join("、")} onChange={(e) => updateListField(index, "effects", e.target.value)} /></label>
                  <label>转场<input value={section.transition || ""} onChange={(e) => updateSection(index, "transition", e.target.value)} /></label>
                </div>

                <div className="shot-toolbar">
                  <button onClick={() => estimateSection(index)}>按旁白估时并重建本段镜头</button>
                  <button onClick={() => rebuildSectionShots(index)}>按当前时长重建镜头</button>
                  <button onClick={() => addShot(index)}>新增镜头</button>
                  <button onClick={() => toggleShots(section.id)}>{expandedShots[section.id] ? "收起 shots" : `展开 shots (${section.shots?.length || 0})`}</button>
                </div>

                {expandedShots[section.id] && (
                  <div className="shots-list">
                    {(section.shots || []).map((shot, shotIndex) => (
                      <div className="shot-row" key={shot.id || shotIndex}>
                        <span>{shot.id}</span>
                        <label>开始<input type="number" min="0" step="0.5" value={shot.start || 0} onChange={(e) => updateShot(index, shotIndex, "start", Number(e.target.value))} /></label>
                        <label>时长<input type="number" min="0.5" step="0.5" value={shot.duration || 1} onChange={(e) => updateShot(index, shotIndex, "duration", Number(e.target.value))} /></label>
                        <label>素材类型<select value={shot.suggested_asset_type || "video"} onChange={(e) => updateShot(index, shotIndex, "suggested_asset_type", e.target.value)}>{assetTypes.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                        <label>动效<select value={shot.effect || "none"} onChange={(e) => updateShot(index, shotIndex, "effect", e.target.value)}>{defaultEffects.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                        <label className="shot-note">画面变化<input value={shot.visual_change || ""} onChange={(e) => updateShot(index, shotIndex, "visual_change", e.target.value)} /></label>
                        <button className="danger" onClick={() => deleteShot(index, shotIndex)}>删镜头</button>
                      </div>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function summarize(storyboard) {
  if (!storyboard) return { sections: 0, shots: 0, duration: 0 };
  return storyboard.sections.reduce(
    (total, section) => ({
      sections: total.sections + 1,
      shots: total.shots + (section.shots?.length || 0),
      duration: total.duration + Number(section.estimated_duration || 0),
    }),
    { sections: 0, shots: 0, duration: 0 }
  );
}

function createBlankSection(sectionId, style) {
  const duration = 20;
  return {
    id: sectionId,
    title: "新增段落",
    narration: "",
    estimated_duration: duration,
    purpose: "补充新的论点或转折",
    core_message: "",
    emotion: "medium",
    visual_plan: "这里写这一段需要什么画面、素材如何切换。",
    required_assets: ["主视觉素材"],
    missing_assets: [],
    subtitle_keywords: [],
    text_overlays: [],
    effects: [style === "B站知识型" ? "quick_cut" : "slow_zoom_in"],
    transition: "自然切",
    pacing: "medium",
    shots: createShots(sectionId, duration, style, "medium"),
  };
}

function estimateDuration(text) {
  const duration = Math.round((text || "").trim().length / 4.2);
  return Math.max(12, Math.min(45, duration || 12));
}

function createShots(sectionId, duration, style, pacing = "medium") {
  const shotLength = pacing === "fast" || ["B站知识型", "小红书口播型"].includes(style) ? 5 : 7;
  const shots = [];
  let start = 0;
  let index = 1;
  while (start < duration) {
    const shotDuration = Math.min(shotLength, duration - start);
    shots.push({
      id: `${sectionId}_shot_${String(index).padStart(2, "0")}`,
      start,
      duration: shotDuration,
      visual_change: "切换素材或增加文字/标注",
      suggested_asset_type: index % 2 ? "video" : "image",
      effect: ["情绪共鸣型", "社科解释型"].includes(style) ? "slow_zoom_in" : "quick_cut",
    });
    start += shotDuration;
    index += 1;
  }
  return shots;
}

function renumberStoryboard(storyboard) {
  const copy = structuredClone(storyboard);
  copy.sections = copy.sections.map((section, index) => {
    const id = `s${String(index + 1).padStart(3, "0")}`;
    return { ...section, id, shots: normalizeShots(id, section.shots || []) };
  });
  return copy;
}

function normalizeShots(sectionId, shots) {
  return recalcShotStarts(shots).map((shot, index) => ({
    ...shot,
    id: `${sectionId}_shot_${String(index + 1).padStart(2, "0")}`,
    duration: Math.max(0.5, Number(shot.duration || 1)),
    start: Number(shot.start || 0),
  }));
}

function recalcShotStarts(shots) {
  let cursor = 0;
  return shots.map((shot) => {
    const next = { ...shot, start: Number(cursor.toFixed(3)) };
    cursor += Number(shot.duration || 0);
    return next;
  });
}

function sumShots(shots = []) {
  return Number(shots.reduce((sum, shot) => sum + Number(shot.duration || 0), 0).toFixed(3));
}

function parseList(value) {
  return value.split(/[、,，\n]/).map((item) => item.trim()).filter(Boolean);
}

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${String(secs).padStart(2, "0")}`;
}
