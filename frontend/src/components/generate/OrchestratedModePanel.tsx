import React from "react";
import type { CharacterParams as Character } from "../../types";
import type { GenerationState } from "../../types";

interface OrchestratedModePanelProps {
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
  agentProgress: Record<string, { status: string; payload?: any }>;
  output: string;
  startUnified: () => void;
  cancelUnified: () => void;
  isActive: boolean;
  selectedBookId: number | null;
  onMessage?: (msg: string) => void;
}

export default function OrchestratedModePanel(props: OrchestratedModePanelProps) {
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
    agentProgress,
    output,
    startUnified,
    cancelUnified,
    isActive,
    selectedBookId,
    onMessage,
  } = props;

  return (
    <div>
      <div className="form-group">
        <label className="label">オーケストレーションモード設定</label>
        <div>
          <p className="label">
            8つの特化エージェントが協調して高品質な小説を生成します。<br />
            エージェント: Planning → Plot → Bible → ContextBuilder → Writing → Audit → Illustration → Marketing
          </p>
        </div>
      </div>

      <div className="form-group">
        <label className="label">作品基本情報</label>
        <div>
          <div style={{ display: "flex", marginBottom: "8px" }}>
            <span className="label">タイトル:</span>
            <input
              type="text"
              className="input"
              value={character.name || "主人公の冒険"}
              onChange={(e) => setCharacter((prev: Character) => ({ ...prev, name: e.target.value }))}
            />
          </div>
          <div style={{ display: "flex", marginBottom: "8px" }}>
            <span className="label">ジャンル:</span>
            <select
              className="select"
              value={character.genre}
              onChange={(e) => setCharacter((prev: Character) => ({ ...prev, genre: e.target.value }))}
            >
              <option value="fan">ファンタジー</option>
              <option value="sf">SF</option>
              <option value="romance">恋愛</option>
              <option value="mystery">ミステリー</option>
              <option value="horror">ホラー</option>
              <option value="other">その他</option>
            </select>
          </div>
          <div style={{ display: "flex", marginBottom: "8px" }}>
            <span className="label">目標話数:</span>
            <input
              type="number"
              className="input"
              min={1}
              max={100}
              value={targetEpisodes || 10}
              onChange={(e) => setTargetEpisodes(Number(e.target.value))}
            />
          </div>
        </div>
      </div>

      <div className="form-group">
        <label className="label">エージェント進捗状況</label>
        <div>
          {Object.keys(agentProgress).map(agent => (
            <div key={agent} style={{ marginBottom: "4px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>
                {agent === "planning" && "🎯 Planning"} ||
                {agent === "plot" && "📖 Plot"} ||
                {agent === "bible" && "📚 Bible"} ||
                {agent === "context_builder" && "🏗️ ContextBuilder"} ||
                {agent === "writing" && "✍️ Writing"} ||
                {agent === "enrichment" && "🌟 Enrichment"} ||
                {agent === "audit" && "🔍 Audit"} ||
                {agent === "illustration" && "🎨 Illustration"} ||
                {agent === "marketing" && "📢 Marketing"}
              </span>
              <span>
                {agentProgress[agent]?.status === "pending" && "⏳ 待機中"} ||
                {agentProgress[agent]?.status === "running" && "🔄 実行中"} ||
                {agentProgress[agent]?.status === "completed" && "✅ 完了"} ||
                {agentProgress[agent]?.status === "failed" && "❌ 失敗"}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="form-group">
        <label className="label">生成結果</label>
        <div>
          {output && (
            <div>
              <h3>生成されたテキスト:</h3>
              <textarea
                className="textarea"
                rows={10}
                readOnly
                value={output}
              />
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: "8px" }}>
        <button
          className="btn btn-primary"
          onClick={() => startUnified()}
          disabled={isActive || isBusy}
        >
          {isActive ? "実行中..." : "🚀 オーケストレーション開始"}
        </button>
        <button
          className="btn btn-danger"
          onClick={cancelUnified}
          disabled={!isActive}
        >
          ⏹ キャンセル
        </button>
      </div>
    </div>
  );
}