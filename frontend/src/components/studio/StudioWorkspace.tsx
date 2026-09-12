import React, { useState, useEffect } from "react";
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
import { ConflictReportPanel } from "../editor/ConflictReportPanel";
import { CommercialPublishPanel } from "../commercial/CommercialPublishPanel";
import { QualityDashboardModal } from "./QualityDashboardModal";
import { fetchChapterBookScore } from "../../api/quality";

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
    isWizardActive,
    setIsWizardActive,
    wizardStep,
    setWizardStep,
  } = useNovelContext();

  const [tab, setTab] = useState<StudioTab>(() => {
    if (typeof window === "undefined") return "editor";
    try {
      const saved = window.localStorage.getItem("autonovel.studioTab");
      if (saved === "editor" || saved === "multimedia" || saved === "branches" || saved === "audit" || saved === "commercial") return saved;
    } catch {
      // localStorage が使えない環境では無視
    }
    return "editor";
  });

  useEffect(() => {
    try {
      window.localStorage.setItem("autonovel.studioTab", tab);
    } catch {
      // ignore storage error
    }
  }, [tab]);

  const [showLeftPane, setShowLeftPane] = useState(true);
  const [showRightPane, setShowRightPane] = useState(true);
  const [showStyleComparison, setShowStyleComparison] = useState(false);
  const [showBookShowcase, setShowBookShowcase] = useState(false);
  const [showQualityDashboard, setShowQualityDashboard] = useState(false);
  const [chapterScore, setChapterScore] = useState<number | null>(null);
  const [budgetInfo, setBudgetInfo] = useState<BudgetInfo | null>(null);
  const [currentSceneName, setCurrentSceneName] = useState<string | null>(null);
  const [currentImageUrl, setCurrentImageUrl] = useState<string | undefined>(undefined);

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

  const handleOpenAuditReport = () => {
    setTab("audit");
    onMessage?.("🧠 矛盾診断レポートタブに切り替えました", "info");
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
      <div className={gridClass} data-testid="studio-workspace">
      {/* 左ペイン: 作品・登場人物・設定概要 & 章ツリー */}
      {showLeftPane ? (
        <aside id="character-settings-pane" className="studio-pane studio-sidebar-left" style={{ gap: "16px", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ fontSize: "1.05rem", color: "var(--accent-cyan)", fontWeight: 700 }}>
              📖 設定 & キャラクター
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

          <div className="form-group" style={{ marginBottom: "8px" }}>
            <label className="label">主人公名</label>
            <input
              className="input"
              value={character.name}
              onChange={(e) => setCharacter((prev) => ({ ...prev, name: e.target.value }))}
            />
          </div>

          <div className="form-group" style={{ marginBottom: "8px" }}>
            <label className="label">性格・特徴</label>
            <input
              className="input"
              value={character.personality}
              onChange={(e) => setCharacter((prev) => ({ ...prev, personality: e.target.value }))}
            />
          </div>

          <div className="form-group" style={{ marginBottom: "8px" }}>
            <label className="label">特殊能力・スキル</label>
            <input
              className="input"
              value={character.ability}
              onChange={(e) => setCharacter((prev) => ({ ...prev, ability: e.target.value }))}
            />
          </div>

          <div className="form-group" style={{ marginBottom: "14px" }}>
            <label className="label">ジャンル</label>
            <select
              className="select"
              value={character.genre}
              onChange={(e) => setCharacter((prev) => ({ ...prev, genre: e.target.value }))}
            >
              <option value="ハイファンタジー (R15)">ハイファンタジー (R15)</option>
              <option value="ダークファンタジー (R15)">ダークファンタジー (R15)</option>
              <option value="異世界転生・バトル (R15)">異世界転生・バトル (R15)</option>
            </select>
          </div>

          {/* 章・プロットナビゲーター */}
          <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "14px" }}>
            <ChapterOutlineTree />
          </div>

          <div style={{ marginTop: "auto", padding: "10px", background: "rgba(0,0,0,0.2)", borderRadius: "8px", fontSize: "0.75rem", color: "var(--text-muted)", lineHeight: "1.4" }}>
            💡 <strong>Studio モードのヒント</strong><br />
            ・左下で章を切り替えて複数話を執筆可能<br />
            ・本文のテキスト選択で五感推敲ツールバー出現<br />
            ・右側 AI 編集者に設定質問＆矛盾自動修正
          </div>
        </aside>
      ) : null}

      <main className="studio-pane" style={{ minHeight: "600px" }}>
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
            💰 ${budgetInfo.current_cost_usd.toFixed(2)} / ${budgetInfo.budget_usd.toFixed(2)}
          </div>
        )}
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
          <>
            <div style={{ padding: '20px', textAlign: 'center' }}>
              <h2>🧠 矛盾診断レポート</h2>
              <p>矛盾診断レポートを表示するには、まず矛盾診断を実行してください。</p>
            </div>
          </>
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
              {chapterScore !== null && (
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
            totalSteps={4}
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
            totalSteps={4}
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
            totalSteps={4}
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
            totalSteps={4}
            title="AI診断"
            description="最後に、AIによる矛盾診断を実行しましょう。「矛盾診断レポート」タブに切り替え、診断ボタンを押して設定の整合性をチェックしてください。"
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
  </>
);
};