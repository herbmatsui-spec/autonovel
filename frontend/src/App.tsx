import React, { useState, useEffect } from "react";
import { NovelProvider, useNovelContext } from "./context/NovelContext";
import { useToast } from "./hooks/useToast";
import { ToastContainer } from "./components/common/ToastContainer";
import GeneratePanel from "./components/GeneratePanel";
import ExportPanel from "./components/ExportPanel";
import GraphVisualization from "./components/GraphVisualization";
import { StudioWorkspace } from "./components/studio/StudioWorkspace";
import { AssetPackPanel } from "./components/AssetPackPanel";

function AppContent() {
  const { toasts, addToast, removeToast } = useToast();
  const { selectedBookId } = useNovelContext();
  const [showGraph, setShowGraph] = useState(false);
  const [showMedia, setShowMedia] = useState(false);
  const [mode, setMode] = useState<"easy" | "studio">("studio");

  // /studio/:bookId?token=xxx URL を popstate 経由で検知し Studio モードへ切替
  useEffect(() => {
    const syncModeFromLocation = () => {
      if (typeof window === "undefined") return;
      const path = window.location.pathname || "";
      if (path.startsWith("/studio/")) {
        setMode("studio");
      }
    };
    syncModeFromLocation();
    window.addEventListener("popstate", syncModeFromLocation);
    return () => window.removeEventListener("popstate", syncModeFromLocation);
  }, []);

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

      {showMedia && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            backdropFilter: "blur(4px)",
          }}
          data-testid="media-modal"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowMedia(false);
          }}
        >
          <div
            style={{
              background: "var(--card-bg, #18181b)",
              border: "1px solid var(--border-color, #27272a)",
              borderRadius: "12px",
              width: "90%",
              maxWidth: "900px",
              padding: "20px",
              maxHeight: "85vh",
              overflowY: "auto",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h2 style={{ margin: 0, fontSize: "1.2rem", color: "var(--accent-primary, #a78bfa)" }}>
                🖼️ マルチメディア生成 (Asset Pack)
              </h2>
              <button
                type="button"
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}
                onClick={() => setShowMedia(false)}
                data-testid="btn-close-media-modal"
              >
                ✕
              </button>
            </div>
            <AssetPackPanel bookId={selectedBookId} />
          </div>
        </div>
      )}

      <header className="header">
        <div>
          <h1 className="brand-title">AutoNovel Studio</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
            AI 執筆・設定管理・矛盾診断・マルチメディア生成スタジオ
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
            onClick={() => setShowMedia(true)}
            style={{
              padding: "6px 12px",
              borderRadius: "8px",
              backgroundColor: "var(--accent-cyan, #06b6d4)",
              color: "white",
              border: "none",
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: 500,
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
            data-testid="open-media-btn"
          >
            🖼️ 画像生成
          </button>
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
