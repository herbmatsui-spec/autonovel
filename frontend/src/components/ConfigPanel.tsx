import React, { useState, useEffect } from "react";
import { useNovelContext } from "../context/NovelContext";
import { fetchServerModelInfo, ServerModelInfo } from "../api/system";

interface ConfigPanelProps {
  onClose: () => void;
}

export default function ConfigPanel({ onClose }: ConfigPanelProps) {
  const {
    llmConfig,
    setLlmConfig,
  } = useNovelContext();

  const [showApiKey, setShowApiKey] = useState(false);
  const [activeTab, setActiveTab] = useState<"summary" | "basic" | "advanced">("basic");
  const [serverInfo, setServerInfo] = useState<ServerModelInfo | null>(null);
  const [isLoadingServerInfo, setIsLoadingServerInfo] = useState(false);

  useEffect(() => {
    let mounted = true;
    setIsLoadingServerInfo(true);
    fetchServerModelInfo().then((info) => {
      if (mounted) {
        setServerInfo(info);
        setIsLoadingServerInfo(false);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  // 実効モデルの計算（ユーザー個別指定 > 全体指定 > サーバー既定）
  const effectivePlanning =
    llmConfig?.model_planning ||
    llmConfig?.model_name ||
    serverInfo?.server_defaults?.planning ||
    "gemini-3.5-flash-lite";

  const effectiveWriting =
    llmConfig?.model_writing ||
    llmConfig?.model_name ||
    serverInfo?.server_defaults?.writing ||
    "gemma-4-31b-it";

  const effectiveAudit =
    llmConfig?.model_audit ||
    llmConfig?.model_name ||
    serverInfo?.server_defaults?.audit ||
    "gemini-3.5-flash-lite";

  const effectiveEmbedding =
    llmConfig?.model_embedding ||
    serverInfo?.server_defaults?.embedding ||
    "text-embedding-3-small";

  return (
    <div style={{ color: "var(--text-main, #f3f4f6)" }}>
      {/* タイトルバー */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "1.3rem" }}>⚙️</span>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.15rem", color: "var(--accent-primary, #a78bfa)", fontWeight: 700 }}>
              AIモデル & API接続設定
            </h2>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted, #9ca3af)", marginTop: "2px" }}>
              プロット作成・本文執筆・監査・検索モデルの一元管理
            </div>
          </div>
        </div>
        <button
          type="button"
          style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}
          onClick={onClose}
          aria-label="閉じる"
        >
          ✕
        </button>
      </div>

      {/* 現在の稼働モデル概要ステータスカード */}
      <div
        style={{
          background: "rgba(167, 139, 250, 0.08)",
          border: "1px solid rgba(167, 139, 250, 0.25)",
          borderRadius: "8px",
          padding: "10px 14px",
          marginBottom: "16px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
          <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--accent-primary, #a78bfa)" }}>
            🤖 現在有効なモデル構成
          </span>
          <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
            {llmConfig?.provider && llmConfig.provider !== "default"
              ? `カスタム (${llmConfig.provider})`
              : "⚡ サーバー既定"}
          </span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", fontSize: "0.75rem" }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ color: "var(--text-muted)" }}>📝 プロット・構成:</span>
            <span style={{ fontWeight: 600, color: "#38bdf8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {effectivePlanning}
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ color: "var(--text-muted)" }}>✍️ 本文執筆:</span>
            <span style={{ fontWeight: 600, color: "#4ade80", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {effectiveWriting}
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ color: "var(--text-muted)" }}>🔍 校正・監査:</span>
            <span style={{ fontWeight: 600, color: "#facc15", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {effectiveAudit}
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ color: "var(--text-muted)" }}>🧠 埋め込み (RAG):</span>
            <span style={{ fontWeight: 600, color: "#c084fc", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {effectiveEmbedding}
            </span>
          </div>
        </div>
      </div>

      {/* タブナビゲーション */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid rgba(255, 255, 255, 0.1)", marginBottom: "14px", paddingBottom: "6px" }}>
        <button
          type="button"
          onClick={() => setActiveTab("basic")}
          style={{
            background: "none",
            border: "none",
            borderBottom: activeTab === "basic" ? "2px solid var(--accent-cyan, #06b6d4)" : "none",
            color: activeTab === "basic" ? "var(--accent-cyan, #06b6d4)" : "var(--text-muted)",
            fontWeight: activeTab === "basic" ? 600 : 400,
            padding: "4px 12px",
            fontSize: "0.85rem",
            cursor: "pointer",
          }}
        >
          簡易設定 (全体)
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("advanced")}
          style={{
            background: "none",
            border: "none",
            borderBottom: activeTab === "advanced" ? "2px solid var(--accent-cyan, #06b6d4)" : "none",
            color: activeTab === "advanced" ? "var(--accent-cyan, #06b6d4)" : "var(--text-muted)",
            fontWeight: activeTab === "advanced" ? 600 : 400,
            padding: "4px 12px",
            fontSize: "0.85rem",
            cursor: "pointer",
          }}
        >
          詳細設定 (用途別指定)
        </button>
      </div>

      {/* プロバイダ選択（共通） */}
      <div className="form-group" style={{ marginBottom: "12px" }}>
        <label className="label" style={{ fontSize: "0.85rem", fontWeight: 600 }}>プロバイダ選択</label>
        <select
          className="select"
          style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", fontSize: "0.85rem" }}
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
              setLlmConfig((prev) => ({
                ...prev,
                provider: "openai",
                model_name: prev.model_name || "deepseek-chat",
                base_url: prev.base_url || "https://api.deepseek.com/v1",
              }));
            }
          }}
        >
          <option value="default">⚡ サーバー既定（.env / 自動フォールバック）</option>
          <option value="gemini">🔷 Google Gemini (推奨: 高速・長文特化)</option>
          <option value="openai">🟢 OpenAI (GPT-4o / GPT-4o-mini)</option>
          <option value="openai_compatible">🟣 OpenAI互換 / ローカル (DeepSeek, Ollama, vLLM等)</option>
        </select>
      </div>

      {/* APIキー入力（プロバイダ指定時） */}
      {llmConfig?.provider && llmConfig.provider !== "default" && (
        <div className="form-group" style={{ marginBottom: "12px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <label className="label" style={{ fontSize: "0.85rem", margin: 0, fontWeight: 600 }}>
              {llmConfig.provider === "gemini" ? "Google Gemini APIキー" : "APIキー"}
            </label>
            <button
              type="button"
              onClick={() => setShowApiKey((prev) => !prev)}
              style={{ background: "none", border: "none", color: "var(--accent-cyan, #06b6d4)", fontSize: "0.75rem", cursor: "pointer" }}
            >
              {showApiKey ? "隠す 👁️" : "表示 👁️"}
            </button>
          </div>
          <input
            type={showApiKey ? "text" : "password"}
            className="input"
            style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", fontSize: "0.85rem", marginTop: "4px" }}
            placeholder={llmConfig.provider === "gemini" ? "AIzaSy..." : "sk-..."}
            value={llmConfig.api_key || ""}
            onChange={(e) => setLlmConfig((prev) => ({ ...prev, api_key: e.target.value }))}
          />
        </div>
      )}

      {/* Base URL（互換モード時） */}
      {llmConfig?.base_url !== undefined && (
        <div className="form-group" style={{ marginBottom: "12px" }}>
          <label className="label" style={{ fontSize: "0.85rem", fontWeight: 600 }}>ベースURL (OpenAI互換エンドポイント)</label>
          <input
            type="text"
            className="input"
            style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", fontSize: "0.85rem", marginTop: "4px" }}
            placeholder="https://api.deepseek.com/v1 または http://localhost:11434/v1"
            value={llmConfig.base_url || ""}
            onChange={(e) => setLlmConfig((prev) => ({ ...prev, base_url: e.target.value }))}
          />
        </div>
      )}

      {/* TAB 1: 簡易設定（全体一括モデル） */}
      {activeTab === "basic" && (
        <div className="form-group" style={{ marginBottom: "14px" }}>
          <label className="label" style={{ fontSize: "0.85rem", fontWeight: 600 }}>全体既定モデル名</label>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "4px" }}>
            ※ 用途別モデルを未指定の場合、すべての機能（プロット・執筆・監査）にこのモデルが適用されます。
          </div>
          <input
            type="text"
            className="input"
            style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", fontSize: "0.85rem" }}
            placeholder={llmConfig?.provider === "gemini" ? "gemini-2.5-flash" : "gpt-4o-mini"}
            value={llmConfig?.model_name || ""}
            onChange={(e) => setLlmConfig((prev) => ({ ...prev, model_name: e.target.value }))}
          />
          <div style={{ display: "flex", gap: "6px", marginTop: "6px", flexWrap: "wrap" }}>
            {llmConfig?.provider === "gemini" ? (
              ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"].map((m) => (
                <button
                  key={m}
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: "3px 8px", fontSize: "0.75rem", borderRadius: "4px" }}
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
                  style={{ padding: "3px 8px", fontSize: "0.75rem", borderRadius: "4px" }}
                  onClick={() => setLlmConfig((prev) => ({ ...prev, model_name: m }))}
                >
                  {m}
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 2: 詳細設定（用途別個別モデル） */}
      {activeTab === "advanced" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "14px" }}>
          {/* プロット・構成用 */}
          <div style={{ background: "rgba(255, 255, 255, 0.02)", border: "1px solid rgba(255, 255, 255, 0.06)", borderRadius: "6px", padding: "8px 10px" }}>
            <label className="label" style={{ fontSize: "0.8rem", fontWeight: 600, display: "flex", justifyContent: "space-between" }}>
              <span>📝 プロット・構成用モデル</span>
              <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>既定: {serverInfo?.server_defaults?.planning || "gemini-3.5-flash-lite"}</span>
            </label>
            <input
              type="text"
              className="input"
              style={{ width: "100%", padding: "6px 8px", borderRadius: "4px", fontSize: "0.8rem" }}
              placeholder="未指定時は全体モデルを使用"
              value={llmConfig?.model_planning || ""}
              onChange={(e) => setLlmConfig((prev) => ({ ...prev, model_planning: e.target.value }))}
            />
            <div style={{ display: "flex", gap: "4px", marginTop: "4px", flexWrap: "wrap" }}>
              {["gemini-2.5-flash", "gemini-3.5-flash-lite", "gpt-4o-mini"].map((m) => (
                <button
                  key={m}
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: "2px 6px", fontSize: "0.7rem" }}
                  onClick={() => setLlmConfig((prev) => ({ ...prev, model_planning: m }))}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          {/* 本文執筆用 */}
          <div style={{ background: "rgba(255, 255, 255, 0.02)", border: "1px solid rgba(255, 255, 255, 0.06)", borderRadius: "6px", padding: "8px 10px" }}>
            <label className="label" style={{ fontSize: "0.8rem", fontWeight: 600, display: "flex", justifyContent: "space-between" }}>
              <span>✍️ 本文執筆用モデル (表現力・文学的描写重視)</span>
              <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>既定: {serverInfo?.server_defaults?.writing || "gemma-4-31b-it"}</span>
            </label>
            <input
              type="text"
              className="input"
              style={{ width: "100%", padding: "6px 8px", borderRadius: "4px", fontSize: "0.8rem" }}
              placeholder="未指定時は全体モデルを使用"
              value={llmConfig?.model_writing || ""}
              onChange={(e) => setLlmConfig((prev) => ({ ...prev, model_writing: e.target.value }))}
            />
            <div style={{ display: "flex", gap: "4px", marginTop: "4px", flexWrap: "wrap" }}>
              {["claude-3-5-sonnet", "gpt-4o", "gemini-2.5-pro", "gemma-4-31b-it"].map((m) => (
                <button
                  key={m}
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: "2px 6px", fontSize: "0.7rem" }}
                  onClick={() => setLlmConfig((prev) => ({ ...prev, model_writing: m }))}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          {/* 監査・校正用 */}
          <div style={{ background: "rgba(255, 255, 255, 0.02)", border: "1px solid rgba(255, 255, 255, 0.06)", borderRadius: "6px", padding: "8px 10px" }}>
            <label className="label" style={{ fontSize: "0.8rem", fontWeight: 600, display: "flex", justifyContent: "space-between" }}>
              <span>🔍 校正・監査用モデル (高速・論理チェック)</span>
              <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>既定: {serverInfo?.server_defaults?.audit || "gemini-3.5-flash-lite"}</span>
            </label>
            <input
              type="text"
              className="input"
              style={{ width: "100%", padding: "6px 8px", borderRadius: "4px", fontSize: "0.8rem" }}
              placeholder="未指定時は全体モデルを使用"
              value={llmConfig?.model_audit || ""}
              onChange={(e) => setLlmConfig((prev) => ({ ...prev, model_audit: e.target.value }))}
            />
            <div style={{ display: "flex", gap: "4px", marginTop: "4px", flexWrap: "wrap" }}>
              {["gemini-2.5-flash", "gpt-4o-mini", "gemini-3.5-flash-lite"].map((m) => (
                <button
                  key={m}
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: "2px 6px", fontSize: "0.7rem" }}
                  onClick={() => setLlmConfig((prev) => ({ ...prev, model_audit: m }))}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          {/* ベクトル検索・Embedding用 */}
          <div style={{ background: "rgba(255, 255, 255, 0.02)", border: "1px solid rgba(255, 255, 255, 0.06)", borderRadius: "6px", padding: "8px 10px" }}>
            <label className="label" style={{ fontSize: "0.8rem", fontWeight: 600, display: "flex", justifyContent: "space-between" }}>
              <span>🧠 埋め込み用モデル (Embedding / RAG検索)</span>
              <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>既定: {serverInfo?.server_defaults?.embedding || "text-embedding-3-small"}</span>
            </label>
            <input
              type="text"
              className="input"
              style={{ width: "100%", padding: "6px 8px", borderRadius: "4px", fontSize: "0.8rem" }}
              placeholder="text-embedding-3-small"
              value={llmConfig?.model_embedding || ""}
              onChange={(e) => setLlmConfig((prev) => ({ ...prev, model_embedding: e.target.value }))}
            />
            <div style={{ display: "flex", gap: "4px", marginTop: "4px", flexWrap: "wrap" }}>
              {["text-embedding-3-small", "text-embedding-3-large"].map((m) => (
                <button
                  key={m}
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: "2px 6px", fontSize: "0.7rem" }}
                  onClick={() => setLlmConfig((prev) => ({ ...prev, model_embedding: m }))}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* フッター操作ボタン */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "18px", paddingTop: "14px", borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
        <button
          type="button"
          className="btn btn-secondary"
          style={{
            padding: "6px 12px",
            borderRadius: "6px",
            backgroundColor: "rgba(239, 68, 68, 0.15)",
            color: "#f87171",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            cursor: "pointer",
            fontSize: "0.8rem",
            fontWeight: 500,
          }}
          onClick={() => {
            setLlmConfig({});
          }}
        >
          🗑️ 設定をリセット
        </button>

        <button
          type="button"
          className="btn btn-primary"
          style={{
            padding: "6px 16px",
            borderRadius: "6px",
            backgroundColor: "var(--accent-cyan, #06b6d4)",
            color: "white",
            border: "none",
            cursor: "pointer",
            fontSize: "0.85rem",
            fontWeight: 600,
          }}
          onClick={onClose}
        >
          完了
        </button>
      </div>
    </div>
  );
}