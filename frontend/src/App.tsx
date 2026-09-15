import React, { useState, useEffect, Suspense, lazy } from "react";
import { NovelProvider, useNovelContext } from "./context/NovelContext";
import { useToast } from "./hooks/useToast";
import { useAppTheme, AppTheme } from "./hooks/useAppTheme";
import { ToastContainer } from "./components/common/ToastContainer";
import { Modal } from "./components/common/Modal";
import { Button } from "./components/common/Button";
import GeneratePanel from "./components/GeneratePanel";
import ExportPanel from "./components/ExportPanel";
import { StudioWorkspace } from "./components/studio/StudioWorkspace";
import { AssetPackPanel } from "./components/AssetPackPanel";
import ConfigPanel from "./components/ConfigPanel";
import { BookSelector } from "./components/common/BookSelector";
import { BookshelfModal } from "./components/common/BookshelfModal";
import { getGenreBadgeConfig } from "./constants/genres";
import { MobileBottomNav } from "./components/mobile/MobileBottomNav";
import { MobileChapterDrawer } from "./components/mobile/MobileChapterDrawer";
import { MobileQuickActionBar } from "./components/mobile/MobileQuickActionBar";

// 提案3: react-force-graph-2d は重いため React.lazy でコード分割
const GraphVisualization = lazy(
  () => import("./components/GraphVisualization")
);

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
    chapters,
    currentEpNum,
    setCurrentEpNum,
  } = useNovelContext();
  const [showGraph, setShowGraph] = useState(false);
  const [showMedia, setShowMedia] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  // 提案4: モバイル「books」タブ用の本棚モーダル
  const [showBookshelf, setShowBookshelf] = useState(false);
  const [showTransitionOverlay, setShowTransitionOverlay] = useState(false);
  const [mobileTab, setMobileTab] = useState<'books' | 'plots' | 'writing' | 'settings'>('writing');
  const [isChapterDrawerOpen, setIsChapterDrawerOpen] = useState(false);
  const [mode, setMode] = useState<"easy" | "studio">(() => {
    if (typeof window === "undefined") return "studio";
    return (localStorage.getItem("autonovel.mode") as "easy" | "studio") || "studio";
  });
  // 提案8: アプリ全体のテーマ（ライト/ダーク/セピア）
  const { theme, setTheme } = useAppTheme();

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

      {showGraph && (
        <Suspense fallback={null}>
          <GraphVisualization onClose={() => setShowGraph(false)} />
        </Suspense>
      )}

      {/* マルチメディア生成モーダル（共通 Modal に統合） */}
      <Modal
        isOpen={showMedia}
        onClose={() => setShowMedia(false)}
        title="🖼️ マルチメディア生成 (Asset Pack)"
        testId="media-modal"
        closeBtnTestId="btn-close-media-modal"
      >
        <AssetPackPanel bookId={selectedBookId} />
      </Modal>

      {/* LLM設定モーダル（共通 Modal に統合） */}
      <Modal
        isOpen={showConfig}
        onClose={() => setShowConfig(false)}
        title="⚙️ LLM設定"
        testId="config-modal"
        closeBtnTestId="btn-close-config-modal"
        maxWidth={500}
      >
        <ConfigPanel onClose={() => setShowConfig(false)} />
      </Modal>

      {/* Studioモード移行オーバーレイ（共通 Modal に統合） */}
      <Modal
        isOpen={showTransitionOverlay}
        onClose={() => setShowTransitionOverlay(false)}
        title="🚀 Studioモードへようこそ！"
        testId="transition-overlay"
        closeBtnTestId="btn-close-transition-overlay"
        maxWidth={500}
        zIndex={999}
      >
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
          <Button variant="primary" onClick={() => setShowTransitionOverlay(false)}>
            今すぐ体験する
          </Button>
          <Button variant="secondary" onClick={() => {
            setShowTransitionOverlay(false);
            setMode("easy"); // Easyモードに戻す
          }}>
            今はEasyモードで
          </Button>
        </div>
      </Modal>

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

          {/* 提案8: テーマ切替セレクター（ライト/ダーク/セピア） */}
          <select
            className="select theme-selector"
            value={theme}
            onChange={(e) => setTheme(e.target.value as AppTheme)}
            aria-label="テーマを選択"
            data-testid="theme-selector"
            style={{ width: "auto", padding: "6px 10px", fontSize: "0.85rem" }}
          >
            <option value="dark">🌙 ダーク</option>
            <option value="light">☀️ ライト</option>
            <option value="sepia">📜 セピア</option>
          </select>

          <Button
            variant="accent-yellow"
            size="sm"
            onClick={() => setShowConfig(true)}
            data-testid="open-config-btn"
          >
            ⚙️ LLM設定
          </Button>

          <Button
            variant="accent-cyan"
            size="sm"
            onClick={() => setShowMedia(true)}
            data-testid="open-media-btn"
          >
            🖼️ 画像生成
          </Button>

          <Button
            variant="accent-purple"
            size="sm"
            onClick={() => setShowGraph(true)}
            data-testid="open-graph-btn"
          >
            📊 相関図
          </Button>

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

      {/* Mobile Responsive Navigation & Toolbars */}
      <MobileQuickActionBar
        onInsertText={(txt) => {
          handleMessage(`テキストに「${txt}」を挿入しました`);
        }}
        onAiContinue={() => handleMessage("AI続きの執筆を開始します...")}
        onProofread={() => handleMessage("文章の校正を実行中...")}
      />

      <MobileChapterDrawer
        isOpen={isChapterDrawerOpen}
        onClose={() => setIsChapterDrawerOpen(false)}
        chapters={chapters || []}
        currentChapterId={currentEpNum}
        onSelectChapter={(epNum) => {
          setCurrentEpNum(epNum);
          handleMessage(`第 ${epNum} 話を選択しました`);
        }}
      />

      <MobileBottomNav
        activeTab={mobileTab}
        onTabChange={(tab) => {
          setMobileTab(tab);
          // 提案4: タブ名と動作の不一致を解消
          if (tab === 'books') {
            setShowBookshelf(true); // 本棚モーダル（LLM設定ではなく作品一覧）
          } else if (tab === 'plots') {
            setShowGraph(true);
          } else if (tab === 'writing') {
            setIsChapterDrawerOpen(true);
          } else if (tab === 'settings') {
            setShowConfig(true);
          }
        }}
      />

      {/* 提案4: モバイル「books」タブ用の本棚モーダル */}
      <BookshelfModal
        isOpen={showBookshelf}
        onClose={() => setShowBookshelf(false)}
        books={books}
        selectedBook={selectedBook}
        onSelectBook={(book) => {
          setSelectedBookId(book.id);
          setShowBookshelf(false);
        }}
        onCreateBook={async (payload) => {
          const { createBook } = await import("./api/books");
          const newBook = await createBook(payload);
          await refreshBooks();
          setSelectedBookId(newBook.id);
          setShowBookshelf(false);
        }}
      />
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
