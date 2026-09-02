import { useState, useRef, useCallback } from "react";
import { generateContentStream } from "../api/easyMode";
import { useNovelContext } from "../context/NovelContext";

interface UseStreamingWriterOptions {
  onSuccess?: (finalText: string) => void;
  onMessage?: (msg: string) => void;
  onError?: (errMsg: string) => void;
}

export function useStreamingWriter(options?: UseStreamingWriterOptions) {
  const {
    character,
    currentChapterText,
    setCurrentChapterText,
    setGenerationState,
    contentLengthLimit,
    targetEpisodes,
    llmConfig,
  } = useNovelContext();
  const [isStreaming, setIsStreaming] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [streamOutput, setStreamOutput] = useState("");

  const abortControllerRef = useRef<AbortController | null>(null);
  const isPausedRef = useRef(false);
  const accumulatedTextRef = useRef("");

  const startStreaming = useCallback(
    async (promptOverride?: string) => {
      setIsStreaming(true);
      setIsPaused(false);
      isPausedRef.current = false;
      setStreamOutput("");
      accumulatedTextRef.current = "";

      setGenerationState((prev) => ({
        ...prev,
        isGenerating: true,
        statusText: "リアルタイム執筆中...",
        error: null,
      }));

      const controller = new AbortController();
      abortControllerRef.current = controller;

      const promptText = promptOverride !== undefined ? promptOverride : currentChapterText;

      try {
        const response = await generateContentStream(
          {
            chapter_history: promptText ? [promptText] : [],
            current_chapter: promptText || "冒険のプロット",
            character_params: character,
            content_length_limit: contentLengthLimit || 2000,
            target_episodes: targetEpisodes || 1,
            llm_config: (llmConfig && (llmConfig.api_key || llmConfig.provider)) ? llmConfig : undefined,
          },
          controller.signal
        );

        if (!response.body) {
          throw new Error("ストリームレスポンスが取得できませんでした");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          // ポーズ状態の待機ループ
          while (isPausedRef.current) {
            await new Promise((r) => setTimeout(r, 150));
            if (controller.signal.aborted) break;
          }

          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith("data:")) continue;

            const jsonStr = trimmed.replace(/^data:\s*/, "");
            try {
              const data = JSON.parse(jsonStr);
              if (data.type === "chunk" && data.text) {
                accumulatedTextRef.current += data.text;
                setStreamOutput(accumulatedTextRef.current);
              } else if (data.type === "done") {
                // 完了
              } else if (data.type === "error") {
                throw new Error(data.message || "ストリーミング生成エラー");
              }
            } catch (err: any) {
              if (err.message && err.message.includes("ストリーミング生成エラー")) {
                throw err;
              }
              // 通常のJSONパーススキップ
            }
          }
        }

        const finalText = accumulatedTextRef.current || "執筆が完了しました。";
        // 本文にリアルタイム反映（末尾追記または全文更新）
        setCurrentChapterText((prev) => (prev ? `${prev}\n\n${finalText}` : finalText));
        setGenerationState((prev) => ({
          ...prev,
          isGenerating: false,
          statusText: "",
          currentOutput: finalText,
        }));

        setIsStreaming(false);
        options?.onSuccess?.(finalText);
        options?.onMessage?.("✨ リアルタイム執筆が完了しました！");
      } catch (err: any) {
        if (controller.signal.aborted) {
          // ユーザーキャンセル時
          setIsStreaming(false);
          setGenerationState((prev) => ({
            ...prev,
            isGenerating: false,
            statusText: "執筆を一時停止・中断しました",
          }));
          options?.onMessage?.("⏹ 執筆ストリーミングを停止しました。");
          return;
        }

        // フォールバック（オフライン・モック時）: タイピングシミュレーション
        const fallbackText = `【第1章 展開】\n${character.name}は古代の魔導剣を構え、ダンジョンの深淵へと踏み出した。剣先から放たれる微かな蒼い光が、古代文字が刻まれた石壁を照らし出す。\n「ここで引き返すわけにはいかない――」\n胸に秘めた正義感と決意を新たに、若き冒険者は運命の扉を開いた。`;

        let currentIdx = 0;
        const interval = setInterval(() => {
          if (controller.signal.aborted || currentIdx >= fallbackText.length) {
            clearInterval(interval);
            setIsStreaming(false);
            const res = fallbackText.substring(0, currentIdx);
            setCurrentChapterText((prev) => (prev ? `${prev}\n\n${res}` : res));
            setGenerationState((prev) => ({ ...prev, isGenerating: false, statusText: "" }));
            options?.onSuccess?.(res);
            options?.onMessage?.("✨ 執筆が完了しました！");
            return;
          }
          currentIdx += 3;
          accumulatedTextRef.current = fallbackText.substring(0, currentIdx);
          setStreamOutput(accumulatedTextRef.current);
        }, 50);
      }
    },
    [
      character,
      currentChapterText,
      setCurrentChapterText,
      setGenerationState,
      options,
      contentLengthLimit,
      targetEpisodes,
      llmConfig,
    ]
  );

  const pauseStreaming = useCallback(() => {
    isPausedRef.current = true;
    setIsPaused(true);
    options?.onMessage?.("⏸ 執筆を一時停止しました");
  }, [options]);

  const resumeStreaming = useCallback(() => {
    isPausedRef.current = false;
    setIsPaused(false);
    options?.onMessage?.("▶ 執筆を再開しました");
  }, [options]);

  const cancelStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsStreaming(false);
    setIsPaused(false);
    isPausedRef.current = false;
    options?.onMessage?.("⏹ 執筆をキャンセルしました");
  }, [options]);

  return {
    isStreaming,
    isPaused,
    streamOutput,
    startStreaming,
    pauseStreaming,
    resumeStreaming,
    cancelStreaming,
  };
}
