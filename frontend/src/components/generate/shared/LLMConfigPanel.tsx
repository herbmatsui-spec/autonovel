import React from "react";

interface LLMConfigPanelProps {
  llmConfig: any;
  setLlmConfig: React.Dispatch<React.SetStateAction<any>>;
  showApiSettings: boolean;
  setShowApiSettings: React.Dispatch<React.SetStateAction<boolean>>;
  showApiKey: boolean;
  setShowApiKey: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function LLMConfigPanel({
  llmConfig,
  setLlmConfig,
  showApiSettings,
  setShowApiSettings,
  showApiKey,
  setShowApiKey,
}: LLMConfigPanelProps) {
  return (
    <div
      style={{
        marginBottom: "16px",
        padding: "12px 14px",
        background: "rgba(255, 255, 255, 0.03)",
        border: "1px solid var(--border-color, rgba(255, 255, 255, 0.1))",
        borderRadius: "8px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: "pointer",
        }}
        onClick={() => setShowApiSettings((prev) => !prev)}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "0.95rem", fontWeight: 600 }}>
            🔑 AIモデル & API接続設定
          </span>
          {llmConfig?.api_key ? (
            <span style={{ fontSize: "0.75rem", padding: "2px 6px", borderRadius: "4px", background: "rgba(34, 197, 94, 0.2)", color: "#4ade80", border: "1px solid rgba(34, 197, 94, 0.4)" }}>
              🔒 カスタムAPI設定中 ({llmConfig.provider || "gemini"})
            </span>
          ) : (
            <span style={{ fontSize: "0.75rem", padding: "2px 6px", borderRadius: "4px", background: "rgba(148, 163, 184, 0.15)", color: "var(--text-muted)" }}>
              ⚡ サーバー既定 / オプトイン
            </span>
          )}
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          style={{ padding: "2px 8px", fontSize: "0.75rem" }}
        >
          {showApiSettings ? "閉じる ▲" : "設定を開く ▼"}
        </button>
      </div>

      {showApiSettings && (
        <div style={{ marginTop: "14px", borderTop: "1px solid rgba(255, 255, 255, 0.08)", paddingTop: "12px" }}>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "12px", lineHeight: 1.4 }}>
            ※ ここにAPIキーを入力すると、サーバーの環境変数（.env）に依存せずブラウザから直接指定したAPIを使用できます（キーはブラウザにのみ保存されます）。
          </p>

          <div className="form-group" style={{ marginBottom: "10px" }}>
            <label className="label" style={{ fontSize: "0.85rem" }}>プロバイダ選択</label>
            <select
              className="select"
              value={llmConfig?.provider || "default"}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "default") {
                  setLlmConfig({});
                } else if (val === "gemini") {
                  setLlmConfig((prev: any) => ({ ...prev, provider: "gemini", model_name: prev.model_name || "gemini-2.5-flash" }));
                } else if (val === "openai") {
                  setLlmConfig((prev: any) => ({ ...prev, provider: "openai", model_name: prev.model_name || "gpt-4o-mini", base_url: undefined }));
                } else if (val === "openai_compatible") {
                  setLlmConfig((prev: any) => ({ ...prev, provider: "openai", model_name: prev.model_name || "deepseek-chat", base_url: prev.base_url || "https://api.deepseek.com/v1" }));
                }
              }}
            >
              <option value="default">⚡ サーバー既定（.env / 自動フォールバック）</option>
              <option value="gemini">🔷 Google Gemini (推奨: 高速・長文特化)</option>
              <option value="openai">🟢 OpenAI (GPT-4o / GPT-4o-mini)</option>
              <option value="openai_compatible">🟣 OpenAI互換 / ローカル (DeepSeek, Ollama, vLLM等)</option>
            </select>
          </div>

          {llmConfig?.provider && llmConfig.provider !== "default" && (
            <>
              <div className="form-group" style={{ marginBottom: "10px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label className="label" style={{ fontSize: "0.85rem", margin: 0 }}>
                    {llmConfig.provider === "gemini" ? "Google Gemini APIキー" : "APIキー"}
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowApiKey((prev) => !prev)}
                    style={{ background: "none", border: "none", color: "var(--accent-cyan)", fontSize: "0.75rem", cursor: "pointer" }}
                  >
                    {showApiKey ? "隠す 👁️" : "表示 👁️"}
                  </button>
                </div>
                <input
                  type={showApiKey ? "text" : "password"}
                  className="input"
                  placeholder={llmConfig.provider === "gemini" ? "AIzaSy..." : "sk-..."}
                  value={llmConfig.api_key || ""}
                  onChange={(e) => setLlmConfig((prev: any) => ({ ...prev, api_key: e.target.value }))}
                />
              </div>

              {llmConfig.base_url !== undefined && (
                <div className="form-group" style={{ marginBottom: "10px" }}>
                  <label className="label" style={{ fontSize: "0.85rem" }}>ベースURL (OpenAI互換エンドポイント)</label>
                  <input
                    type="text"
                    className="input"
                    placeholder="https://api.deepseek.com/v1 または http://localhost:11434/v1"
                    value={llmConfig.base_url || ""}
                    onChange={(e) => setLlmConfig((prev: any) => ({ ...prev, base_url: e.target.value }))}
                  />
                </div>
              )}

              <div className="form-group" style={{ marginBottom: "10px" }}>
                <label className="label" style={{ fontSize: "0.85rem" }}>モデル名</label>
                <input
                  type="text"
                  className="input"
                  placeholder={llmConfig.provider === "gemini" ? "gemini-2.5-flash" : "gpt-4o-mini"}
                  value={llmConfig.model_name || ""}
                  onChange={(e) => setLlmConfig((prev: any) => ({ ...prev, model_name: e.target.value }))}
                />
                <div style={{ display: "flex", gap: "6px", marginTop: "4px", flexWrap: "wrap" }}>
                  {llmConfig.provider === "gemini" ? (
                    ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"].map((m) => (
                      <button
                        key={m}
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: "2px 6px", fontSize: "0.7rem" }}
                        onClick={() => setLlmConfig((prev: any) => ({ ...prev, model_name: m }))}
                      >
                        {m}
                      </button>
                    ))
                  ) : (
                    ["gpt-4o-mini", "gpt-4o", "deepseek-chat", "llama3.1"].map((m) => (
                      <button
                        key={m}
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: "2px 6px", fontSize: "0.7rem" }}
                        onClick={() => setLlmConfig((prev: any) => ({ ...prev, model_name: m }))}
                      >
                        {m}
                      </button>
                    ))
                  )}
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: "4px 10px", fontSize: "0.75rem", color: "var(--accent-danger, #ef4444)" }}
                  onClick={() => {
                    setLlmConfig({});
                  }}
                >
                  🗑️ 設定をリセット
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}