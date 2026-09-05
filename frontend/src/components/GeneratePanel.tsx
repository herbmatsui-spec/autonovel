import React, { useState } from "react";
import { useNovelContext } from "../context/NovelContext";
import { useNovelGeneration } from "../hooks/useNovelGeneration";
import { useStreamingWriter } from "../hooks/useStreamingWriter";
import { ReversePlotBuilder } from "./ReversePlotBuilder";
import { GeneratedPlotStructure } from "../types/reversePlot";
import { GachaPlan, GachaResponse, DigestResponse } from "../types/easyMode";
import { generateGachaPlans, generateDigest } from "../api/easyMode";
import { StylePresetSummary, StyleProfile } from "../types/style";
import { fetchStylePresets, distillStyleFromText } from "../api/styleApi";
import { GENRE_OPTIONS } from "../constants/genres";

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
    setPlotStructure,
    chapters,
    setChapters,
    setCurrentEpNum,
    syncGenerationToEditor,
    contentLengthLimit,
    setContentLengthLimit,
    targetEpisodes,
    setTargetEpisodes,
    llmConfig,
    setLlmConfig,
  } = useNovelContext();

  const { startGeneration, cancelGeneration } = useNovelGeneration(
    (out, sug) => {
      syncGenerationToEditor(out);
      onGenerated?.(out, sug);
    },
    (msg) => onMessage?.(msg),
    (errMsg) => onMessage?.(errMsg)
  );

  const {
    isStreaming,
    isPaused,
    streamOutput,
    startStreaming,
    pauseStreaming,
    resumeStreaming,
    cancelStreaming,
  } = useStreamingWriter({
    onSuccess: (finalText) => {
      syncGenerationToEditor(finalText);
      onGenerated?.(finalText, []);
    },
    onMessage,
    onError: (err) => onMessage?.(`❌ ${err}`),
  });

  const [mode, setMode] = useState<'simple' | 'reverse'>('simple');
  const [showGachaModal, setShowGachaModal] = useState(false);
  const [gachaLoading, setGachaLoading] = useState(false);
  const [gachaResult, setGachaResult] = useState<GachaResponse | null>(null);
  const [digestLoading, setDigestLoading] = useState(false);
  const [digestResult, setDigestResult] = useState<DigestResponse | null>(null);

  // 6コマ要約漫画 (yonkoma) のオン/オフ。UI 側で即時プレビューできるよう localStorage に同期。
  const [yonkomaEnabled, setYonkomaEnabled] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem("autonovel.yonkomaEnabled") === "1";
  });
  const toggleYonkoma = (next: boolean) => {
    setYonkomaEnabled(next);
    try {
      window.localStorage.setItem("autonovel.yonkomaEnabled", next ? "1" : "0");
    } catch {
      // localStorage が使えない環境では無視
    }
  };

  // オプトインAPI設定のアコーディオン・キー表示ステート
  const [showApiSettings, setShowApiSettings] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);

  // 文体（Style DNA）関連のステート
  const [stylePresets, setStylePresets] = useState<StylePresetSummary[]>([]);
  const [selectedStyleId, setSelectedStyleId] = useState<string>("auto");
  const [customStyleProfile, setCustomStyleProfile] = useState<StyleProfile | null>(null);
  const [showStyleModal, setShowStyleModal] = useState(false);
  const [styleSampleText, setStyleSampleText] = useState("");
  const [distillLoading, setDistillLoading] = useState(false);
  const [distillResult, setDistillResult] = useState<StyleProfile | null>(null);

  React.useEffect(() => {
    fetchStylePresets()
      .then((presets) => setStylePresets(presets))
      .catch((err) => console.warn("Failed to fetch style presets:", err));
  }, []);

  const handleStyleChange = (styleId: string) => {
    setSelectedStyleId(styleId);
    if (styleId === "custom_modal") {
      setShowStyleModal(true);
      return;
    }
    if (styleId === "auto") {
      setCustomStyleProfile(null);
      setCharacter((prev) => ({ ...prev, style_id: undefined, style_profile: undefined }));
    } else {
      setCustomStyleProfile(null);
      setCharacter((prev) => ({ ...prev, style_id: styleId, style_profile: undefined }));
      const found = stylePresets.find((p) => p.id === styleId);
      if (found) {
        onMessage?.(`🎨 文体スタイルを「${found.name}」に設定しました`);
      }
    }
  };

  const handleRunDistill = async () => {
    if (!styleSampleText.trim() || styleSampleText.trim().length < 10) {
      onMessage?.("💡 お手本となる文章を10文字以上入力してください");
      return;
    }
    setDistillLoading(true);
    try {
      const res = await distillStyleFromText({
        sample_text: styleSampleText,
        name_hint: "カスタム抽出文体",
      });
      setDistillResult(res.profile);
      onMessage?.("✨ サンプルテキストから作家性DNAを抽出しました！");
    } catch (err: any) {
      onMessage?.(`❌ 文体抽出エラー: ${err.message || err}`);
    } finally {
      setDistillLoading(false);
    }
  };

  const handleApplyCustomStyle = () => {
    if (!distillResult) return;
    setCustomStyleProfile(distillResult);
    setSelectedStyleId("custom_applied");
    setCharacter((prev) => ({
      ...prev,
      style_id: undefined,
      style_profile: distillResult,
    }));
    setShowStyleModal(false);
    onMessage?.(`✨ 作家性DNA「${distillResult.name}」を適用しました！ケレン味強度: ${distillResult.kerenmi_intensity}`);
  };

  const handleReversePlotComplete = (structure: GeneratedPlotStructure) => {
    setPlotStructure(structure);
    if (structure.episodes && structure.episodes.length > 0) {
      // 既存章にユーザーが記述した本文がある場合は警告 (上書き前に確認)
      const hasUserContent = chapters.some((c) => {
        const userText = (c.content || "").replace(/^【第\d+話[^\n]*】\n?/, "").trim();
        return userText.length > 0;
      });

      if (hasUserContent && typeof window !== "undefined") {
        const confirmed = window.confirm(
          "既存の章に記述済みの本文があります。逆算プロットで上書きすると既存本文が消えます。続行しますか？",
        );
        if (!confirmed) {
          onMessage?.("⚠️ 既存本文を保護するため、逆算プロットの適用をキャンセルしました");
          return;
        }
      }

      const mappedChapters = structure.episodes.map((ep) => {
        const existing = chapters.find((c) => c.ep_num === ep.ep_num);
        // 既存章があり、ユーザーが何か書いていた場合は保持
        const preserveExisting = existing && (existing.content || "").trim().length > 0;
        return {
          ep_num: ep.ep_num,
          title: `第${ep.ep_num}話: ${ep.title}`,
          summary: ep.one_line_summary,
          content: preserveExisting
            ? existing!.content
            : ep.ep_num === 1 && currentChapterText
              ? currentChapterText
              : `【第${ep.ep_num}話: ${ep.title}】\n${ep.one_line_summary}\n\n`,
          is_catharsis: ep.is_catharsis,
          status: (ep.ep_num === 1 ? "writing" : "draft") as "writing" | "draft",
        };
      });
      setChapters(mappedChapters);
      setCurrentEpNum(1);
    }
    onMessage?.(`✨ 逆算プロット構造を確定しました: ${structure.arcs.length}アーク, ${structure.episodes.length}話（章ツリーに反映完了）`);
    setMode('simple');
  };

  const handleRunGacha = async () => {
    setGachaLoading(true);
    setShowGachaModal(true);
    try {
      const res = await generateGachaPlans({
        genre: character.genre || "ハイファンタジー (R15)",
        keywords: [character.name || "主人公", character.ability || "剣術", "冒険"],
      });
      setGachaResult(res);
      onMessage?.("✨ 3案の企画ガチャを生成しました！");
    } catch (err: any) {
      onMessage?.(`❌ ガチャ生成エラー: ${err.message || err}`);
    } finally {
      setGachaLoading(false);
    }
  };

  const handleSelectGachaPlan = (plan: GachaPlan) => {
    setCharacter((prev) => ({
      ...prev,
      personality: `${prev.personality} / ${plan.charm_point}`.trim(),
    }));
    setCurrentChapterText(
      `【${plan.title}】\n${plan.logline}\n\n${plan.protagonist_summary}`
    );
    setShowGachaModal(false);
    onMessage?.(`✨ 「${plan.title}」の企画を採用しました！`);
  };

  const handleRunDigest = async () => {
    if (!gachaResult?.request_id || !gachaResult.plans[0]) {
      onMessage?.("💡 先に企画ガチャを実行してください");
      return;
    }
    setDigestLoading(true);
    try {
      const res = await generateDigest({
        request_id: gachaResult.request_id,
        selected_plan_id: gachaResult.plans[0].plan_id,
      });
      setDigestResult(res);
      if (res.episode_1_text) {
        setCurrentChapterText(res.episode_1_text);
      }
      onMessage?.("✨ ダイジェストおよび第1話草案を生成しました！");
    } catch (err: any) {
      onMessage?.(`❌ ダイジェストエラー: ${err.message || err}`);
    } finally {
      setDigestLoading(false);
    }
  };

  const isBusy = generationState.isGenerating || isStreaming;

  return (
    <section className="card" data-testid="generate-panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <h2 style={{ fontSize: "1.2rem", color: "var(--accent-primary, #a78bfa)", margin: 0 }}>
          ⚙️ 制作設定 & プロンプト
        </h2>
        <div style={{ display: "flex", gap: "6px" }}>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: "4px 8px", fontSize: "0.8rem" }}
            onClick={handleRunGacha}
            disabled={isBusy || gachaLoading}
            title="AIが異なる3つの企画案を提案します"
            data-testid="btn-open-gacha"
          >
            🎲 企画ガチャ
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        <button
          type="button"
          className={`btn ${mode === 'simple' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setMode('simple')}
          disabled={isBusy}
          data-testid="btn-submode-simple"
        >
          ⚙️ かんたんモード
        </button>
        <button
          type="button"
          className={`btn ${mode === 'reverse' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setMode('reverse')}
          disabled={isBusy}
          data-testid="btn-submode-reverse"
        >
          🔮 逆算プロットビルダー
        </button>
      </div>

      {mode === 'simple' ? (
        <>
          <div className="form-group">
            <label className="label">作品ジャンル・レーティング</label>
            <select
              className="select"
              value={character.genre}
              onChange={(e) => setCharacter((prev) => ({ ...prev, genre: e.target.value }))}
            >
              {GENRE_OPTIONS.map((g) => (
                <option key={g.value} value={g.value}>
                  {g.value}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <label className="label" style={{ margin: 0 }}>🎨 作家性DNA・文体スタイル</label>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: "2px 8px", fontSize: "0.75rem", color: "var(--accent-cyan)" }}
                onClick={() => setShowStyleModal(true)}
                title="お手本の文章を貼り付けて作家性・文体を自動抽出"
                data-testid="btn-open-style-modal"
              >
                ✨ お手本から文体を抽出
              </button>
            </div>
            <select
              className="select"
              value={selectedStyleId}
              onChange={(e) => handleStyleChange(e.target.value)}
              data-testid="style-select"
            >
              <option value="auto">⚡ ジャンル標準文体（自動最適化）</option>
              {customStyleProfile && (
                <option value="custom_applied">
                  ✨ {customStyleProfile.name} (抽出済みDNA)
                </option>
              )}
              {stylePresets.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.genre})
                </option>
              ))}
            </select>
            {customStyleProfile && selectedStyleId === "custom_applied" && (
              <div
                style={{
                  marginTop: "6px",
                  padding: "6px 10px",
                  background: "rgba(168, 85, 247, 0.1)",
                  border: "1px solid rgba(168, 85, 247, 0.3)",
                  borderRadius: "6px",
                  fontSize: "0.8rem",
                  color: "#d8b4fe",
                }}
              >
                <span>🎯 <strong>適用中:</strong> {customStyleProfile.tone_description}</span>
                <span style={{ marginLeft: "10px", opacity: 0.8 }}>⚡ ケレン味: {customStyleProfile.kerenmi_intensity}</span>
              </div>
            )}
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

          {/* オプトイン: AIモデル & API接続設定 */}
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
                        setLlmConfig((prev) => ({ ...prev, provider: "gemini", model_name: prev.model_name || "gemini-2.5-flash" }));
                      } else if (val === "openai") {
                        setLlmConfig((prev) => ({ ...prev, provider: "openai", model_name: prev.model_name || "gpt-4o-mini", base_url: undefined }));
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
                          {llmConfig.provider === "gemini" ? "Google Gemini API Key" : "API Key"}
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
                        <label className="label" style={{ fontSize: "0.85rem" }}>Base URL (OpenAI互換エンドポイント)</label>
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
                        style={{ padding: "4px 10px", fontSize: "0.75rem", color: "var(--accent-danger, #ef4444)" }}
                        onClick={() => {
                          setLlmConfig({});
                          onMessage?.("⚡ API設定をクリアし、サーバー既定に戻しました");
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

          {/* ボリューム設定（字数 & 話数） */}
          <div
            style={{
              marginBottom: "16px",
              padding: "12px 14px",
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid var(--border-color, rgba(255, 255, 255, 0.1))",
              borderRadius: "8px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <span style={{ fontSize: "0.95rem", fontWeight: 600 }}>📏 執筆ボリューム設定</span>
              <span style={{ fontSize: "0.8rem", color: "var(--accent-cyan)", fontWeight: 700 }}>
                1話あたり {contentLengthLimit.toLocaleString()} 字 / 全 {targetEpisodes} 話 構成
              </span>
            </div>

            {/* 1話あたりの字数 */}
            <div style={{ marginBottom: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "4px" }}>
                <label className="label" style={{ margin: 0 }}>1話あたりの目標字数</label>
                <span style={{ color: "#d8b4fe", fontWeight: 600 }}>{contentLengthLimit.toLocaleString()} 文字</span>
              </div>
              <input
                type="range"
                min={500}
                max={8000}
                step={250}
                value={contentLengthLimit}
                onChange={(e) => setContentLengthLimit(Number(e.target.value))}
                style={{ width: "100%", cursor: "pointer" }}
              />
              <div style={{ display: "flex", gap: "6px", marginTop: "4px" }}>
                {[
                  { label: "短編 (1,500字)", val: 1500 },
                  { label: "標準 (2,500字)", val: 2500 },
                  { label: "長編 (4,000字)", val: 4000 },
                  { label: "重厚 (6,000字)", val: 6000 },
                ].map((p) => (
                  <button
                    key={p.val}
                    type="button"
                    className={`btn ${contentLengthLimit === p.val ? "btn-primary" : "btn-secondary"}`}
                    style={{ flex: 1, padding: "3px 4px", fontSize: "0.72rem" }}
                    onClick={() => setContentLengthLimit(p.val)}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 構成目標話数（最大50話） */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "4px" }}>
                <label className="label" style={{ margin: 0 }}>構成目標話数 (最大50話)</label>
                <span style={{ color: "#38bdf8", fontWeight: 600 }}>全 {targetEpisodes} 話</span>
              </div>
              <input
                type="range"
                min={1}
                max={50}
                step={1}
                value={targetEpisodes}
                onChange={(e) => setTargetEpisodes(Number(e.target.value))}
                style={{ width: "100%", cursor: "pointer" }}
              />
              <div style={{ display: "flex", gap: "6px", marginTop: "4px", flexWrap: "wrap" }}>
                {[1, 3, 5, 10, 20, 30, 50].map((num) => (
                  <button
                    key={num}
                    type="button"
                    className={`btn ${targetEpisodes === num ? "btn-primary" : "btn-secondary"}`}
                    style={{ flex: 1, minWidth: "40px", padding: "3px 4px", fontSize: "0.72rem" }}
                    onClick={() => setTargetEpisodes(num)}
                  >
                    {num}話
                  </button>
                ))}
              </div>
            </div>

            {/* 6コマ要約漫画 (yonkoma) のオン/オフ */}
            <div
              style={{
                marginTop: "12px",
                paddingTop: "10px",
                borderTop: "1px dashed var(--border-color, rgba(255, 255, 255, 0.15))",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "8px",
              }}
            >
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  fontSize: "0.85rem",
                  cursor: "pointer",
                }}
                data-testid="label-yonkoma-toggle"
              >
                <input
                  type="checkbox"
                  checked={yonkomaEnabled}
                  onChange={(e) => toggleYonkoma(e.target.checked)}
                  data-testid="checkbox-yonkoma"
                />
                <span>🎬 各話を6コマ要約漫画プロンプトで生成する</span>
              </label>
              <span style={{ fontSize: "0.7rem", color: "var(--text-muted, #94a3b8)" }}>
                {yonkomaEnabled ? "ON: 1話=1枚のサマリー画像" : "OFF"}
              </span>
            </div>
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

          {/* ストリーミング生成中のコントロールバー */}
          {isStreaming && (
            <div
              style={{
                background: "rgba(6, 182, 212, 0.15)",
                border: "1px solid var(--accent-cyan)",
                borderRadius: "8px",
                padding: "10px 14px",
                marginBottom: "14px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
              data-testid="streaming-control-bar"
            >
              <div style={{ fontSize: "0.85rem", color: "var(--accent-cyan)", display: "flex", alignItems: "center", gap: "6px" }}>
                <span>⚡ リアルタイム執筆中 ({streamOutput.length} 文字)</span>
                {isPaused && <span style={{ color: "#fbbf24", fontWeight: 700 }}>(一時停止中)</span>}
              </div>
              <div style={{ display: "flex", gap: "6px" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                  onClick={isPaused ? resumeStreaming : pauseStreaming}
                  data-testid="btn-pause-stream"
                >
                  {isPaused ? "▶ 再開" : "⏸ 一時停止"}
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                  onClick={cancelStreaming}
                  data-testid="btn-cancel-stream"
                >
                  ⏹ 中止
                </button>
              </div>
            </div>
          )}

          {generationState.statusText && !isStreaming && (
            <div style={{ marginBottom: "12px", fontSize: "0.9rem", color: "var(--text-muted)" }}>
              {generationState.statusText}
            </div>
          )}

          <div style={{ display: "flex", gap: "8px" }}>
            <button
              className="btn btn-primary"
              style={{ flex: 1.2, backgroundColor: "var(--accent-cyan)", borderColor: "var(--accent-cyan)", color: "#000", fontWeight: 700 }}
              onClick={() => startStreaming()}
              disabled={isBusy}
              data-testid="btn-stream-generate"
              title="SSEストリーミングで1文字ずつリアルタイム執筆"
            >
              {isStreaming ? "⚡ ストリーミング執筆中..." : "⚡ リアルタイム速筆 (SSE)"}
            </button>

            <button
              className="btn btn-secondary"
              style={{ flex: 1 }}
              onClick={startGeneration}
              disabled={isBusy}
              data-testid="btn-standard-generate"
            >
              {generationState.isGenerating ? "🪄 執筆中..." : "🪄 かんたん執筆開始"}
            </button>

            {generationState.isGenerating && !isStreaming && (
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
        </>
      ) : (
        <ReversePlotBuilder
          onComplete={handleReversePlotComplete}
          onCancel={() => setMode('simple')}
          targetEpisodes={targetEpisodes}
          genre={character.genre}
          llmConfig={llmConfig}
          onTargetEpisodesChange={setTargetEpisodes}
        />
      )}

  {/* 3案企画ガチャモーダル */}
  {showGachaModal && (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0,0,0,0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        backdropFilter: "blur(4px)",
      }}
      data-testid="gacha-modal"
    >
      <div
        style={{
          background: "var(--card-bg, #18181b)",
          border: "1px solid var(--border-color, #27272a)",
          borderRadius: "12px",
          width: "90%",
          maxWidth: "750px",
          padding: "20px",
          maxHeight: "85vh",
          overflowY: "auto",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h3 style={{ margin: 0, fontSize: "1.1rem", color: "var(--accent-primary, #a78bfa)" }}>
            🎲 3案 企画ガチャ (Gacha Pitch)
          </h3>
          <button
            type="button"
            style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}
            onClick={() => setShowGachaModal(false)}
          >
            ✕
          </button>
        </div>

        {gachaLoading ? (
          <div style={{ textAlign: "center", padding: "40px", color: "var(--accent-cyan)" }}>
            ⏳ AIが3つの異なる方向性の企画を創出中...
          </div>
        ) : gachaResult ? (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", marginBottom: "16px" }}>
              {gachaResult.plans.map((p) => (
                <div
                  key={p.plan_id}
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "8px",
                    padding: "12px",
                    display: "flex",
                    flexDirection: "column",
                  }}
                  data-testid={`gacha-plan-${p.plan_id}`}
                >
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      color: p.plan_type === "royal" ? "#38bdf8" : p.plan_type === "curveball" ? "#f59e0b" : "#f43f5e",
                      marginBottom: "4px",
                    }}
                  >
                    {p.plan_type === "royal" ? "⚔️ 王道" : p.plan_type === "curveball" ? "🌀 変化球" : "🌑 ダーク"}
                  </span>
                  <div style={{ fontWeight: 700, fontSize: "0.95rem", marginBottom: "6px" }}>{p.title}</div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "8px", flex: 1, lineHeight: "1.4" }}>
                    {p.logline}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--accent-cyan)", marginBottom: "12px", fontStyle: "italic" }}>
                    ✨ {p.charm_point}
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ padding: "6px 8px", fontSize: "0.8rem", width: "100%" }}
                    onClick={() => handleSelectGachaPlan(p)}
                    data-testid={`btn-select-plan-${p.plan_id}`}
                  >
                    この企画を採用
                  </button>
                </div>
              ))}
            </div>

            <div style={{ display: "flex", gap: "8px", justifyContent: "space-between", alignItems: "center" }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleRunGacha}
                disabled={gachaLoading}
                style={{ fontSize: "0.85rem" }}
              >
                🔄 再ガチャを回す
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleRunDigest}
                disabled={digestLoading}
                style={{ fontSize: "0.85rem", color: "var(--accent-cyan)" }}
              >
                {digestLoading ? "⏳ ダイジェスト生成中..." : "📝 選択案からダイジェスト生成"}
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )}

      {/* 作家性DNA（文体）抽出モーダル */}
      {showStyleModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            backdropFilter: "blur(4px)",
          }}
          data-testid="style-distiller-modal"
        >
          <div
            style={{
              background: "var(--card-bg, #18181b)",
              border: "1px solid var(--border-color, #27272a)",
              borderRadius: "12px",
              width: "90%",
              maxWidth: "700px",
              padding: "20px",
              maxHeight: "85vh",
              overflowY: "auto",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ margin: 0, fontSize: "1.1rem", color: "var(--accent-primary, #a78bfa)" }}>
                ✨ お手本から作家性DNA（文体）を抽出
              </h3>
              <button
                type="button"
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "1.2rem" }}
                onClick={() => setShowStyleModal(false)}
              >
                ✕
              </button>
            </div>

            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "12px", lineHeight: "1.4" }}>
              真似したいプロ作家やWeb小説の文章サンプル（300〜1,000文字程度）を貼り付けてください。
              AIが「文長リズム」「文末比率」「比喩の癖」「ケレン味（過剰演出強度）」を逆算抽出します。
            </p>

            <div className="form-group" style={{ marginBottom: "14px" }}>
              <textarea
                className="textarea"
                rows={5}
                placeholder="ここに真似したい小説の本文サンプルを貼り付けてください..."
                value={styleSampleText}
                onChange={(e) => setStyleSampleText(e.target.value)}
                data-testid="style-sample-textarea"
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginBottom: "16px" }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleRunDistill}
                disabled={distillLoading || !styleSampleText.trim()}
                data-testid="btn-run-distill"
              >
                {distillLoading ? "⏳ AIが文体DNAを解析中..." : "🔍 文体DNAを抽出（蒸留）"}
              </button>
            </div>

            {distillResult && (
              <div
                style={{
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid var(--border-color)",
                  borderRadius: "8px",
                  padding: "14px",
                  marginBottom: "16px",
                }}
                data-testid="distill-result-card"
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <span style={{ fontWeight: 700, fontSize: "1rem", color: "var(--accent-primary, #a78bfa)" }}>
                    🎯 {distillResult.name}
                  </span>
                  <span
                    style={{
                      fontSize: "0.8rem",
                      padding: "2px 8px",
                      background: "rgba(16, 185, 129, 0.2)",
                      color: "#34d399",
                      borderRadius: "12px",
                      fontWeight: 700,
                    }}
                  >
                    ケレン味: {distillResult.kerenmi_intensity}
                  </span>
                </div>

                <div style={{ fontSize: "0.85rem", marginBottom: "6px" }}>
                  <strong>トーン:</strong> {distillResult.tone_description}
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "8px" }}>
                  <strong>文長分布:</strong> 平均{distillResult.sentence_length.avg}文字 / <strong>文末:</strong> だ・である({Math.round(distillResult.sentence_end_distribution.da_dearu * 100)}%), 体言止め({Math.round(distillResult.sentence_end_distribution.nominal * 100)}%)
                </div>

                {distillResult.few_shot_sample && (
                  <div
                    style={{
                      background: "rgba(0,0,0,0.3)",
                      padding: "8px 10px",
                      borderRadius: "6px",
                      fontSize: "0.8rem",
                      fontStyle: "italic",
                      color: "#e2e8f0",
                      marginBottom: "12px",
                      borderLeft: "3px solid var(--accent-primary, #a78bfa)",
                    }}
                  >
                    "{distillResult.few_shot_sample}"
                  </div>
                )}

                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ width: "100%", padding: "8px" }}
                  onClick={handleApplyCustomStyle}
                  data-testid="btn-apply-style"
                >
                  ✨ この文体スタイルを採用して執筆に適用
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

