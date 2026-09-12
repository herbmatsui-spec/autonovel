import React from "react";
import type { CharacterParams as Character } from "../../types";
import type { GenerationState } from "../../types";

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
  onRunGacha?: () => void;
  onRunDigest?: () => void;
  isGachaLoading?: boolean;
  isDigestLoading?: boolean;
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
          onChange={(e) => setCharacter((prev: Character) => ({ ...prev, genre: e.target.value }))}
          title="Studioモードでは詳細なジャンル分析とトレンドデータを参照できます"
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
          onChange={(e) => setCharacter((prev: Character) => ({ ...prev, name: e.target.value }))}
          title="Studioモードではキャラクターの詳細プロファイルと関係性マッピングが可能です"
        />
      </div>

      <div className="form-group">
        <label className="label">性格・特徴</label>
        <input
          className="input"
          value={character.personality}
          onChange={(e) => setCharacter((prev: Character) => ({ ...prev, personality: e.target.value }))}
          title="StudioモードではAIによる性格分析と一貫性チェックが行われます"
        />
      </div>

      <div className="form-group">
        <label className="label">特殊能力・スキル</label>
        <input
          className="input"
          value={character.ability}
          onChange={(e) => setCharacter((prev: Character) => ({ ...prev, ability: e.target.value }))}
          title="Studioモードでは能力バランス分析とプロットへの組み込み提案が行われます"
        />
      </div>

      <div className="form-group">
        <label className="label">執筆対象の冒頭 / 前話プロンプト</label>
        <textarea
          className="textarea"
          rows={4}
          value={currentChapterText}
          onChange={(e) => setCurrentChapterText(e.target.value)}
          title="Studioモードではリアルタイム品質スコア表示、シーン別プレビュー、AIによる詳細な推敲サポートが利用できます"
        />
      </div>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        <button
          className="btn btn-primary"
          style={{ flex: 1.2, backgroundColor: "var(--accent-cyan)", borderColor: "var(--accent-cyan)", color: "#000", fontWeight: 700, minWidth: "120px" }}
          onClick={() => startStreaming()}
          disabled={isBusy}
          title="Studioモードでは、プロットベースのAI共同執筆とブランチングが利用できます"
        >
          {isStreaming ? "⚡ ストリーミング執筆中..." : "⚡ リアルタイム速筆 (SSE)"}
        </button>

        <button
          className="btn btn-secondary"
          style={{ flex: 1, minWidth: "120px" }}
          onClick={startGeneration}
          disabled={isBusy}
          title="Studioモードでは、詳細なアウトライン生成と Beat シート編集が利用できます"
        >
          {generationState.isGenerating ? "🪄 執筆中..." : "🪄 かんたん執筆開始"}
        </button>

        {generationState.isGenerating && !isStreaming && (
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => cancelGeneration(generationState.currentTaskId)}
            title="Studioモードでは、生成の一時停止と詳細なログ確認が利用できます"
          >
            ⏹ 中止
          </button>
        )}
        
        {/* Studio機能チラ見せボタン */}
        <button
          type="button"
          className="btn btn-outline-secondary"
          style={{ flex: 1, minWidth: "120px", fontSize: "0.9rem" }}
          onClick={() => {
            // Studio機能のチラ見せとして、マルチメディアプレビューのサンプルを表示
            alert("Studio機能のプレビュー:\n・シーン別マルチメディアプレビュー\n・AI診断・品質スコア詳細表示\n・プロットビジュアライザー\n・キャラ設定詳細編集\n\n※実際の機能はStudioモードでご利用ください");
          }}
          disabled={isBusy}
        >
          👀 Studio機能チラ見せ
        </button>
        <button
          className="btn btn-outline-primary"
          style={{ flex: 1, minWidth: "120px", borderColor: "var(--accent-cyan)", color: "var(--accent-cyan)" }}
          onClick={onRunGacha}
          disabled={isBusy || isGachaLoading}
          title="3つの物語案をランダムに生成します"
        >
          {isGachaLoading ? "🎲 生成中..." : "🎲 企画ガチャ"}
        </button>
        <button
          className="btn btn-outline-secondary"
          style={{ flex: 1, minWidth: "120px" }}
          onClick={onRunDigest}
          disabled={isBusy || isDigestLoading}
          title="選択したプランからダイジェストを生成します"
        >
          {isDigestLoading ? "📖 解析中..." : "📖 ダイジェスト"}
        </button>
      </div>
    </div>
  );
}