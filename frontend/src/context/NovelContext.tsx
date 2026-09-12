import React, { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from "react";
import { CharacterParams, GenerationState, ChapterItem, ActiveAuditHighlight, BookItem } from "../types";
import { LineScore } from "../types/quality";
import { LLMConfigOverride } from "../types/easyMode";
import { GeneratedPlotStructure } from "../types/reversePlot";
import { fetchBooks, fetchBookById } from "../api/books";

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
  applyDiff: (start: number, end: number, replacement: string) => void;
  syncGenerationToEditor: (output: string) => void;
  updateActiveChapterText: (text: string) => void;
  books: BookItem[];
  selectedBook: BookItem | null;
  isLoadingBooks: boolean;
  refreshBooks: () => Promise<void>;
  lineScores: LineScore[];
  setLineScores: React.Dispatch<React.SetStateAction<LineScore[]>>;
  hoveredNodeSummary: { summary: string; properties: Record<string, any> } | null;
  setHoveredNodeSummary: React.Dispatch<React.SetStateAction<{ summary: string; properties: Record<string, any> } | null>>;
  wizardStep: number;
  setWizardStep: React.Dispatch<React.SetStateAction<number>>;
  isWizardActive: boolean;
  setIsWizardActive: React.Dispatch<React.SetStateAction<boolean>>;
  hasCompletedWizard: boolean;
  setHasCompletedWizard: React.Dispatch<React.SetStateAction<boolean>>;
  mode: "easy" | "studio";
  setMode: React.Dispatch<React.SetStateAction<"easy" | "studio">>;
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
     defaultInitialChapters[0]?.content ?? ""
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

  const [books, setBooks] = useState<BookItem[]>([]);
  const [lineScores, setLineScores] = useState<LineScore[]>([]);
  const [hoveredNodeSummary, setHoveredNodeSummary] = useState<{ summary: string; properties: Record<string, any> } | null>(null);
  const [wizardStep, setWizardStep] = useState<number>(0);
  const [isWizardActive, setIsWizardActive] = useState<boolean>(false);
  const [hasCompletedWizard, setHasCompletedWizard] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("autonovel.wizard_completed") === "true";
  });
  // 共有UI設定（Easy/Studioモード間で同期）
  const [selectedStyleId, setSelectedStyleId] = useState<string>(() => {
    if (typeof window === "undefined") return "auto";
    const saved = localStorage.getItem("autonovel.selectedStyleId");
    return saved ?? "auto";
  });
  const [customStyleProfile, setCustomStyleProfile] = useState<any>(() => {
    if (typeof window === "undefined") return null;
    const saved = localStorage.getItem("autonovel.customStyleProfile");
    return saved ? JSON.parse(saved) : null;
  });
  const [showApiSettings, setShowApiSettings] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("autonovel.showApiSettings") === "true";
  });
  const [showApiKey, setShowApiKey] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("autonovel.showApiKey") === "true";
  });
  const [selectedBook, setSelectedBook] = useState<BookItem | null>(null);
  const [isLoadingBooks, setIsLoadingBooks] = useState<boolean>(false);
  const [mode, setMode] = useState<"easy" | "studio">(() => {
    if (typeof window === "undefined") return "studio";
    return (localStorage.getItem("autonovel.mode") as "easy" | "studio") || "studio";
  });

  useEffect(() => {
    localStorage.setItem("autonovel.mode", mode);
  }, [mode]);

  const selectedBookIdRef = useRef(selectedBookId);
  useEffect(() => {
    selectedBookIdRef.current = selectedBookId;
  }, [selectedBookId]);

  const refreshBooks = useCallback(async () => {
    setIsLoadingBooks(true);
    try {
      const data = await fetchBooks();
      setBooks(data);
      const current = data.find((b) => b.id === selectedBookIdRef.current);
      setSelectedBook(current || (data.length > 0 ? data[0] : null));
    } catch (err) {
      console.error("Failed to fetch books:", err);
    } finally {
      setIsLoadingBooks(false);
    }
  }, []);

  // 作品切り替え時にその作品の章一覧を取得
  useEffect(() => {
    let cancelled = false;
    const loadChapters = async () => {
      if (!selectedBookId) {
        setSelectedBook(null);
        return;
      }
      setIsLoadingBooks(true);
      try {
        const book = await fetchBookById(selectedBookId);
        if (!cancelled) {
          setSelectedBook(book);
        }
        // バックエンドから章一覧を取得（存在する場合）
        // TODO: 実装後に章APIを呼ぶ
      } catch (err) {
        if (!cancelled) {
          setSelectedBook(null);
        }
      } finally {
        if (!cancelled) setIsLoadingBooks(false);
      }
    };
    loadChapters();
    return () => { cancelled = true; };
  }, [selectedBookId]);

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

  // selectedStyleId 変更時に localStorage へ同期
  useEffect(() => {
    try {
      if (selectedStyleId) {
        localStorage.setItem("autonovel.selectedStyleId", selectedStyleId);
      } else {
        localStorage.removeItem("autonovel.selectedStyleId");
      }
    } catch {
      // ignore storage error
    }
  }, [selectedStyleId]);

  // customStyleProfile 変更時に localStorage へ同期
  useEffect(() => {
    try {
      if (customStyleProfile) {
        localStorage.setItem("autonovel.customStyleProfile", JSON.stringify(customStyleProfile));
      } else {
        localStorage.removeItem("autonovel.customStyleProfile");
      }
    } catch {
      // ignore storage error
    }
  }, [customStyleProfile]);

  // showApiSettings 変更時に localStorage へ同期
  useEffect(() => {
    try {
      if (showApiSettings) {
        localStorage.setItem("autonovel.showApiSettings", "true");
      } else {
        localStorage.removeItem("autonovel.showApiSettings");
      }
    } catch {
      // ignore storage error
    }
  }, [showApiSettings]);

  // showApiKey 変更時に localStorage へ同期
  useEffect(() => {
    try {
      if (showApiKey) {
        localStorage.setItem("autonovel.showApiKey", "true");
      } else {
        localStorage.removeItem("autonovel.showApiKey");
      }
    } catch {
      // ignore storage error
    }
  }, [showApiKey]);

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
  const updateActiveChapterText = useCallback((textOrUpdater: string | ((prev: string) => string)) => {
    setCurrentChapterText((prev) => {
      const newText = typeof textOrUpdater === "function" ? textOrUpdater(prev) : textOrUpdater;
      setChapters((prevChapters) =>
        prevChapters.map((c) => (c.ep_num === currentEpNum ? { ...c, content: newText } : c))
      );
      return newText;
    });
  }, [currentEpNum]);

  const applySuggestion = useCallback((suggestion: string) => {
    updateActiveChapterText((prev) =>
      prev.trim()
        ? `${prev.trim()}\n\n【展開】${suggestion}`
        : suggestion
    );
  }, [updateActiveChapterText]);

  const applyDiff = useCallback((start: number, end: number, replacement: string) => {
    updateActiveChapterText((prev) => {
      const before = prev.substring(0, start);
      const after = prev.substring(end);
      return `${before}${replacement}${after}`;
    });
  }, [updateActiveChapterText]);

  const syncGenerationToEditor = useCallback((output: string) => {
    if (output) {
      updateActiveChapterText(output);
    }
  }, [updateActiveChapterText]);

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
        applyDiff,
        syncGenerationToEditor,
        updateActiveChapterText,
        books,
        selectedBook,
        isLoadingBooks,
        refreshBooks,
        lineScores,
        setLineScores,
        hoveredNodeSummary,
        setHoveredNodeSummary,
        wizardStep,
        setWizardStep,
        isWizardActive,
        setIsWizardActive,
        hasCompletedWizard,
        setHasCompletedWizard,
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
