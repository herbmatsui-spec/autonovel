import React, { useState, useEffect } from "react";
import { useNovelContext } from "../context/NovelContext";
import { useNovelGeneration } from "../hooks/useNovelGeneration";
import { useStreamingWriter } from "../hooks/useStreamingWriter";
import { useSnapshotHistory } from "../hooks/useSnapshotHistory";
import { useUnifiedStreaming } from "../hooks/useUnifiedStreaming";
import { ReversePlotBuilder } from "./ReversePlotBuilder";
import { GeneratedPlotStructure } from "../types/reversePlot";
import { GachaPlan, GachaResponse, DigestResponse } from "../types/easyMode";
import { generateGachaPlans, generateDigest } from "../api/easyMode";
import { fetchChapterBookScore } from "../api/quality";
import { StylePresetSummary, StyleProfile } from "../types/style";
import { fetchStylePresets, distillStyleFromText } from "../api/styleApi";
import { GENRE_OPTIONS } from "../constants/genres";
import { StyleComparisonModal } from "./style/StyleComparisonModal";
import SimpleModePanel from "./generate/SimpleModePanel";
import ReverseModePanel from "./generate/ReverseModePanel";
import OrchestratedModePanel from "./generate/OrchestratedModePanel";
import { GachaModal } from "./generate/GachaModal";
import { DigestModal } from "./generate/DigestModal";
import { PDCALiveMonitor } from "./studio/PDCALiveMonitor";
import { DAGLiveTracker } from "./studio/DAGLiveTracker";

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
    selectedBookId,
    currentEpNum,
  } = useNovelContext();

  const [chapterScore, setChapterScore] = useState<number | null>(null);

  const { takeSnapshot } = useSnapshotHistory(selectedBookId, currentEpNum);

  useEffect(() => {
    const fetchScore = async () => {
      if (!selectedBookId) return;
      try {
        const scoreData = await fetchChapterBookScore(selectedBookId, currentEpNum);
        setChapterScore(scoreData.overall_score);
      } catch (e) {
        console.error("Failed to fetch chapter score in GeneratePanel", e);
        setChapterScore(null);
      }
    };
    void fetchScore();
  }, [selectedBookId, currentEpNum]);
  const [showStyleComparison, setShowStyleComparison] = useState(false);

  const { startGeneration, cancelGeneration } = useNovelGeneration(
    (out, sug) => {
      takeSnapshot("AI生成前", currentChapterText, "ai_generate");
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
      takeSnapshot("AI生成前", currentChapterText, "ai_generate");
      syncGenerationToEditor(finalText);
      onGenerated?.(finalText, []);
    },
    onMessage: onMessage ?? (() => {}),
    onError: (err) => onMessage?.(`❌ ${err}`),
  });

  const {
    isActive,
    output,
    agentProgress,
    error,
    start: startUnified,
    cancel: cancelUnified,
  } = useUnifiedStreaming();

  const [mode, setMode] = useState<'simple' | 'reverse' | 'orchestrated'>('simple');
  const [showGachaModal, setShowGachaModal] = useState(false);
  const [showDigestModal, setShowDigestModal] = useState(false);

  const [gachaLoading, setGachaLoading] = useState(false);
  const [gachaResult, setGachaResult] = useState<GachaResponse | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
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
  const [selectedStyleId, setSelectedStyleId] = useState<string>("auto");
  const [customStyleProfile, setCustomStyleProfile] = useState<StyleProfile | null>(null);
  const [stylePresets, setStylePresets] = useState<StylePresetSummary[]>([]);
  const [styleSampleText, setStyleSampleText] = useState("");
  const [distillLoading, setDistillLoading] = useState(false);
  const [distillResult, setDistillResult] = useState<StyleProfile | null>(null);
  const [showStyleModal, setShowStyleModal] = useState(false);

  // ハンドラー
  const handleStyleChange = (id: string) => {
    setSelectedStyleId(id);
  };

  const handleReversePlotComplete = (structure: GeneratedPlotStructure) => {
    setPlotStructure(structure);
    setMode('simple');
  };

  const handleSelectGachaPlan = (plan: GachaPlan) => {
    // 1. ガチャの結果をキャラクター設定に反映
    setCharacter((prev) => ({
      ...prev,
      personality: `${prev.personality}\n${plan.protagonist_summary}`.trim(),
    }));

    // 2. 選択したプランの方向性を本文のシードとして挿入
    const seedText = `【プラン: ${plan.title}】\n概要: ${plan.logline}\n魅力点: ${plan.charm_point}`;
    setCurrentChapterText((prev) => (prev ? `${prev}\n\n${seedText}` : seedText));

    // 3. モーダルを閉じる
    setShowGachaModal(false);

    // 4. ステート反映後に生成を開始 (少しだけ遅延させて context 更新を待つ)
    setTimeout(() => {
      startGeneration();
    }, 100);
  };

  const handleRunGacha = async () => {
    setGachaLoading(true);
    try {
      const response = await generateGachaPlans({
        genre: character.genre,
        keywords: [], // 将来的にキーワード入力欄を追加することを想定
      });
      setGachaResult(response);
      setShowGachaModal(true);
    } catch (error) {
      console.error("Gacha generation failed:", error);
      alert("ガチャの生成に失敗しました。");
    } finally {
      setGachaLoading(false);
    }
  };

  const handleRunDigest = async () => {
    if (!gachaResult) {
      alert("先にガチャを回してプランを生成してください。");
      return;
    }

    const planId = selectedPlanId || gachaResult.plans[0]?.plan_id;
    if (!planId) {
      alert("利用可能なプランが見つかりませんでした。");
      return;
    }

    setDigestLoading(true);
    try {
      const response = await generateDigest({
        request_id: gachaResult.request_id,
        selected_plan_id: planId,
      });
      setDigestResult(response);
      setShowDigestModal(true);
    } catch (error) {
      console.error("Digest generation failed:", error);
      alert("ダイジェストの生成に失敗しました。");
    } finally {
      setDigestLoading(false);
    }
  };

  const handleRunDistill = () => {
    // Implementation placeholder
  };

  const handleApplyCustomStyle = () => {
    // Implementation placeholder
  };

  const isBusy = generationState.isGenerating || isStreaming;

  // Early return pattern - clean conditional rendering
  const renderContent = () => {
    if (mode === 'simple') {
      return (
        <SimpleModePanel
        character={character}
        setCharacter={setCharacter}
        llmConfig={llmConfig}
        setLlmConfig={setLlmConfig}
        selectedStyleId={selectedStyleId}
        customStyleProfile={customStyleProfile}
        showStyleModal={showStyleModal}
        setShowStyleModal={setShowStyleModal}
        showApiSettings={showApiSettings}
        setShowApiSettings={setShowApiSettings}
        showApiKey={showApiKey}
        setShowApiKey={setShowApiKey}
        yonkomaEnabled={yonkomaEnabled}
        setYonkomaEnabled={setYonkomaEnabled}
        generationState={generationState}
        startGeneration={startGeneration}
        cancelGeneration={cancelGeneration}
        isStreaming={isStreaming}
        startStreaming={startStreaming}
        cancelStreaming={cancelStreaming}
        isPaused={isPaused}
        resumeStreaming={resumeStreaming}
        pauseStreaming={pauseStreaming}
        streamOutput={streamOutput}
        isBusy={isBusy}
        targetEpisodes={targetEpisodes}
        setTargetEpisodes={setTargetEpisodes}
        contentLengthLimit={contentLengthLimit}
        setContentLengthLimit={setContentLengthLimit}
        currentChapterText={currentChapterText}
        setCurrentChapterText={setCurrentChapterText}
        onMessage={onMessage ?? (() => {})}
        onRunGacha={handleRunGacha}
        onRunDigest={handleRunDigest}
        isGachaLoading={gachaLoading}
        isDigestLoading={digestLoading}
        />
      );
    }

    if (mode === 'reverse') {
      return (
        <ReverseModePanel
          targetEpisodes={targetEpisodes}
          genre={character.genre}
          llmConfig={llmConfig}
          onTargetEpisodesChange={setTargetEpisodes}
          onComplete={handleReversePlotComplete}
          onCancel={() => setMode('simple')}
        />
      );
    }

    return (
      <OrchestratedModePanel
        character={character}
        setCharacter={setCharacter}
        llmConfig={llmConfig}
        setLlmConfig={setLlmConfig}
        selectedStyleId={selectedStyleId}
        customStyleProfile={customStyleProfile}
        showStyleModal={showStyleModal}
        setShowStyleModal={setShowStyleModal}
        showApiSettings={showApiSettings}
        setShowApiSettings={setShowApiSettings}
        showApiKey={showApiKey}
        setShowApiKey={setShowApiKey}
        yonkomaEnabled={yonkomaEnabled}
        setYonkomaEnabled={setYonkomaEnabled}
        generationState={generationState}
        startGeneration={startGeneration}
        cancelGeneration={cancelGeneration}
        isStreaming={isStreaming}
        startStreaming={startStreaming}
        cancelStreaming={cancelStreaming}
        isPaused={isPaused}
        resumeStreaming={resumeStreaming}
        pauseStreaming={pauseStreaming}
        streamOutput={streamOutput}
        isBusy={isBusy}
        targetEpisodes={targetEpisodes}
        setTargetEpisodes={setTargetEpisodes}
        contentLengthLimit={contentLengthLimit}
        setContentLengthLimit={setContentLengthLimit}
        currentChapterText={currentChapterText}
        setCurrentChapterText={setCurrentChapterText}
        agentProgress={agentProgress}
        output={output}
        startUnified={() => startUnified('orchestrated')}
        cancelUnified={cancelUnified}
        isActive={isActive}
        selectedBookId={selectedBookId}
        {...(onMessage ? { onMessage } : {})}
      />
    );
  };

  return (
    <>
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {chapterScore !== null && (
        <div
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: `1px solid ${chapterScore >= 70 ? "rgba(34, 197, 94, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
            borderRadius: "12px",
            padding: "12px 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "50%",
                background: chapterScore >= 70 ? "rgba(34, 197, 94, 0.2)" : "rgba(239, 68, 68, 0.2)",
                color: chapterScore >= 70 ? "#4ade80" : "#f87171",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: "bold",
                fontSize: "1.1rem",
                border: `1px solid ${chapterScore >= 70 ? "#4ade80" : "#f87171"}`,
              }}
            >
              {chapterScore.toFixed(0)}
            </div>
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>
                Current Chapter Quality Score
              </div>
              <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text-main)" }}>
                {chapterScore >= 70 ? "✅ High Quality" : "⚠️ Needs Improvement"}
              </div>
            </div>
          </div>

          {chapterScore < 70 && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#f87171", fontSize: "0.8rem", fontWeight: 600 }}>
              <div
                className="spinner"
                style={{
                  width: "14px",
                  height: "14px",
                  border: "2px solid rgba(248, 113, 113, 0.3)",
                  borderTopColor: "#f87171",
                  borderRadius: "50%",
                  animation: "spin 1s linear infinite",
                }}
              />
              自動改善ループ実行中...
              <style>{`
                @keyframes spin {
                  to { transform: rotate(360deg); }
                }
              `}</style>
            </div>
          )}
        </div>
      )}
      {renderContent()}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        <PDCALiveMonitor bookId={selectedBookId} />
        <DAGLiveTracker bookId={selectedBookId} />
      </div>
    </div>
      <GachaModal
        isOpen={showGachaModal}
        onClose={() => setShowGachaModal(false)}
        plans={gachaResult?.plans || []}
        onSelectPlan={handleSelectGachaPlan}
      />
      <DigestModal
        isOpen={showDigestModal}
        onClose={() => setShowDigestModal(false)}
        digest={digestResult}
      />
    </>
  );
}