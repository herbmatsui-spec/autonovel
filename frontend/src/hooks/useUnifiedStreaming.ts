import { useState, useCallback, useRef, useEffect } from "react";
import { generateContentStream } from "../api/easyMode";
import { generateOrchestrated, getOrchestratedStatus, subscribeToAgentEvents } from "../api/orchestratedApi";
import type { EasyModeInput } from "../types/easyMode";
import type { OrchestratedGenerateRequest, AgentEvent, AgentName } from "../types/orchestrated";
import type { UnifiedStreamingState, GenerationMode, GenerationState } from "../types";
import { useNovelContext } from "../context/NovelContext";

export function useUnifiedStreaming() {
  const {
    character,
    currentChapterText,
    setCurrentChapterText,
    setGenerationState,
    contentLengthLimit,
    targetEpisodes,
    llmConfig,
    selectedBookId,
  } = useNovelContext();
  const [state, setState] = useState<UnifiedStreamingState>({
    mode: "easy",
    isActive: false,
    output: "",
    agentProgress: {} as any,
    error: undefined,
  });
  const abortRef = useRef<AbortController | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const start = useCallback(async (mode: GenerationMode, input?: OrchestratedGenerateRequest) => {
    abortRef.current = new AbortController();
    esRef.current?.close();
    
    setState((s: UnifiedStreamingState) => ({ ...s, mode, isActive: true, output: "", agentProgress: {} as any, error: undefined }));
    setGenerationState(p => ({ ...p, isGenerating: true, statusText: mode === "easy" ? "リアルタイム執筆中..." : "オーケストレーション開始...", error: null }));
    
    try {
      if (mode === "easy") {
        const response = await generateContentStream(
          { chapter_history: [currentChapterText], current_chapter: currentChapterText, character_params: character, content_length_limit: contentLengthLimit || 2000, target_episodes: targetEpisodes || 1, llm_config: llmConfig },
          abortRef.current.signal
        );
        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          for (const line of buffer.split("\n")) {
            if (line.startsWith("data:")) {
              const data = JSON.parse(line.replace(/^data:\s*/, ""));
              if (data.type === "chunk") setState((s: UnifiedStreamingState) => ({ ...s, output: s.output + data.text }));
            }
          }
        }
      } else {
        const { task_id } = await generateOrchestrated(input!);
        esRef.current = subscribeToAgentEvents(input!.correlation_id || `book_${input!.book_id}_branch_${input!.branch_id}_ep_${input!.ep_num}`, (event) => {
          setState((s: UnifiedStreamingState) => ({ ...s, agentProgress: { ...s.agentProgress, [event.agent]: { status: event.payload?.status, payload: event.payload } } }));
        });
        // ポーリングで完了待ち（省略）
        const deadline = Date.now() + 300_000; // 5分タイムアウト
        while (Date.now() < deadline) {
          if (abortRef.current?.signal.aborted) throw new Error("キャンセルされました");
          const status = await getOrchestratedStatus(task_id, abortRef.current.signal);
          
          if (status.status === "completed") {
            const result = status.result;
            if (result?.output) {
              setCurrentChapterText(result.output);
              setState((s: UnifiedStreamingState) => ({ ...s, output: result.output }));
              setGenerationState((p: GenerationState) => ({ ...p, isGenerating: false, statusText: "", error: null }));
            }
setState((s: UnifiedStreamingState) => ({ ...s, isActive: false }));
            setGenerationState((p: GenerationState) => ({ ...p, isGenerating: false, statusText: "" }));
            return;
          }
          if (status.status === "failed") throw new Error(status.error || "生成失敗");
          
          await new Promise(resolve => setTimeout(resolve, 500));
        }
        throw new Error("タイムアウト");
      }
    } catch (e: any) {
      if (e.name !== "AbortError") {
        setState((s: UnifiedStreamingState) => ({ ...s, isActive: false, error: e.message }));
        setGenerationState((p: GenerationState) => ({ ...p, isGenerating: false, error: e.message }));
      }
    }
  },
  [
    character,
    currentChapterText,
    setCurrentChapterText,
    setGenerationState,
    contentLengthLimit,
    targetEpisodes,
    llmConfig,
    selectedBookId,
  ]
);
 
   const cancel = useCallback(() => {
    abortRef.current?.abort();
    esRef.current?.close();
    setState((s: UnifiedStreamingState) => ({ ...s, isActive: false }));
  }, []);

  return { ...state, start, cancel, setMode: (m: GenerationMode) => setState((s: UnifiedStreamingState) => ({ ...s, mode: m })) };
}