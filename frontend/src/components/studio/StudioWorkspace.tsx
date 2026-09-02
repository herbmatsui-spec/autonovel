import React, { useState } from "react";
import { useNovelContext } from "../../context/NovelContext";
import { Editor } from "../editor/Editor";
import { NextBeatsPanel } from "../editor/NextBeatsPanel";
import { EditorialSidebar } from "../editor/EditorialSidebar";
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

  const handleToast = (msg: string, type: "success" | "error" | "info") => {
    if (type === "error") {
      onMessage?.(`❌ ${msg}`);
    } else if (type === "success") {
      onMessage?.(`✨ ${msg}`);
    } else {
      onMessage?.(msg);
    }
  };

  return (
    <div className="studio-grid" data-testid="studio-workspace">
      <aside className="studio-pane studio-sidebar-left" style={{ gap: "16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ fontSize: "1.05rem", color: "var(--accent-cyan)", fontWeight: 700 }}>
            📖 設定 & キャラクター
          </h2>
          {onOpenGraph && (
            <button
              type="button"
              className="inline-ai-btn"
              onClick={onOpenGraph}
              title="GraphRAG 相関図を開く"
              data-testid="btn-open-graph-studio"
            >
              📊 相関図
            </button>
          )}
        </div>

        <div className="form-group" style={{ marginBottom: "12px" }}>
          <label className="label">主人公名</label>
          <input
            className="input"
            value={character.name}
            onChange={(e) => setCharacter((prev) => ({ ...prev, name: e.target.value }))}
          />
        </div>

        <div className="form-group" style={{ marginBottom: "12px" }}>
          <label className="label">性格・特徴</label>
          <input
            className="input"
            value={character.personality}
            onChange={(e) => setCharacter((prev) => ({ ...prev, personality: e.target.value }))}
          />
        </div>

        <div className="form-group" style={{ marginBottom: "12px" }}>
          <label className="label">特殊能力・スキル</label>
          <input
            className="input"
            value={character.ability}
            onChange={(e) => setCharacter((prev) => ({ ...prev, ability: e.target.value }))}
          />
        </div>

        <div className="form-group" style={{ marginBottom: "12px" }}>
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

        <div style={{ marginTop: "auto", display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            type="button"
            className={tab === "editor" ? "inline-ai-btn active" : "inline-ai-btn"}
            onClick={() => setTab("editor")}
            data-testid="tab-editor"
          >
            ✍️ Editor
          </button>
          <button
            type="button"
            className={tab === "multimedia" ? "inline-ai-btn active" : "inline-ai-btn"}
            onClick={() => setTab("multimedia")}
            data-testid="tab-multimedia"
          >
            🎬 Multimedia
          </button>
        </div>

        <div style={{ marginTop: "auto", padding: "12px", background: "rgba(0,0,0,0.2)", borderRadius: "8px", fontSize: "0.8rem", color: "var(--text-muted)", lineHeight: "1.5" }}>
          💡 <strong>Studio モードのヒント</strong><br />
          ・本文のテキストを選択すると五感推敲ツールバーが出現<br />
          ・下部の Next Beats から 3 つの展開を選択可能<br />
          ・右側の AI 編集者に設定を何でも質問できます<br />
          ・Multimedia タブから IF ルート・電子書籍・メディアミックスを生成
        </div>
      </aside>

      <main className="studio-pane" style={{ minHeight: "600px" }}>
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

      <aside className="studio-pane">
        <h2 style={{ fontSize: "1.05rem", color: "var(--accent-purple)", fontWeight: 700, marginBottom: "12px" }}>
          🧠 専属 AI 編集者 (GraphRAG)
        </h2>
        <EditorialSidebar
          bookId={selectedBookId}
          currentText={currentChapterText}
          onToast={handleToast}
        />
      </aside>
    </div>
  );
};
