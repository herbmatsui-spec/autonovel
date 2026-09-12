import React from "react";

interface LLMConfigPanelProps {
  llmConfig: any;
  setLlmConfig: React.Dispatch<React.SetStateAction<any>>;
  showApiSettings?: boolean;
  setShowApiSettings?: React.Dispatch<React.SetStateAction<boolean>>;
  showApiKey?: boolean;
  setShowApiKey?: React.Dispatch<React.SetStateAction<boolean>>;
  onOpenSettings?: () => void;
}

export default function LLMConfigPanel({
  llmConfig,
  onOpenSettings,
}: LLMConfigPanelProps) {
  // 実効モデルのラベル判定
  const providerLabel =
    llmConfig?.provider && llmConfig.provider !== "default"
      ? llmConfig.provider
      : "サーバー既定";

  const modelLabel =
    llmConfig?.model_writing ||
    llmConfig?.model_name ||
    "自動選択 (執筆: gemma-4-31b-it / プロット: gemini-3.5-flash-lite)";

  return (
    <div
      style={{
        marginBottom: "16px",
        padding: "10px 14px",
        background: "rgba(255, 255, 255, 0.03)",
        border: "1px solid var(--border-color, rgba(255, 255, 255, 0.1))",
        borderRadius: "8px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span style={{ fontSize: "1rem" }}>🤖</span>
        <div>
          <div style={{ fontSize: "0.85rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
            <span>稼働モデル: {modelLabel}</span>
            <span
              style={{
                fontSize: "0.7rem",
                padding: "1px 6px",
                borderRadius: "4px",
                background: llmConfig?.api_key ? "rgba(34, 197, 94, 0.2)" : "rgba(148, 163, 184, 0.15)",
                color: llmConfig?.api_key ? "#4ade80" : "var(--text-muted)",
              }}
            >
              {providerLabel}
            </span>
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
            ※ プロット・執筆・監査・Embeddingの変更はヘッダーの「⚙️ LLM設定」から一元管理できます。
          </div>
        </div>
      </div>

      {onOpenSettings && (
        <button
          type="button"
          className="btn btn-secondary"
          style={{ padding: "4px 10px", fontSize: "0.75rem", whiteSpace: "nowrap" }}
          onClick={onOpenSettings}
        >
          ⚙️ 設定変更
        </button>
      )}
    </div>
  );
}