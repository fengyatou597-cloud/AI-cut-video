const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    let detail = "请求失败";
    try {
      const data = await response.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      detail = await response.text();
    }
    throw new Error(detail);
  }
  return response.json();
}

export const apiBase = API_BASE;

export const api = {
  getTemplates: () => request("/api/templates"),
  getSettings: () => request("/api/settings"),
  getDraftDirCandidates: () => request("/api/settings/draft-dir-candidates"),
  updateSettings: (payload) =>
    request("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  createDemoProject: () => request("/api/demo/seed", { method: "POST" }),
  listProjectOverview: () => request("/api/projects/overview"),
  getProjectOverview: (projectId) => request(`/api/projects/${projectId}/overview`),
  listProjects: () => request("/api/projects"),
  createProject: (payload) =>
    request("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  getProject: (projectId) => request(`/api/projects/${projectId}`),
  uploadScript: (projectId, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/api/projects/${projectId}/script/upload`, { method: "POST", body: form });
  },
  getLatestScript: (projectId) => request(`/api/projects/${projectId}/script/latest`),
  uploadSubtitles: (projectId, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/api/projects/${projectId}/script/subtitles/upload`, { method: "POST", body: form });
  },
  getLatestSubtitles: (projectId) => request(`/api/projects/${projectId}/script/subtitles/latest`),
  generateStoryboard: (projectId) => request(`/api/projects/${projectId}/script/generate-storyboard`, { method: "POST" }),
  getStoryboard: (projectId) => request(`/api/projects/${projectId}/storyboard`),
  updateStoryboard: (projectId, data) =>
    request(`/api/projects/${projectId}/storyboard`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data }),
    }),
  listAssets: (projectId) => request(`/api/projects/${projectId}/assets`),
  uploadAsset: (projectId, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/api/projects/${projectId}/assets/upload`, { method: "POST", body: form });
  },
  analyzeAsset: (projectId, assetId) => request(`/api/projects/${projectId}/assets/${assetId}/analyze`, { method: "POST" }),
  analyzeAllAssets: (projectId) => request(`/api/projects/${projectId}/assets/analyze-all`, { method: "POST" }),
  deleteAsset: (projectId, assetId) => request(`/api/projects/${projectId}/assets/${assetId}/delete`, { method: "POST" }),
  generateTimeline: (projectId) => request(`/api/projects/${projectId}/timeline/generate`, { method: "POST" }),
  getTimeline: (projectId) => request(`/api/projects/${projectId}/timeline`),
  applyAiAdjustment: (projectId, instruction) =>
    request(`/api/projects/${projectId}/adjustments/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ instruction }),
    }),
  getDraftEnvironment: (projectId) => request(`/api/projects/${projectId}/draft/environment`),
  generateDraft: (projectId) => request(`/api/projects/${projectId}/draft/generate`, { method: "POST" }),
  listDraftExports: (projectId) => request(`/api/projects/${projectId}/draft/exports`),
};

