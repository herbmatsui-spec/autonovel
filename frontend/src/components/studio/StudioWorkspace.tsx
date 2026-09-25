import React, { useState, useEffect, useRef } from "react";
import { useNovelContext } from "../../context/NovelContext";
import { apiFetch, handleResponse } from "../../api/client";
import { Editor } from "../editor/Editor";
import { NextBeatsPanel } from "../editor/NextBeatsPanel";
import { MultimediaPreviewPanel } from "../editor/MultimediaPreviewPanel";
import { WizardStep } from "../wizard/WizardStep";
import { EditorialSidebar } from "../editor/EditorialSidebar";
import { ChapterOutlineTree } from "./ChapterOutlineTree";
import { AssetPackPanel } from "../AssetPackPanel";
import { StyleComparisonModal } from "../style/StyleComparisonModal";
import { BookShowcaseModal } from "../showcase/BookShowcaseModal";
import { BranchManagement } from "../branches/BranchManagement";
import { ConflictReportPanel, ConflictReport } from "../editor/ConflictReportPanel";
import { runHybridAudit } from "../../api/editor";
import { CommercialPublishPanel } from "../commercial/CommercialPublishPanel";
import { QualityDashboardModal } from "./QualityDashboardModal";
import { fetchChapterBookScore } from "../../api/quality";
import { WorkspaceLayoutMode } from "../../types/editorLayout";
import { ZenWritingScreen } from "../editor/ZenWritingScreen";

interface StudioWorkspaceProps {
  onMessage?: (msg: string, type?: "success" | "error" | "info") => void;
  onOpenGraph?: () => void;
}

interface BudgetInfo {
  book_id: number;
  budget_usd: number;
  current_cost_usd: number;
  ratio: number;
  status: "normal" | "warning" | "exceeded";
  downgrade_active: boolean;
  recommended_model: string;
}

type StudioTab = "editor" | "branches" | "audit" | "multimedia" | "commercial";

export const StudioWorkspace: React.FC<StudioWorkspaceProps> = ({
  onMessage,
  onOpenGraph,
}) => {
  const {
    character,
    setCharacter,
    currentChapterText,
    setCurrentChapterText,
    selectedBookId,
    selectedBook,
    currentEpNum,
    setCurrentEpNum,
    isWizardActive,
    setIsWizardActive,
    wizardStep,
    setWizardStep,
    hasCompletedWizard,
    setHasCompletedWizard,
    mode,
    setMode,
  } = useNovelContext();

  const [tab, setTab] = useState<StudioTab>(() => {
    if (typeof window === "undefined") return "editor";
    try {
      const saved = window.localStorage.getItem("autonovel.studioTab");
      if (saved === "editor" || saved === "multimedia" || saved === "branches" || saved === "audit" || saved === "commercial") return saved;
    } catch {
      // localStorage が使れない環境では無視
    }
    return "editor";
  });

  const [layoutMode, setLayoutMode] = useState<WorkspaceLayoutMode>(() => {
    if (typeof window === "undefined") return "studio";
    try {
      const saved = window.localStorage.getItem("autonovel.layoutMode");
      if (saved === "studio" || saved === "split" || saved === "zen") return saved;
    } catch {
      // localStorage が使れない環境では無視
    }
    return "studio";
  });

  useEffect(() => {
    try {
      window.localStorage.setItem("autonovel.layoutMode", layoutMode);
    } catch {
      // ignore storage error
    }
  }, [layoutMode]);

  useEffect(() => {
    try {
      window.localStorage.setItem("autonovel.studioTab", tab);
    } catch {
      // ignore storage error
    }
  }, [tab]);

  const [showLeftPane, setShowLeftPane] = useState(true);
  const [showRightPane, setShowRightPane] = useState(true);
  const [leftPaneWidth, setLeftPaneWidth] = useState(260);
  const [rightPaneWidth, setRightPaneWidth] = useState(340);
  const [isResizingLeft, setIsResizingLeft] = useState(false);
  const [isResizingRight, setIsResizingRight] = useState(false);
  const leftPaneRef = useRef<HTMLDivElement>(null);
  const rightPaneRef = useRef<HTMLDivElement>(null);
  const [showStyleComparison, setShowStyleComparison] = useState(false);
  const [showBookShowcase, setShowBookShowcase] = useState(false);
  const [showQualityDashboard, setShowQualityDashboard] = useState(false);
  const [chapterScore, setChapterScore] = useState<number | null>(null);
  const [budgetInfo, setBudgetInfo] = useState<BudgetInfo | null>(null);
  const [currentSceneName, setCurrentSceneName] = useState<string | null>(null);
  const [currentImageUrl, setCurrentImageUrl] = useState<string | undefined>(undefined);

  const handleLeftResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizingLeft(true);
    document.addEventListener('mousemove', handleLeftResizeMove);
    document.addEventListener('mouseup', handleLeftResizeEnd);
  };

  const handleLeftResizeMove = (e: MouseEvent) => {
    if (!isResizingLeft || !leftPaneRef.current) return;
    const newWidth = e.clientX - leftPaneRef.current.getBoundingClientRect().left;
    setLeftPaneWidth(Math.max(200, Math.min(400, newWidth)));
  };

  const handleLeftResizeEnd = () => {
    setIsResizingLeft(false);
    document.removeEventListener('mousemove', handleLeftResizeMove);
    document.removeEventListener('mouseup', handleLeftResizeEnd);
  };

  const handleRightResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizingRight(true);
    document.addEventListener('mousemove', handleRightResizeMove);
    document.addEventListener('mouseup', handleRightResizeEnd);
  };

  const handleRightResizeMove = (e: MouseEvent) => {
    if (!isResizingRight || !rightPaneRef.current) return;
    const rect = rightPaneRef.current.getBoundingClientRect();
    const newWidth = rect.right - e.clientX;
    setRightPaneWidth(Math.max(280, Math.min(480, newWidth)));
  };

  const handleRightResizeEnd = () => {
    setIsResizingRight(false);
    document.removeEventListener('mousemove', handleRightResizeMove);
    document.removeEventListener('mouseup', handleRightResizeEnd);
  };

  useEffect(() => {
    const fetchImage = async () => {
      if (!currentSceneName) {
        setCurrentImageUrl(undefined);
        return;
      }
      try {
        // 実際の実装では /api/multimedia/images/{sceneName} のようなエンドポイントを呼び出す
        // 現時点ではプレースホルダーを使用して表示を確認し、API連携の構造を構築する
        setCurrentImageUrl(`https://placehold.co/600x400?text=${encodeURIComponent(currentSceneName)}`);
      } catch (e) {
        console.error("Failed to fetch scene image", e);
        setCurrentImageUrl(undefined);
      }
    };
    void fetchImage();
  }, [currentSceneName]);

  useEffect(() => {
    const fetchBudget = async () => {
      if (!selectedBookId) return;
      try {
        const res = await apiFetch(`/api/cost/budget/${selectedBookId}`);
        const data = await handleResponse<BudgetInfo>(res, "Failed to fetch budget");
        setBudgetInfo(data);
      } catch {
        setBudgetInfo(null);
      }
    };
    void fetchBudget();
  }, [selectedBookId]);

  useEffect(() => {
    const fetchScore = async () => {
      if (!selectedBookId) return;
      try {
        const scoreData = await fetchChapterBookScore(selectedBookId, currentEpNum);
        setChapterScore(scoreData.overall_score);
      } catch (e) {
        console.error("Failed to fetch chapter score", e);
        setChapterScore(null);
      }
    };
    void fetchScore();
  }, [selectedBookId, currentEpNum]);

  const handleCreateBranch = () => {
    setTab("branches");
    onMessage?.("🌿 IF分岐管理タブに切り替えました", "info");
  };

  const [auditReport, setAuditReport] = useState<ConflictReport | null>(null);
  const [isAuditing, setIsAuditing] = useState(false);

  const handleRunHybridAudit = async () => {
    setIsAuditing(true);
    handleToast("🧠 二層ハイブリッド監査を実行中...", "info");
    try {
      const res = await runHybridAudit({
        draft_text: currentChapterText || "本文なし",
        character_profiles: character ? `${character.name}: ${character.genre}` : "",
        plot_spec: `第${currentEpNum}話`,
      });
      const convertedReport: ConflictReport = {
        book_id: selectedBookId || 1,
        ep_num: currentEpNum,
        patch_review_id: null,
        summary: `総合スコア: ${res.final_score}点 (定性: ${res.qualitative.overall_score}点 / 定量: ${res.quantitative_score}点)\n講評: ${res.qualitative.critique}`,
        total_count: res.conflicts.length,
        critical_count: res.conflicts.filter((c) => c.severity === "critical").length,
        high_count: res.conflicts.filter((c) => c.severity === "high").length,
        medium_count: res.conflicts.filter((c) => c.severity === "medium").length,
        low_count: res.conflicts.filter((c) => c.severity === "low").length,
        conflicts: res.conflicts.map((c) => ({
          category: c.category,
          severity: c.severity,
          title: c.title,
          description: c.description,
          field_path: c.field_path ?? null,
          current_value: c.current_value ?? null,
          suggested_value: c.suggested_value ?? null,
          evidence_past: c.evidence_past ?? "",
          evidence_current: c.evidence_current ?? "",
          constraint_for_next: c.constraint_for_next ?? "",
          confidence: c.confidence ?? 0.9,
        })),
      };
      setAuditReport(convertedReport);
      setTab("audit");
      handleToast("✨ 二層ハイブリッド監査が完了しました", "success");
    } catch (e: any) {
      handleToast(e?.detail || e?.message || "二層ハイブリッド監査の実行に失敗しました", "error");
    } finally {
      setIsAuditing(false);
    }
  };

  const handleOpenAuditReport = () => {
    setTab("audit");
    onMessage?.("🧠 矛盾診断レポートタブに切り替えました", "info");
    if (!auditReport && !isAuditing) {
      void handleRunHybridAudit();
    }
  };

  const handleToast = (msg: string, type: "success" | "error" | "info") => {
    if (type === "error") {
      onMessage?.(`❌ ${msg}`, "error");
    } else if (type === "success") {
      onMessage?.(`✨ ${msg}`, "success");
    } else {
      onMessage?.(msg, type);
    }
  };

  const gridClass = [
    "studio-grid",
    !showLeftPane && !showRightPane
      ? "studio-grid--collapsed-both"
      : !showLeftPane
      ? "studio-grid--collapsed-left"
      : !showRightPane
      ? "studio-grid--collapsed-right"
      : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <>
      <div className={gridClass} data-testid="studio-workspace" style={{ 
        gridTemplateColumns: `${showLeftPane ? leftPaneWidth : 0}px 1fr ${showRightPane ? rightPaneWidth : 0}px`
      }}>
      {/* 左ペイン: 作品・登場人物・設定概要 & 章ツリー */}
      {showLeftPane ? (
        <>
          <aside id="character-settings-pane" className="studio-pane studio-sidebar-left" style={{ 
            gap: "16px", 
            display: "flex", 
            flexDirection: "column",
            width: leftPaneWidth,
            minWidth: 200,
            maxWidth: 400
          }} ref={leftPaneRef}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ fontSize: "1.05rem", color: "var(--accent-cyan)", fontWeight: 700 }}>
                📖 章一覧 & 設定
              </h2>
              <div style={{ display: "flex", gap: "6px" }}>
                {onOpenGraph && (
                  <button
                    type="button"
                    className="inline-ai-btn"
                    onClick={onOpenGraph}
                    title="GraphRAG 相関図を開く"
                    data-testid="btn-open-graph-studio"
                  >
                    📊
                  </button>
                )}
                <button
                  type="button"
                  className="pane-toggle-btn"
                  onClick={() => setShowLeftPane(false)}
                  title="左サイドバーを折りたたむ"
                  data-testid="btn-toggle-left-pane"
                >
                  ◀
                </button>
                <button
                  type="button"
                  onClick={() => setShowStyleComparison(true)}
                  className="pane-toggle-btn"
                  title="文体のBefore/Afterを比較"
                  data-testid="btn-open-style-comparison-studio"
                >
                  🔍
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTab("branches");
                    handleToast("🌿 IF分岐管理タブを開きました", "info");
                  }}
                  className="pane-toggle-btn"
                  title="分岐管理を開く"
                  data-testid="btn-open-branch-management-studio"
                >
                  🌿
                </button>
                <button
                  type="button"
                  onClick={() => setShowBookShowcase(true)}
                  title="縦書き装丁プレビューと宣伝カードを表示"
                  data-testid="btn-open-book-showcase-studio"
                >
                  📖
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (window.confirm("Easyモードに戻りますか？現在のStudioモードの設定は保存されます。")) {
                      setMode("easy");
                    }
                  }}
                  className="pane-toggle-btn"
                  title="Easyモードに戻る"
                  data-testid="btn-switch-to-easy-mode"
                >
                  🏠
                </button>
                {/* 書籍ショーケースモーダル */}
                {showBookShowcase && selectedBook && (
                  <div
                    style={{
                      position: "fixed",
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      background: "rgba(0,0,0,0.75)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      zIndex: 1000,
                      backdropFilter: "blur(4px)",
                    }}
                    data-testid="book-showcase-modal"
                  >
                    <BookShowcaseModal
                      onClose={() => setShowBookShowcase(false)}
                      bookData={{
                        title: selectedBook.title,
                        author: character.name || "不明な作者",
                        content: currentChapterText
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
            <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
              <ChapterOutlineTree
                onSelectChapter={(epNum) => {
                  setCurrentEpNum(epNum);
                  handleToast(`第 ${epNum} 話を選択しました`, "info");
                }}
                onMessage={handleToast}
              />
            </div>
          </aside>
          <div
            className="splitter"
            onMouseDown={handleLeftResizeStart}
            style={{
              width: "4px",
              cursor: "col-resize",
              background: isResizingLeft ? "var(--accent-purple)" : "var(--border-color)",
              transition: "background 0.1s",
              zIndex: 10
            }}
            data-testid="left-splitter"
          />
        </>
      ) : (
        <div
          className="splitter"
          onClick={() => setShowLeftPane(true)}
          style={{
            width: "4px",
            cursor: "pointer",
            background: "var(--accent-cyan)",
            opacity: 0.5,
            transition: "opacity 0.2s",
            zIndex: 10
          }}
          data-testid="left-splitter-collapsed"
        />
      )}

      <main className="studio-pane" style={{ minHeight: "600px", flex: 1 }}>
        {/* ペイン展開用ツールバー（折りたたみ時） */}
        {(!showLeftPane || !showRightPane) && (
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
            {!showLeftPane ? (
              <button
                type="button"
                className="pane-toggle-btn"
                onClick={() => setShowLeftPane(true)}
                title="左サイドバー（設定・章一覧）を展開"
                data-testid="btn-restore-left-pane"
              >
                ▶ 設定 & 章一覧
              </button>
            ) : (
              <div />
            )}
            {!showRightPane ? (
              <button
                type="button"
                className="pane-toggle-btn"
                onClick={() => setShowRightPane(true)}
                title="右サイドバー（AI編集者）を展開"
                data-testid="btn-restore-right-pane"
              >
                🧠 AI編集者 ◀
              </button>
            ) : (
              <div />
            )}
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: "8px",
            marginBottom: "12px",
            borderBottom: "1px solid var(--border-color)",
            paddingBottom: "8px",
          }}
          data-testid="studio-tab-bar"
        >
          <button
            type="button"
            className={`btn-tab ${tab === "editor" ? "btn-tab--active" : ""}`}
            onClick={() => setTab("editor")}
            data-testid="tab-studio-editor"
          >
            ✏️ エディタ
          </button>
          <button
            type="button"
            className={`btn-tab ${tab === "branches" ? "btn-tab--active" : ""}`}
            onClick={() => setTab("branches")}
            data-testid="tab-studio-branches"
          >
            🌿 IF分岐ルート
          </button>
          <button
            id="studio-tab-audit"
            type="button"
            className={`btn-tab ${tab === "audit" ? "btn-tab--active" : ""}`}
            onClick={() => setTab("audit")}
            data-testid="tab-studio-audit"
          >
            🧠 矛盾診断レポート
          </button>
          <button
            type="button"
            className={`btn-tab ${tab === "multimedia" ? "btn-tab--active" : ""}`}
            onClick={() => setTab("multimedia")}
            data-testid="tab-studio-multimedia"
          >
            🖼️ マルチメディア
          </button>
          <button
            type="button"
            className={`btn-tab ${tab === "commercial" ? "btn-tab--active" : ""}`}
            onClick={() => setTab("commercial")}
            data-testid="tab-studio-commercial"
          >
            📢 商用投稿
          </button>
          {budgetInfo && (
            <div
              style={{
                marginLeft: "auto",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "2px 10px",
                borderRadius: "6px",
                fontSize: "0.8rem",
                fontWeight: 600,
                background:
                  budgetInfo.status === "exceeded"
                    ? "rgba(239, 68, 68, 0.15)"
                    : budgetInfo.status === "warning"
                      ? "rgba(245, 158, 11, 0.15)"
                      : "rgba(34, 197, 94, 0.15)",
                color:
                  budgetInfo.status === "exceeded"
                    ? "#fca5a5"
                    : budgetInfo.status === "warning"
                      ? "#fbbf24"
                      : "#86efac",
              }}
              data-testid="cost-indicator"
              title={`Status: ${budgetInfo.status}${budgetInfo.downgrade_active ? " (downgrade active)" : ""}`}
            >
              💰 ${(budgetInfo.current_cost_usd ?? 0).toFixed(2)} / ${(budgetInfo.budget_usd ?? 0).toFixed(2)}
            </div>
          )}
          <div style={{ display: "flex", gap: "4px", marginLeft: "12px" }}>
            <button
              type="button"
              className={`btn-tab ${layoutMode === "studio" ? "btn-tab--active" : ""}`}
              onClick={() => setLayoutMode("studio")}
              title="完全Studioモード"
              data-testid="btn-layout-studio"
            >
              📊 完全Studio
            </button>
            <button
              type="button"
              className={`btn-tab ${layoutMode === "split" ? "btn-tab--active" : ""}`}
              onClick={() => setLayoutMode("split")}
              title="執筆重視モード"
              data-testid="btn-layout-split"
            >
              📝 執筆重視
            </button>
            <button
              type="button"
              className={`btn-tab ${layoutMode === "zen" ? "btn-tab--active" : ""}`}
              onClick={() => setLayoutMode("zen")}
              title="集中Zenモード"
              data-testid="btn-layout-zen"
            >
              🧘 集中Zen
            </button>
          </div>
        </div>

        {tab === "editor" && (
          <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", overflowY: "auto" }}>
              <Editor
                content={currentChapterText}
                onChange={(val) => {
                  setCurrentChapterText(val);
                  // Update scene name when content changes to keep markers in sync
                  // Note: we can't easily get cursor pos here, but the Editor's internal
                  // updateCurrentScene will be triggered by user interaction.
                }}
                genre={character.genre}
                onToast={handleToast}
                onCreateBranch={handleCreateBranch}
                onSceneChange={setCurrentSceneName}
              />

              <div id="next-beats-panel">
                <NextBeatsPanel
                  currentText={currentChapterText}
                  genre={character.genre}
                  bookId={selectedBookId}
                  onApplyBeat={(content, mode) => {
                    if (mode === "replace_all") {
                      setCurrentChapterText(content);
                    } else {
                      setCurrentChapterText((prev) => (prev ? `${prev}\n\n${content}` : content));
                    }
                  }}
                  onToast={handleToast}
                />
              </div>
            </div>
            <MultimediaPreviewPanel
              sceneName={currentSceneName}
              imageUrl={currentImageUrl}
            />
          </div>
        )}
        {tab === "multimedia" && (
          <>
            <div
              style={{
                background: "rgba(56, 189, 248, 0.08)",
                border: "1px solid rgba(56, 189, 248, 0.25)",
                borderRadius: "8px",
                padding: "10px 14px",
                marginBottom: "14px",
                fontSize: "0.85rem",
                color: "var(--accent-secondary, #38bdf8)",
              }}
              data-testid="multimedia-tab-info"
            >
              🖼️ <strong>マルチメディア生成</strong>:
              このタブでは挿絵・電子書籍 (ePub/PDF)・マンガ/ショート動画サムネイルなどの二次創作物 ZIP を一括生成できます。
            </div>
            <AssetPackPanel bookId={selectedBookId} />
          </>
        )}
        {tab === "branches" && (
          <>
            <BranchManagement bookId={selectedBookId} />
          </>
        )}
        {tab === "audit" && (
          <div style={{ padding: "8px 0" }}>
            <ConflictReportPanel
              report={
                auditReport ?? {
                  book_id: selectedBookId || 1,
                  ep_num: currentEpNum,
                  patch_review_id: null,
                  summary: "二層ハイブリッド監査を実行すると、文長リズム・会話文比率・AI定型表現・キャラクター整合性の診断結果が表示されます。",
                  total_count: 0,
                  critical_count: 0,
                  high_count: 0,
                  medium_count: 0,
                  low_count: 0,
                  conflicts: [],
                }
              }
              onRunAudit={handleRunHybridAudit}
              isLoading={isAuditing}
              onApprove={(reviewId, comment) => {
                handleToast("パッチを承認しました", "success");
              }}
              onReject={(reviewId, comment) => {
                handleToast(`指摘を却下しました: ${comment}`, "info");
              }}
              onRevise={(reviewId, proposedContent, comment) => {
                setCurrentChapterText(proposedContent);
                handleToast("修正本文をエディタに反映しました", "success");
              }}
            />
          </div>
        )}
        {tab === "commercial" && (
          <>
            <CommercialPublishPanel
              bookId={selectedBookId}
              onToast={handleToast}
            />
          </>
        )}
      </main>

      {/* 右ペイン: GraphRAG 専属AI編集者サイドバー */}
      {showRightPane ? (
        <aside className="studio-pane">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <h2 style={{ fontSize: "1.05rem", color: "var(--accent-purple)", fontWeight: 700, margin: 0 }}>
                🧠 専属 AI 編集者 (GraphRAG)
              </h2>
              {typeof chapterScore === "number" && (
                <button
                  type="button"
                  onClick={() => setShowQualityDashboard(true)}
                  style={{
                    padding: "2px 8px",
                    borderRadius: "12px",
                    fontSize: "0.75rem",
                    fontWeight: "bold",
                    cursor: "pointer",
                    border: "1px solid var(--border-color)",
                    background: chapterScore >= 70 ? "rgba(34, 197, 94, 0.2)" : "rgba(239, 68, 68, 0.2)",
                    color: chapterScore >= 70 ? "#4ade80" : "#f87171",
                    transition: "all 0.2s",
                  }}
                  title="品質ダッシュボードを開く"
                >
                  📈 Score: {chapterScore.toFixed(1)}
                </button>
              )}
            </div>
            <button
              type="button"
              className="pane-toggle-btn"
              onClick={() => setShowRightPane(false)}
              title="右サイドバーを折りたたむ"
              data-testid="btn-toggle-right-pane"
            >
              ▶
            </button>
          </div>
          <EditorialSidebar
            bookId={selectedBookId}
            currentText={currentChapterText}
            onToast={handleToast}
            onOpenAuditReport={handleOpenAuditReport}
            onRunHybridAudit={handleRunHybridAudit}
          />
        </aside>
      ) : null}

      {showQualityDashboard && selectedBookId && (
        <QualityDashboardModal
          bookId={selectedBookId}
          chapterNumber={currentEpNum}
          onClose={() => setShowQualityDashboard(false)}
        />
      )}
    </div>
    {isWizardActive && (
      <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, pointerEvents: "none", zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center" }}>
        {wizardStep === 1 && (
          <WizardStep
            stepNumber={1}
            totalSteps={6}
            title="コンセプト設定"
            description="まずは作品の方向性を決めましょう。左側のパネルでジャンルを選択し、主人公の名前や性格を入力してください。"
            onNext={() => setWizardStep(2)}
            onSkip={() => setIsWizardActive(false)}
            targetElementId="character-settings-pane"
          />
        )}
        {wizardStep === 2 && (
          <WizardStep
            stepNumber={2}
            totalSteps={6}
            title="プロット構築"
            description="物語の骨組みを作りましょう。エディタ下部の「次なる展開を生成」パネルを使って、物語の構成案を具体化させてください。"
            onNext={() => setWizardStep(3)}
            onSkip={() => setIsWizardActive(false)}
            targetElementId="next-beats-panel"
          />
        )}
        {wizardStep === 3 && (
          <WizardStep
            stepNumber={3}
            totalSteps={6}
            title="初稿執筆"
            description="いよいよ執筆です。プロットを参考に、まずは最初のシーンを書き進めてみましょう。AI推敲ツールバーを使って描写を肉付けすることも可能です。"
            onNext={() => setWizardStep(4)}
            onSkip={() => setIsWizardActive(false)}
            targetElementId="editor-textarea"
          />
        )}
        {wizardStep === 4 && (
          <WizardStep
            stepNumber={4}
            totalSteps={6}
            title="マルチメディア統合"
            description="シーンに画像を追加しましょう。マルチメディアタブに切り替え、画像をアップロードまたはプロンプトから生成してください。生成された画像はエディタ内のマーカーと同期します。"
            onNext={() => setWizardStep(5)}
            onSkip={() => setIsWizardActive(false)}
            targetElementId="studio-tab-multimedia"
          />
        )}
        {wizardStep === 5 && (
          <WizardStep
            stepNumber={5}
            totalSteps={6}
            title="IF分岐と物語の分岐"
            description="物語の分岐構造を作成します。IF分岐ルートタブを使って、選択肢によるストーリーの変化を設計してください。"
            onNext={() => setWizardStep(6)}
            onSkip={() => setIsWizardActive(false)}
            targetElementId="studio-tab-branches"
          />
        )}
        {wizardStep === 6 && (
          <WizardStep
            stepNumber={6}
            totalSteps={6}
            title="AI診断と品質チェック"
            description="最後に、AIによる矛盾診断と品質スコアを確認しましょう。「矛盾診断レポート」タブと品質ダッシュボードを使って、作品の完成度を高めてください。"
            onNext={() => {
              setIsWizardActive(false);
              setWizardStep(0);
              setHasCompletedWizard(true);
              localStorage.setItem("autonovel.wizard_completed", "true");
            }}
            onSkip={() => {
              setIsWizardActive(false);
              // Skip doesn't necessarily mean completed, but we can mark it as such if we want
            }}
            targetElementId="studio-tab-audit"
          />
        )}
      </div>
    )}
    {layoutMode === "zen" && (
      <ZenWritingScreen
        isVisible={true}
        onExit={() => setLayoutMode("studio")}
        focusState={{
          isZenMode: true,
          hideToolbars: true,
          dimBackground: true,
          targetWordCount: 3000,
          currentWordCount: 0,
        }}
        onFocusStateChange={() => {}}
      />
    )}
  </>
);
};

const styles = {
  splitter: {
    width: "4px",
    cursor: "col-resize",
    background: "var(--border-color)",
    transition: "background 0.1s",
    zIndex: 10
  },
  splitterCollapsed: {
    width: "4px",
    cursor: "pointer",
    background: "var(--accent-cyan)",
    opacity: 0.5,
    transition: "opacity 0.2s",
    zIndex: 10
  }
};