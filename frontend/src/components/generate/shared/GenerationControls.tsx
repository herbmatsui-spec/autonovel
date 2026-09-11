import React from "react";

interface GenerationControlsProps {
  isStreaming: boolean;
  isPaused: boolean;
  isBusy: boolean;
  generationState: { isGenerating: boolean; currentTaskId: string | null };
  startStreaming: () => void;
  cancelStreaming: () => void;
  resumeStreaming: () => void;
  pauseStreaming: () => void;
  startGeneration: () => void;
  cancelGeneration: (taskId: string | null) => void;
}

export default function GenerationControls({
  isStreaming,
  isPaused,
  isBusy,
  generationState,
  startStreaming,
  cancelStreaming,
  resumeStreaming,
  pauseStreaming,
  startGeneration,
  cancelGeneration,
}: GenerationControlsProps) {
  return (
    <div style={{ display: "flex", gap: "8px" }}>
      <button
        className="btn btn-primary"
        style={{ flex: 1.2, backgroundColor: "var(--accent-cyan)", borderColor: "var(--accent-cyan)", color: "#000", fontWeight: 700 }}
        onClick={startStreaming}
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
  );
}