import React, { useState } from "react";
import { useNovelContext } from "../context/NovelContext";
import { useNovelGeneration } from "../hooks/useNovelGeneration";
import { useStreamingWriter } from "../hooks/useStreamingWriter";
import { useSnapshotHistory } from "../hooks/useSnapshotHistory";
import { useUnifiedStreaming } from "../hooks/useUnifiedStreaming";
import { ReversePlotBuilder } from "./ReversePlotBuilder";
import { GeneratedPlotStructure } from "../types/reversePlot";
import { GachaPlan, GachaResponse, DigestResponse } from "../types/easyMode";
import { generateGachaPlans, generateDigest } from "../api/easyMode";
import { StylePresetSummary, StyleProfile } from "../types/style";
import { fetchStylePresets, distillStyleFromText } from "../api/styleApi";
import { GENRE_OPTIONS } from "../constants/genres";
import { StyleComparisonModal } from "./style/StyleComparisonModal";
import SimpleModePanel from "./generate/SimpleModePanel";
import ReverseModePanel from "./generate/ReverseModePanel";
import OrchestratedModePanel from "./generate/OrchestratedModePanel";

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

  const { takeSnapshot } = useSnapshotHistory(selectedBookId, currentEpNum);
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
    onMessage,
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
    // Implementation placeholder
  };

  const handleRunGacha = () => {
    // Implementation placeholder
  };

  const handleRunDigest = () => {
    // Implementation placeholder
  };

  const handleRunDistill = () => {
    // Implementation placeholder
  };

  const handleApplyCustomStyle = () => {
    // Implementation placeholder
  };

  const isBusy = generationState.isGenerating || isStreaming;

  // Early return pattern - clean conditional rendering
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
        onMessage={onMessage}
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
      startUnified={startUnified}
      cancelUnified={cancelUnified}
      isActive={isActive}
      selectedBookId={selectedBookId}
      onMessage={onMessage}
    />
  );
}