import React, { useState } from "react";
import { useNovelContext } from "../../context/NovelContext";
import { Editor } from "../editor/Editor";
import { NextBeatsPanel } from "../editor/NextBeatsPanel";
import { EditorialSidebar } from "../editor/EditorialSidebar";
import { ChapterOutlineTree } from "./ChapterOutlineTree";
import { AssetPackPanel } from "../AssetPackPanel";

interface StudioWorkspaceProps {
  onMessage?: (msg: string) => void;
  onOpenGraph?: () => void;
}

type StudioTab = "editor" | "multimedia";

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
  } = useNovelContext();
  const [tab, setTab] = useState<StudioTab>("editor");

  const [showLeftPane, setShowLeftPane] = useState(true);
  const [showRightPane, setShowRightPane] = useState(true);

  const handleToast = (msg: string, type: "success" | "error" | "info") => {
    if (type === "error") {
      onMessage?.(`❌ ${msg}`);
    } else if (type === "success") {
      onMessage?.(`✨ ${msg}`);
    } else {
      onMessage?.(msg);
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
    <div className={gridClass} data-testid="studio-workspace">
      {/* 左ペイン: 作品・登場人物・設定概要 & 章ツリー */}
      {showLeftPane ? (
        <aside className="studio-pane studio-sidebar-left" style={{ gap: "16px", display: "flex", flexDirection: "column" }}>
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

        {tab === "editor" && (
          <>
            <Editor
              content={currentChapterText}
              onChange={setCurrentChapterText}
              genre={character.genre}
              onToast={handleToast}
            />

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
          </>
        )}
        {tab === "multimedia" && <AssetPackPanel bookId={selectedBookId} />}
      </main>

      {/* 右ペイン: GraphRAG 専属AI編集者サイドバー */}
      {showRightPane ? (
        <aside className="studio-pane">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <h2 style={{ fontSize: "1.05rem", color: "var(--accent-purple)", fontWeight: 700, margin: 0 }}>
              🧠 専属 AI 編集者 (GraphRAG)
            </h2>
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
          />
        </aside>
      ) : null}
    </div>
  );
};