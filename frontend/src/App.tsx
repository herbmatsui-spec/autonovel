import React, { useState, useEffect } from "react";
import { NovelProvider, useNovelContext } from "./context/NovelContext";
import { useToast } from "./hooks/useToast";
import { ToastContainer } from "./components/common/ToastContainer";
import GeneratePanel from "./components/GeneratePanel";
import ExportPanel from "./components/ExportPanel";
import GraphVisualization from "./components/GraphVisualization";
import { StudioWorkspace } from "./components/studio/StudioWorkspace";
import { AssetPackPanel } from "./components/AssetPackPanel";
import ConfigPanel from "./components/ConfigPanel";
import { BookSelector } from "./components/common/BookSelector";
import { getGenreBadgeConfig } from "./constants/genres";

function AppContent() {
  const { toasts, addToast, removeToast } = useToast();
  const {
    selectedBookId,
    setSelectedBookId,
    books,
    selectedBook,
    refreshBooks,
    setIsWizardActive,
    setWizardStep,
    hasCompletedWizard,
  } = useNovelContext();
  const [showGraph, setShowGraph] = useState(false);
  const [showMedia, setShowMedia] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [showTransitionOverlay, setShowTransitionOverlay] = useState(false);
  const [mode, setMode] = useState<"easy" | "studio">(() => {
    if (typeof window === "undefined") return "studio";
    return (localStorage.getItem("autonovel.mode") as "easy" | "studio") || "studio";
  });

  // 初回マウント時に作品一覧を読み込み
  React.useEffect(() => {
    refreshBooks();
  }, [refreshBooks]);

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

  useEffect(() => {
    localStorage.setItem("autonovel.mode", mode);
  }, [mode]);

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
      {showConfig && (
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
          data-testid="config-modal"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowConfig(false);
          }}
        >
          <div
            style={{
              background: "var(--card-bg, #18181b)",
              border: "1px solid var(--border-color, #27272a)",
              borderRadius: "12px",
              width: "90%",
              maxWidth: "500px",
              padding: "20px",
              maxHeight: "85vh",
              overflowY: "auto",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h2 style={{ margin: 0, fontSize: "1.2rem", color: "var(--accent-primary, #a78bfa)" }}>
                ⚙️ LLM設定
              </h2>
              <button
                type="button"
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}
                onClick={() => setShowConfig(false)}
                data-testid="btn-close-config-modal"
              >
                ✕
              </button>
            </div>
            <ConfigPanel onClose={() => setShowConfig(false)} />
          </div>
        </div>
      )}

<header className="header">
        <div style={{ display: "flex", alignItems: "center", gap: "16px", flex: 1 }}>
          <div>
            <h1 className="brand-title">AutoNovel Studio</h1>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
              AI 執筆・設定管理・矛盾診断・マルチメディア生成スタジオ
            </p>
          </div>
          <BookSelector
            currentBook={selectedBook}
            books={books}
            onSelectBook={(book) => setSelectedBookId(book.id)}
            onCreateBook={async (payload) => {
              const { createBook } = await import("./api/books");
              const newBook = await createBook(payload);
              await refreshBooks();
              setSelectedBookId(newBook.id);
              
              if (!hasCompletedWizard) {
                setWizardStep(1);
                setIsWizardActive(true);
              }
            }}
          />
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
              onClick={() => {
                if (mode === "easy") {
                  // EasyからStudioへの切り替え時はオーバーレイを表示
                  setShowTransitionOverlay(true);
                }
                setMode("studio");
              }}
              data-testid="btn-mode-studio"
            >
              🚀 上級者 Studio
            </button>
          </div>

<button
  onClick={() => setShowConfig(true)}
  style={{
    padding: "6px 12px",
    borderRadius: "8px",
    backgroundColor: "var(--accent-yellow, #f59e0b)",
    color: "white",
    border: "none",
    cursor: "pointer",
    fontSize: "0.85rem",
    fontWeight: 500,
    display: "flex",
    alignItems: "center",
    gap: "4px",
  }}
  data-testid="open-config-btn"
>
  ⚙️ LLM設定
</button>

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
          {(() => {
            const c = getGenreBadgeConfig(selectedBook?.genre || "ハイファンタジー (R15)");
            return (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "4px 12px",
                  borderRadius: "9999px",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  backgroundColor: c.bg,
                  color: c.text,
                  border: `1px solid ${c.border}`,
                }}
              >
                <span>{c.emoji}</span>
                <span>{selectedBook?.genre || "ハイファンタジー (R15)"}</span>
              </span>
            );
          })()}
        </div>
      </header>

      {showTransitionOverlay && (
        <div
          className="transition-overlay"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 999,
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowTransitionOverlay(false);
          }}
        >
          <div
            style={{
              background: "var(--card-bg, #18181b)",
              border: "2px solid var(--accent-primary, #a78bfa)",
              borderRadius: "16px",
              width: "90%",
              maxWidth: "500px",
              padding: "32px",
              textAlign: "center",
            }}
          >
            <h2 style={{ marginBottom: "24px", color: "var(--accent-primary, #a78bfa)" }}>
              🚀 Studioモードへようこそ！
            </h2>
            <div style={{ textAlign: "left", marginBottom: "24px" }}>
              <p>EasyモードからStudioモードへの移行時に、以下の高度な機能が利用可能になります：</p>
              <ul style={{ paddingLeft: "20px" }}>
                <li>📊 リアルタイム品質スコアと詳細なフィードバック</li>
                <li>🎭 キャラクター詳細プロファイルと関係性マッピング</li>
                <li>🖼️ シーン別マルチメディアプレビューと画像生成</li>
                <li>📖 プロットビジュアライザーとBeatシート編集</li>
                <li>🔍 AI診断による矛盾検出と修正提案</li>
                <li>⚡ ブランチベースの実験的執筆とバージョン管理</li>
              </ul>
            </div>
            <div style={{ display: "flex", justifyContent: "center", gap: "16px" }}>
              <button
                onClick={() => setShowTransitionOverlay(false)}
                style={{
                  padding: "12px 24px",
                  backgroundColor: "var(--accent-primary, #a78bfa)",
                  color: "white",
                  border: "none",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontWeight: "600",
                }}
              >
                今すぐ体験する
              </button>
              <button
                onClick={() => {
                  setShowTransitionOverlay(false);
                  setMode("easy"); // Easyモードに戻す
                }}
                style={{
                  padding: "12px 24px",
                  backgroundColor: "transparent",
                  border: "2px solid var(--text-muted)",
                  color: "var(--text-muted)",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontWeight: "600",
                }}
              >
                今はEasyモードで
              </button>
            </div>
          </div>
        </div>
      )}

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
