import React from "react";
import { useNovelContext } from "../context/NovelContext";

interface ConfigPanelProps {
  onClose: () => void;
}

export default function ConfigPanel({ onClose }: ConfigPanelProps) {
  const {
    llmConfig,
    setLlmConfig,
  } = useNovelContext();

  const [showApiKey, setShowApiKey] = React.useState(false);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <h2 style={{ margin: 0, fontSize: "1.2rem", color: "var(--accent-primary, #a78bfa)" }}>
          ⚙️ LLM設定
        </h2>
        <button
          type="button"
          style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}
          onClick={onClose}
        >
          ✕
        </button>
      </div>
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
              setLlmConfig((prev) => ({ ...prev, provider: "gemini", model_name: prev.model_name || "gemini-2.5-flash" }));
            } else if (val === "openai") {
              setLlmConfig((prev) => {
                const { base_url, ...rest } = prev;
                return { ...rest, provider: "openai", model_name: prev.model_name || "gpt-4o-mini" };
              });
            } else if (val === "openai_compatible") {
              setLlmConfig((prev) => ({ ...prev, provider: "openai", model_name: prev.model_name || "deepseek-chat", base_url: prev.base_url || "https://api.deepseek.com/v1" }));
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
              onChange={(e) => setLlmConfig((prev) => ({ ...prev, api_key: e.target.value }))}
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
                onChange={(e) => setLlmConfig((prev) => ({ ...prev, base_url: e.target.value }))}
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
              onChange={(e) => setLlmConfig((prev) => ({ ...prev, model_name: e.target.value }))}
            />
            <div style={{ display: "flex", gap: "6px", marginTop: "4px", flexWrap: "wrap" }}>
              {llmConfig.provider === "gemini" ? (
                ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"].map((m) => (
                  <button
                    key={m}
                    type="button"
                    className="btn btn-secondary"
                    style={{ padding: "2px 6px", fontSize: "0.7rem" }}
                    onClick={() => setLlmConfig((prev) => ({ ...prev, model_name: m }))}
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
                    onClick={() => setLlmConfig((prev) => ({ ...prev, model_name: m }))}
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
              style={{
                padding: "6px 12px",
                borderRadius: "8px",
                backgroundColor: "var(--accent-danger, #ef4444)",
                color: "white",
                border: "none",
                cursor: "pointer",
                fontSize: "0.85rem",
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
              onClick={() => {
                setLlmConfig({});
                // Note: In a real implementation, we might want to show a toast message here
                // For now, we'll just reset the config
              }}
            >
              🗑️ 設定をリセット
            </button>
          </div>
        </>
      )}

      <div style={{ marginTop: "20px", paddingTop: "15px", borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
            設定はブラウザのローカルストレージに保存されます
          </span>
          <button
            type="button"
            className="btn btn-primary"
            style={{
              padding: "6px 12px",
              borderRadius: "8px",
              backgroundColor: "var(--accent-cyan, #06b6d4)",
              color: "white",
              border: "none",
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: 500,
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
            onClick={onClose}
          >
            閉じる
          </button>
        </div>
      </div>
    </div>
  );
}