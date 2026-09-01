import React, { createContext, useContext, useState, ReactNode } from "react";
import { CharacterParams, GenerationState } from "../types";
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
  applySuggestion: (suggestion: string) => void;
  syncGenerationToEditor: (output: string) => void;
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
  currentOutput: "",
  suggestions: [],
  currentTaskId: null,
  error: null,
};

const NovelContext = createContext<NovelContextType | undefined>(undefined);

export const NovelProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [character, setCharacter] = useState<CharacterParams>(defaultCharacter);
  const [currentChapterText, setCurrentChapterText] = useState<string>(
    "薄暗いダンジョンの中、15歳の青年アルトは古代の剣を手に取った。"
  );
  const [generationState, setGenerationState] = useState<GenerationState>(defaultGenerationState);
  const [selectedBookId, setSelectedBookId] = useState<number>(1);
  const [plotStructure, setPlotStructure] = useState<GeneratedPlotStructure | null>(null);

  const applySuggestion = (suggestion: string) => {
    setCurrentChapterText((prev) => {
      const trimmed = prev.trim();
      return trimmed ? `${trimmed}\n\n【展開】${suggestion}` : suggestion;
    });
  };

  const syncGenerationToEditor = (output: string) => {
    if (output) {
      setCurrentChapterText(output);
      setGenerationState((prev) => ({ ...prev, currentOutput: output }));
    }
  };

  return (
    <NovelContext.Provider
      value={{
        character,
        setCharacter,
        currentChapterText,
        setCurrentChapterText,
        generationState,
        setGenerationState,
        selectedBookId,
        setSelectedBookId,
        plotStructure,
        setPlotStructure,
        applySuggestion,
        syncGenerationToEditor,
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
