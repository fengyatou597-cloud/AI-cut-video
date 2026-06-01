import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AssetLibraryPage } from "./pages/AssetLibraryPage";
import { AiAdjustPage } from "./pages/AiAdjustPage";
import { DraftExportPage } from "./pages/DraftExportPage";
import { ProjectCreatePage } from "./pages/ProjectCreatePage";
import { ProjectListPage } from "./pages/ProjectListPage";
import { ProjectOverviewPage } from "./pages/ProjectOverviewPage";
import { ScriptUploadPage } from "./pages/ScriptUploadPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StoryboardEditorPage } from "./pages/StoryboardEditorPage";
import { TimelinePreviewPage } from "./pages/TimelinePreviewPage";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<ProjectListPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/projects/new" element={<ProjectCreatePage />} />
          <Route path="/projects/:projectId" element={<Navigate to="overview" replace />} />
          <Route path="/projects/:projectId/overview" element={<ProjectOverviewPage />} />
          <Route path="/projects/:projectId/script" element={<ScriptUploadPage />} />
          <Route path="/projects/:projectId/assets" element={<AssetLibraryPage />} />
          <Route path="/projects/:projectId/storyboard" element={<StoryboardEditorPage />} />
          <Route path="/projects/:projectId/timeline" element={<TimelinePreviewPage />} />
          <Route path="/projects/:projectId/adjust" element={<AiAdjustPage />} />
          <Route path="/projects/:projectId/draft" element={<DraftExportPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  </React.StrictMode>
);
