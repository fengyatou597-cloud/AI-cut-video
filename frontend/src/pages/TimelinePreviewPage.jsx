import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { JsonPanel, ProjectNav, StatusBox } from "../components/Layout";

const trackMeta = {
  video: { label: "视频/图片", className: "track-video" },
  text: { label: "花字/标题", className: "track-text" },
  subtitle: { label: "字幕", className: "track-subtitle" },
  audio: { label: "音频", className: "track-audio" },
};

export function TimelinePreviewPage() {
  const { projectId } = useParams();
  const [timeline, setTimeline] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [showJson, setShowJson] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.getTimeline(projectId).then((data) => {
      setTimeline(data);
      setSelectedItem(firstTimelineItem(data));
    }).catch(() => null);
  }, [projectId]);

  const summary = useMemo(() => summarizeTimeline(timeline), [timeline]);

  async function generate() {
    setMessage("生成 timeline 中...");
    setError("");
    try {
      const result = await api.generateTimeline(projectId);
      setTimeline(result);
      setSelectedItem(firstTimelineItem(result));
      setMessage("timeline 已生成。现在可以检查轨道和素材匹配，再进入草稿导出页。")
    } catch (err) {
      setError(err.message);
      setMessage("");
    }
  }

  return (
    <section>
      <ProjectNav />
      <p className="eyebrow">Step 5</p>
      <h1>Timeline 预览</h1>
      <StatusBox>{message}</StatusBox>
      <StatusBox type="error">{error}</StatusBox>
      <div className="toolbar">
        <button className="primary" onClick={generate}>生成智能粗剪 Timeline</button>
        {timeline && <button onClick={() => setShowJson((old) => !old)}>{showJson ? "隐藏 JSON" : "查看 JSON"}</button>}
      </div>

      {timeline ? (
        <>
          <div className="timeline-summary">
            <div><strong>{formatDuration(summary.duration)}</strong><span>总时长</span></div>
            <div><strong>{summary.videoItems}</strong><span>视频镜头</span></div>
            <div><strong>{summary.textItems}</strong><span>花字</span></div>
            <div><strong>{summary.subtitleItems}</strong><span>字幕条</span></div>
            <div><strong>{summary.audioItems}</strong><span>音频轨</span></div>
          </div>
          {timeline.subtitle_source && (
            <div className="card timeline-source-card">
              <strong>字幕来源：{timeline.subtitle_source === "uploaded_srt" ? "已上传 SRT" : "文稿粗切"}</strong>
              <span>{timeline.edit_style?.cut_rule}</span>
            </div>
          )}

          <StatusBox type="warn">{timeline.warnings?.join(" ")}</StatusBox>

          <div className="timeline-workbench">
            <div className="timeline-ruler">
              {buildRuler(summary.duration).map((tick) => (
                <span key={tick} style={{ left: `${positionPercent(tick, summary.duration)}%` }}>{formatShortTime(tick)}</span>
              ))}
            </div>
            <div className="timeline-tracks">
              {(timeline.tracks || []).map((track) => (
                <TrackRow
                  key={track.type}
                  track={track}
                  duration={summary.duration}
                  selectedItem={selectedItem}
                  onSelect={setSelectedItem}
                />
              ))}
            </div>
          </div>

          <TimelineDetail item={selectedItem} />
          {showJson && <JsonPanel data={timeline} />}
        </>
      ) : (
        <p className="muted">还没有 timeline。先从分镜表和素材库生成一次，我们就能看到轨道预览。</p>
      )}
    </section>
  );
}

function TrackRow({ track, duration, selectedItem, onSelect }) {
  const meta = trackMeta[track.type] || { label: track.type, className: "track-generic" };
  const items = track.items || [];
  return (
    <div className="track-row-preview">
      <div className="track-label">
        <strong>{meta.label}</strong>
        <span>{items.length} items</span>
      </div>
      <div className={`track-lane ${meta.className}`}>
        {items.map((item, index) => {
          const selected = selectedItem?._key === itemKey(track.type, index);
          const left = positionPercent(Number(item.start || 0), duration);
          const width = Math.max(2.6, positionPercent(Number(item.duration || 1), duration));
          return (
            <button
              className={`timeline-clip ${selected ? "selected" : ""}`}
              key={itemKey(track.type, index)}
              style={{ left: `${left}%`, width: `${width}%` }}
              title={clipTitle(track.type, item)}
              onClick={() => onSelect({ ...item, _trackType: track.type, _key: itemKey(track.type, index) })}
            >
              <span>{clipPrimaryLabel(track.type, item)}</span>
              <small>{formatShortTime(item.start || 0)} / {Number(item.duration || 0).toFixed(1)}s</small>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function TimelineDetail({ item }) {
  if (!item) return <div className="card"><p className="muted">点击任意轨道片段查看详情。</p></div>;
  return (
    <article className="timeline-detail card">
      <div>
        <span className="pill">{trackMeta[item._trackType]?.label || item._trackType}</span>
        <h3>{clipPrimaryLabel(item._trackType, item)}</h3>
        <p>{item.note || item.text || "暂无备注"}</p>
      </div>
      <dl>
        <div><dt>开始</dt><dd>{formatShortTime(item.start || 0)}</dd></div>
        <div><dt>时长</dt><dd>{Number(item.duration || 0).toFixed(2)}s</dd></div>
        <div><dt>段落</dt><dd>{item.section_id || "-"}</dd></div>
        <div><dt>Shot</dt><dd>{item.shot_id || "-"}</dd></div>
        <div><dt>素材</dt><dd>{item.asset_name || item.asset_id || item.asset_type || "-"}</dd></div>
        <div><dt>取用位置</dt><dd>{item.source_start ? `${Number(item.source_start).toFixed(2)}s` : "0.00s"}</dd></div>
        <div><dt>效果/样式</dt><dd>{[item.effect || item.style, item.transition, item.animation, item.motion].filter(Boolean).join(" / ") || "-"}</dd></div>
        <div><dt>匹配原因</dt><dd>{item.match_reason || "-"}</dd></div>
      </dl>
    </article>
  );
}

function summarizeTimeline(timeline) {
  if (!timeline) return { duration: 0, videoItems: 0, textItems: 0, subtitleItems: 0, audioItems: 0, matchedAssets: 0 };
  const video = trackItems(timeline, "video");
  return {
    duration: Number(timeline.duration || maxEnd(timeline)),
    videoItems: video.length,
    textItems: trackItems(timeline, "text").length,
    subtitleItems: trackItems(timeline, "subtitle").length,
    audioItems: trackItems(timeline, "audio").length,
    matchedAssets: video.filter((item) => item.asset_id).length,
  };
}

function trackItems(timeline, type) {
  return timeline?.tracks?.find((track) => track.type === type)?.items || [];
}

function maxEnd(timeline) {
  return Math.max(0, ...(timeline.tracks || []).flatMap((track) => (track.items || []).map((item) => Number(item.start || 0) + Number(item.duration || 0))));
}

function firstTimelineItem(timeline) {
  const firstTrack = timeline?.tracks?.find((track) => track.items?.length);
  if (!firstTrack) return null;
  return { ...firstTrack.items[0], _trackType: firstTrack.type, _key: itemKey(firstTrack.type, 0) };
}

function buildRuler(duration) {
  if (!duration) return [0];
  const step = duration > 360 ? 60 : duration > 120 ? 30 : 10;
  const ticks = [];
  for (let tick = 0; tick <= duration; tick += step) ticks.push(tick);
  if (ticks[ticks.length - 1] !== duration) ticks.push(duration);
  return ticks;
}

function positionPercent(value, duration) {
  if (!duration) return 0;
  return Math.min(100, Math.max(0, (value / duration) * 100));
}

function itemKey(trackType, index) {
  return `${trackType}-${index}`;
}

function clipPrimaryLabel(trackType, item) {
  if (trackType === "video") return item.asset_name || item.asset_type || item.track_label || "镜头";
  if (trackType === "text") return item.text || item.track_label || "花字";
  if (trackType === "subtitle") return item.text || "字幕";
  if (trackType === "audio") return item.asset_name || item.track_label || "音频";
  return item.track_label || trackType;
}

function clipTitle(trackType, item) {
  return `${clipPrimaryLabel(trackType, item)}\n${formatShortTime(item.start || 0)} / ${Number(item.duration || 0).toFixed(1)}s\n${item.note || item.effect || item.style || ""}`;
}

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

function formatShortTime(seconds) {
  const total = Math.round(Number(seconds || 0));
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${String(secs).padStart(2, "0")}`;
}
