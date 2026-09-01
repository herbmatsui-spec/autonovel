import React, { useState } from "react";
import { NovelProvider } from "./context/NovelContext";
import { useToast } from "./hooks/useToast";
import { ToastContainer } from "./components/common/ToastContainer";
import GeneratePanel from "./components/GeneratePanel";
import ExportPanel from "./components/ExportPanel";
import GraphVisualization from "./components/GraphVisualization";

function AppContent() {
  const { toasts, addToast, removeToast } = useToast();
  const [showGraph, setShowGraph] = useState(false);

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
    <div className="container">
      <ToastContainer toasts={toasts} onClose={removeToast} />

      {showGraph && <GraphVisualization onClose={() => setShowGraph(false)} />}

      <header className="header">
        <div>
          <h1 className="brand-title">AutoNovel Studio</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
            AI小説執筆・設定管理・ワンクリックZIP納品ワークスペース
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <button
            onClick={() => setShowGraph(true)}
            style={{
              padding: "6px 12px",
              borderRadius: "6px",
              backgroundColor: "var(--primary, #3b82f6)",
              color: "white",
              border: "none",
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: 500,
            }}
            data-testid="open-graph-btn"
          >
            📊 相関図を表示
          </button>
          <span className="badge-r15">R15 ファンタジー対応</span>
          <span className="badge-status">Gemini & OpenAI 対応</span>
        </div>
      </header>

      <main className="main-grid">
        <GeneratePanel onMessage={handleMessage} />
        <ExportPanel onExportMessage={handleMessage} />
      </main>
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
