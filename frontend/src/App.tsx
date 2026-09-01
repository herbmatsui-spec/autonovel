import React, { useState } from "react";
import { NovelProvider } from "./context/NovelContext";
import { useToast } from "./hooks/useToast";
import { ToastContainer } from "./components/common/ToastContainer";
import GeneratePanel from "./components/GeneratePanel";
import ExportPanel from "./components/ExportPanel";
import GraphVisualization from "./components/GraphVisualization";
import { StudioWorkspace } from "./components/studio/StudioWorkspace";

function AppContent() {
  const { toasts, addToast, removeToast } = useToast();
  const [showGraph, setShowGraph] = useState(false);
  const [mode, setMode] = useState<"easy" | "studio">("studio");

  const handleMessage = (msg: string) => {
    if (!msg) return;
    if (msg.startsWith("❌")) {
      addToast(msg.replace(/^❌\s*/u, ""), "error");
    } else if (msg.startsWith("✨") || msg.startsWith("📦")) {
      addToast(msg.replace(/^[✨📦]\s*/u, ""), "success");
    } else {
      addToast(msg, "info");
    }
  };

  return (
    <div className={mode === "studio" ? "container-fluid" : "container"} style={mode === "studio" ? { maxWidth: "1500px", margin: "0 auto" } : undefined}>
      <ToastContainer toasts={toasts} onClose={removeToast} />

      {showGraph && <GraphVisualization onClose={() => setShowGraph(false)} />}

      <header className="header">
        <div>
          <h1 className="brand-title">AutoNovel Studio</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
            Notion AI × Sudowrite 式 次世代AI小説執筆・設定管理スタジオ
          </p>
        </div>

        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          {/* モード切替スイッチ */}
          <div className="mode-switcher" data-testid="mode-switcher">
            <button
              type="button"
              className={`mode-btn ${mode === "easy" ? "mode-btn--active" : ""}`}
              onClick={() => setMode("easy")}
              data-testid="btn-mode-easy"
            >
              ⚡ かんたんモード
            </button>
            <button
              type="button"
              className={`mode-btn ${mode === "studio" ? "mode-btn--active" : ""}`}
              onClick={() => setMode("studio")}
              data-testid="btn-mode-studio"
            >
              🚀 上級者 Studio
            </button>
          </div>

          <button
            onClick={() => setShowGraph(true)}
            style={{
              padding: "6px 12px",
              borderRadius: "8px",
              backgroundColor: "var(--accent-purple, #8b5cf6)",
              color: "white",
              border: "none",
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: 500,
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
            data-testid="open-graph-btn"
          >
            📊 相関図
          </button>
          <span className="badge-r15">R15 ファンタジー</span>
        </div>
      </header>

      {mode === "easy" ? (
        <main className="main-grid">
          <GeneratePanel onMessage={handleMessage} />
          <ExportPanel
            onExportMessage={handleMessage}
            onPromoteToStudio={() => setMode("studio")}
          />
        </main>
      ) : (
        <StudioWorkspace
          onMessage={handleMessage}
          onOpenGraph={() => setShowGraph(true)}
        />
      )}
    </div>
  );
}

export default function App() {
  return (
    <NovelProvider>
      <AppContent />
    </NovelProvider>
  );
}
