import React, { useState } from "react";
import { useLocation, useNavigate, Outlet } from "react-router-dom";
import { useNovelContext } from "../../context/NovelContext";
import { useModal } from "../../context/ModalContext";
import { useAppTheme, AppTheme } from "../../hooks/useAppTheme";
import { useToast } from "../../hooks/useToast";
import { ToastContainer } from "../common/ToastContainer";
import { Button } from "../common/Button";
import { BookSelector } from "../common/BookSelector";
import { getGenreBadgeConfig } from "../../constants/genres";
import { MobileBottomNav } from "../mobile/MobileBottomNav";
import { MobileChapterDrawer } from "../mobile/MobileChapterDrawer";
import { MobileQuickActionBar } from "../mobile/MobileQuickActionBar";

export interface AppLayoutProps {
  children?: React.ReactNode;
  onMessage?: (msg: string) => void;
}

export function AppLayout({ children, onMessage }: AppLayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    books,
    selectedBook,
    setSelectedBookId,
    refreshBooks,
    hasCompletedWizard,
    setWizardStep,
    setIsWizardActive,
    chapters,
    currentEpNum,
    setCurrentEpNum,
  } = useNovelContext();

  const {
    openModal,
    setShowConfig,
    setShowWizardWorkflow,
    setShowMedia,
    setShowGraph,
    setShowTransitionOverlay,
    isChapterDrawerOpen,
    setIsChapterDrawerOpen,
  } = useModal();

  const { theme, setTheme } = useAppTheme();
  const { toasts, addToast, removeToast } = useToast();
  const [mobileTab, setMobileTab] = useState<"books" | "plots" | "writing" | "settings">("writing");

  const isStudio = location.pathname.startsWith("/studio");
  const isWizard = location.pathname.startsWith("/wizard");

  React.useEffect(() => {
    refreshBooks();
  }, [refreshBooks]);

  const handleMessage = (msg: string) => {
    if (!msg) return;
    if (msg.startsWith("❌")) {
      addToast(msg.replace(/^❌\s*/u, ""), "error");
    } else if (msg.startsWith("✨") || msg.startsWith("📦")) {
      addToast(msg.replace(/^[✨📦]\s*/u, ""), "success");
    } else {
      addToast(msg, "info");
    }
    onMessage?.(msg);
  };

  return (
    <div
      className={isStudio ? "container-fluid" : "container"}
      style={isStudio ? { maxWidth: "1500px", margin: "0 auto" } : undefined}
    >
      <ToastContainer toasts={toasts} onClose={removeToast} />
      <header className="header">
        <div style={{ display: "flex", alignItems: "center", gap: "16px", flex: 1 }}>
          <div>
            <h1 className="brand-title" onClick={() => navigate("/")} style={{ cursor: "pointer" }}>
              AutoNovel Studio
            </h1>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
              AI 執筆・設定管理・矛盾診断・マルチメディア生成スタジオ
            </p>
          </div>
          <BookSelector
            currentBook={selectedBook}
            books={books}
            onSelectBook={(book) => setSelectedBookId(book.id)}
            onCreateBook={async (payload) => {
              const { createBook } = await import("../../api/books");
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
              className={`mode-btn ${!isStudio && !isWizard ? "mode-btn--active" : ""}`}
              onClick={() => navigate("/")}
              data-testid="btn-mode-easy"
            >
              ⚡ かんたんモード
            </button>
            <button
              type="button"
              className={`mode-btn ${isStudio ? "mode-btn--active" : ""}`}
              onClick={() => navigate("/studio")}
              data-testid="btn-mode-studio"
            >
              🚀 上級者 Studio
            </button>
          </div>

          {/* テーマ切替セレクター */}
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
            variant="primary"
            size="sm"
            onClick={() => setShowWizardWorkflow(true)}
            data-testid="open-wizard-btn"
          >
            ✨ 3ステップ共創ウィザード
          </Button>

          <Button
            variant="accent-cyan"
            size="sm"
            onClick={() => setShowMedia(true)}
            data-testid="open-media-btn"
          >
            📦 アセットパック
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

      {/* Main page content via Outlet or children */}
      {children || <Outlet />}

      {/* Mobile Navigation */}
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
          if (tab === "books") {
            openModal("bookshelf");
          } else if (tab === "plots") {
            setShowGraph(true);
          } else if (tab === "writing") {
            setIsChapterDrawerOpen(true);
          } else if (tab === "settings") {
            setShowConfig(true);
          }
        }}
      />
    </div>
  );
}

export default AppLayout;
