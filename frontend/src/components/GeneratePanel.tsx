import React, { useState } from "react";
import { useNovelContext } from "../context/NovelContext";
import { useNovelGeneration } from "../hooks/useNovelGeneration";
import { ReversePlotBuilder } from "./ReversePlotBuilder";
import { GeneratedPlotStructure } from "../types/reversePlot";
import { GachaPlan, GachaResponse, DigestResponse } from "../types/easyMode";
import { generateGachaPlans, generateDigest } from "../api/easyMode";

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
    syncGenerationToEditor,
  } = useNovelContext();

  const { startGeneration, cancelGeneration } = useNovelGeneration(
    (out, sug) => {
      syncGenerationToEditor(out);
      onGenerated?.(out, sug);
    },
    (msg) => onMessage?.(msg),
    (errMsg) => onMessage?.(errMsg)
  );

  const [mode, setMode] = useState<'simple' | 'reverse'>('simple');
  const [showGachaModal, setShowGachaModal] = useState(false);
  const [gachaLoading, setGachaLoading] = useState(false);
  const [gachaResult, setGachaResult] = useState<GachaResponse | null>(null);
  const [digestLoading, setDigestLoading] = useState(false);
  const [digestResult, setDigestResult] = useState<DigestResponse | null>(null);

  const handleReversePlotComplete = (structure: GeneratedPlotStructure) => {
    setPlotStructure(structure);
    const firstEp = structure.episodes?.[0];
    if (firstEp) {
      setCurrentChapterText(
        `【第1話: ${firstEp.title}】\n${firstEp.one_line_summary}\n\n${currentChapterText || ""}`
      );
    }
    onMessage?.(`✨ 逆算プロット構造を確定しました: ${structure.arcs.length}アーク, ${structure.episodes.length}話`);
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
            disabled={generationState.isGenerating || gachaLoading}
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
          disabled={generationState.isGenerating}
          data-testid="btn-submode-simple"
        >
          ⚙️ かんたんモード
        </button>
        <button
          type="button"
          className={`btn ${mode === 'reverse' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setMode('reverse')}
          disabled={generationState.isGenerating}
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
    </>
  ) : (
    <ReversePlotBuilder
      onComplete={handleReversePlotComplete}
      onCancel={() => setMode('simple')}
      targetEpisodes={10}
      genre={character.genre}
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
</section>
  );
}

