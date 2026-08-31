import React from "react";
import { useNovelContext } from "../context/NovelContext";
import { useNovelGeneration } from "../hooks/useNovelGeneration";

interface GeneratePanelProps {
  onGenerated?: (output: string, suggestions: string[]) => void;
  onMessage?: (message: string) => void;
}

export default function GeneratePanel({ onGenerated, onMessage }: GeneratePanelProps) {
  const {
    character,
    setCharacter,
    currentChapterText,
    setCurrentChapterText,
    generationState,
  } = useNovelContext();

  const { startGeneration, cancelGeneration } = useNovelGeneration(
    (out, sug) => {
      onGenerated?.(out, sug);
    },
    (msg) => onMessage?.(msg),
    (errMsg) => onMessage?.(errMsg)
  );

  return (
    <section className="card">
      <h2 style={{ fontSize: "1.2rem", marginBottom: "16px", color: "var(--accent-primary, #a78bfa)" }}>
        ⚙️ 制作設定 & プロンプト
      </h2>

      <div className="form-group">
        <label className="label">作品ジャンル・レーティング</label>
        <select
          className="select"
          value={character.genre}
          onChange={(e) => setCharacter((prev) => ({ ...prev, genre: e.target.value }))}
        >
          <option value="ファンタジー (R15)">ハイファンタジー (R15)</option>
          <option value="ダークファンタジー (R15)">ダークファンタジー (R15)</option>
          <option value="異世界転生 (R15)">異世界転生・バトル (R15)</option>
        </select>
      </div>

      <div className="form-group">
        <label className="label">主人公の名前</label>
        <input
          className="input"
          value={character.name}
          onChange={(e) => setCharacter((prev) => ({ ...prev, name: e.target.value }))}
        />
      </div>

      <div className="form-group">
        <label className="label">性格・特徴</label>
        <input
          className="input"
          value={character.personality}
          onChange={(e) => setCharacter((prev) => ({ ...prev, personality: e.target.value }))}
        />
      </div>

      <div className="form-group">
        <label className="label">特殊能力・スキル</label>
        <input
          className="input"
          value={character.ability}
          onChange={(e) => setCharacter((prev) => ({ ...prev, ability: e.target.value }))}
        />
      </div>

      <div className="form-group">
        <label className="label">執筆対象の冒頭 / 前話プロンプト</label>
        <textarea
          className="textarea"
          rows={4}
          value={currentChapterText}
          onChange={(e) => setCurrentChapterText(e.target.value)}
        />
      </div>

      {generationState.statusText && (
        <div style={{ marginBottom: "12px", fontSize: "0.9rem", color: "var(--text-muted)" }}>
          {generationState.statusText}
        </div>
      )}

      <div style={{ display: "flex", gap: "8px" }}>
        <button
          className="btn btn-primary"
          style={{ flex: 1 }}
          onClick={startGeneration}
          disabled={generationState.isGenerating}
        >
          {generationState.isGenerating ? "🪄 執筆中..." : "🪄 かんたん執筆開始"}
        </button>

        {generationState.isGenerating && (
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => cancelGeneration(generationState.currentTaskId)}
            title="生成タスクを中止します"
          >
            ⏹ 中止
          </button>
        )}
      </div>
    </section>
  );
}
