import React from "react";
import type { Character } from "../types/easyMode";
import type { GenerationState } from "../hooks/useNovelGeneration";

interface SimpleModePanelProps {
  character: Character;
  setCharacter: React.Dispatch<React.SetStateAction<Character>>;
  llmConfig: any;
  setLlmConfig: React.Dispatch<React.SetStateAction<any>>;
  selectedStyleId: string;
  customStyleProfile: any;
  showStyleModal: boolean;
  setShowStyleModal: React.Dispatch<React.SetStateAction<boolean>>;
  showApiSettings: boolean;
  setShowApiSettings: React.Dispatch<React.SetStateAction<boolean>>;
  showApiKey: boolean;
  setShowApiKey: React.Dispatch<React.SetStateAction<boolean>>;
  yonkomaEnabled: boolean;
  setYonkomaEnabled: React.Dispatch<React.SetStateAction<boolean>>;
  generationState: GenerationState;
  startGeneration: () => void;
  cancelGeneration: (taskId: string | null) => void;
  isStreaming: boolean;
  startStreaming: () => void;
  cancelStreaming: () => void;
  isPaused: boolean;
  resumeStreaming: () => void;
  pauseStreaming: () => void;
  streamOutput: string;
  isBusy: boolean;
  targetEpisodes: number;
  setTargetEpisodes: React.Dispatch<React.SetStateAction<number>>;
  contentLengthLimit: number;
  setContentLengthLimit: React.Dispatch<React.SetStateAction<number>>;
  currentChapterText: string;
  setCurrentChapterText: React.Dispatch<React.SetStateAction<string>>;
  onMessage?: (msg: string) => void;
}

export default function SimpleModePanel(props: SimpleModePanelProps) {
  const {
    character,
    setCharacter,
    llmConfig,
    setLlmConfig,
    selectedStyleId,
    customStyleProfile,
    showStyleModal,
    setShowStyleModal,
    showApiSettings,
    setShowApiSettings,
    showApiKey,
    setShowApiKey,
    yonkomaEnabled,
    setYonkomaEnabled,
    generationState,
    startGeneration,
    cancelGeneration,
    isStreaming,
    startStreaming,
    cancelStreaming,
    isPaused,
    resumeStreaming,
    pauseStreaming,
    streamOutput,
    isBusy,
    targetEpisodes,
    setTargetEpisodes,
    contentLengthLimit,
    setContentLengthLimit,
    currentChapterText,
    setCurrentChapterText,
    onMessage,
  } = props;

  return (
    <div>
      <div className="form-group">
        <label className="label">作品ジャンル・レーティング</label>
        <select
          className="select"
          value={character.genre}
          onChange={(e) => setCharacter((prev) => ({ ...prev, genre: e.target.value }))}
        >
          <option value="fan">ファンタジー</option>
          <option value="sf">SF</option>
          <option value="romance">恋愛</option>
          <option value="mystery">ミステリー</option>
          <option value="horror">ホラー</option>
          <option value="other">その他</option>
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

      <div style={{ display: "flex", gap: "8px" }}>
        <button
          className="btn btn-primary"
          style={{ flex: 1.2, backgroundColor: "var(--accent-cyan)", borderColor: "var(--accent-cyan)", color: "#000", fontWeight: 700 }}
          onClick={() => startStreaming()}
          disabled={isBusy}
        >
          {isStreaming ? "⚡ ストリーミング執筆中..." : "⚡ リアルタイム速筆 (SSE)"}
        </button>

        <button
          className="btn btn-secondary"
          style={{ flex: 1 }}
          onClick={startGeneration}
          disabled={isBusy}
        >
          {generationState.isGenerating ? "🪄 執筆中..." : "🪄 かんたん執筆開始"}
        </button>

        {generationState.isGenerating && !isStreaming && (
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => cancelGeneration(generationState.currentTaskId)}
          >
            ⏹ 中止
          </button>
        )}
      </div>
    </div>
  );
}