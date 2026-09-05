import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from "react";
import { CharacterParams, GenerationState, ChapterItem, ActiveAuditHighlight } from "../types";
import { LLMConfigOverride } from "../types/easyMode";
import { GeneratedPlotStructure } from "../types/reversePlot";

interface NovelContextType {
  character: CharacterParams;
  setCharacter: React.Dispatch<React.SetStateAction<CharacterParams>>;
  currentChapterText: string;
  setCurrentChapterText: React.Dispatch<React.SetStateAction<string>>;
  generationState: GenerationState;
  setGenerationState: React.Dispatch<React.SetStateAction<GenerationState>>;
  selectedBookId: number;
  setSelectedBookId: React.Dispatch<React.SetStateAction<number>>;
  plotStructure: GeneratedPlotStructure | null;
  setPlotStructure: React.Dispatch<React.SetStateAction<GeneratedPlotStructure | null>>;
  activeHighlight: ActiveAuditHighlight | null;
  setActiveHighlight: React.Dispatch<React.SetStateAction<ActiveAuditHighlight | null>>;
  chapters: ChapterItem[];
  setChapters: React.Dispatch<React.SetStateAction<ChapterItem[]>>;
  currentEpNum: number;
  setCurrentEpNum: React.Dispatch<React.SetStateAction<number>>;
  contentLengthLimit: number;
  setContentLengthLimit: React.Dispatch<React.SetStateAction<number>>;
  targetEpisodes: number;
  setTargetEpisodes: React.Dispatch<React.SetStateAction<number>>;
  llmConfig: LLMConfigOverride;
  setLlmConfig: React.Dispatch<React.SetStateAction<LLMConfigOverride>>;
  applySuggestion: (suggestion: string) => void;
  syncGenerationToEditor: (output: string) => void;
  updateActiveChapterText: (text: string) => void;
}

const defaultCharacter: CharacterParams = {
  name: "アルト",
  personality: "熱血・正義感が強い",
  ability: "古代魔導剣術",
  genre: "ハイファンタジー (R15)",
};

const defaultGenerationState: GenerationState = {
  isGenerating: false,
  statusText: "",
  suggestions: [],
  currentTaskId: null,
  error: null,
};

const defaultInitialChapters: ChapterItem[] = [
  {
    ep_num: 1,
    title: "第1話 運命の覚醒",
    summary: "主人公アルトが古代の剣を手にし、冒険へ旅立つ。",
    content: "薄暗いダンジョンの中、15歳の青年アルトは古代の剣を手に取った。",
    is_catharsis: false,
    status: "writing",
  },
];

const NovelContext = createContext<NovelContextType | undefined>(undefined);

export const NovelProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [character, setCharacter] = useState<CharacterParams>(defaultCharacter);
  const [chapters, setChapters] = useState<ChapterItem[]>(defaultInitialChapters);
  const [currentEpNum, setCurrentEpNum] = useState<number>(1);
  const [currentChapterText, setCurrentChapterText] = useState<string>(
    defaultInitialChapters[0].content
  );
  const [generationState, setGenerationState] = useState<GenerationState>(defaultGenerationState);
  const [selectedBookId, setSelectedBookId] = useState<number>(1);
  const [plotStructure, setPlotStructure] = useState<GeneratedPlotStructure | null>(null);
  const [activeHighlight, setActiveHighlight] = useState<ActiveAuditHighlight | null>(null);

  const [contentLengthLimit, setContentLengthLimit] = useState<number>(2000);
  const [targetEpisodes, setTargetEpisodes] = useState<number>(10);
  const [llmConfig, setLlmConfig] = useState<LLMConfigOverride>(() => {
    try {
      const saved = localStorage.getItem("autonovel_llm_config");
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  // llmConfig 変更時に localStorage へ同期
  useEffect(() => {
    try {
      if (llmConfig && Object.keys(llmConfig).length > 0) {
        localStorage.setItem("autonovel_llm_config", JSON.stringify(llmConfig));
      } else {
        localStorage.removeItem("autonovel_llm_config");
      }
    } catch {
      // ignore storage error
    }
  }, [llmConfig]);

  const isSwitchingEpRef = useRef(false);

  // 章切り替え時に該当章のテキストをロード
  useEffect(() => {
    isSwitchingEpRef.current = true;
    const target = chapters.find((c) => c.ep_num === currentEpNum);
    if (target) {
      setCurrentChapterText(target.content);
    }
    const timer = setTimeout(() => {
      isSwitchingEpRef.current = false;
    }, 50);
    return () => clearTimeout(timer);
  }, [currentEpNum]);

  // 本文編集時に chapters 配列の該当章 content も同期
  const updateActiveChapterText = (textOrUpdater: string | ((prev: string) => string)) => {
    const newText = typeof textOrUpdater === "function" ? textOrUpdater(currentChapterText) : textOrUpdater;
    setCurrentChapterText(newText);
    setChapters((prev) =>
      prev.map((c) => (c.ep_num === currentEpNum ? { ...c, content: newText } : c))
    );
  };

  const applySuggestion = (suggestion: string) => {
    updateActiveChapterText(
      currentChapterText.trim()
        ? `${currentChapterText.trim()}\n\n【展開】${suggestion}`
        : suggestion
    );
  };

  const syncGenerationToEditor = (output: string) => {
    if (output) {
      updateActiveChapterText(output);
    }
  };

  return (
    <NovelContext.Provider
      value={{
        character,
        setCharacter,
        currentChapterText,
        setCurrentChapterText: updateActiveChapterText,
        generationState,
        setGenerationState,
        selectedBookId,
        setSelectedBookId,
        plotStructure,
        setPlotStructure,
        activeHighlight,
        setActiveHighlight,
        chapters,
        setChapters,
        currentEpNum,
        setCurrentEpNum,
        contentLengthLimit,
        setContentLengthLimit,
        targetEpisodes,
        setTargetEpisodes,
        llmConfig,
        setLlmConfig,
        applySuggestion,
        syncGenerationToEditor,
        updateActiveChapterText,
      }}
    >
      {children}
    </NovelContext.Provider>
  );
};

export function useNovelContext(): NovelContextType {
  const context = useContext(NovelContext);
  if (!context) {
    throw new Error("useNovelContext must be used within a NovelProvider");
  }
  return context;
}
