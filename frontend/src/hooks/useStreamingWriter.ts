import { useState, useRef, useCallback } from "react";
import { generateContentStream } from "../api/easyMode";
import { useNovelContext } from "../context/NovelContext";

interface UseStreamingWriterOptions {
  onSuccess?: (finalText: string) => void;
  onMessage?: (msg: string) => void;
  onError?: (errMsg: string) => void;
  /** 接続エラー時の最大リトライ回数 (デフォルト: 2) */
  maxRetries?: number;
  /** リトライ間隔 (ミリ秒, デフォルト: 1000) */
  retryDelayMs?: number;
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
  /** 現在のリトライ回数 (UI 表示用) */
  const [retryCount, setRetryCount] = useState(0);

  const abortControllerRef = useRef<AbortController | null>(null);
  const isPausedRef = useRef(false);
  const accumulatedTextRef = useRef("");

  const maxRetries = options?.maxRetries ?? 2;
  const retryDelayMs = options?.retryDelayMs ?? 1000;

  const startStreaming = useCallback(
    async (promptOverride?: string) => {
      setIsStreaming(true);
      setIsPaused(false);
      isPausedRef.current = false;
      setStreamOutput("");
      accumulatedTextRef.current = "";
      setRetryCount(0);

      setGenerationState((prev) => ({
        ...prev,
        isGenerating: true,
        statusText: "リアルタイム執筆中...",
        error: null,
      }));

      const controller = new AbortController();
      abortControllerRef.current = controller;

      const promptText = promptOverride !== undefined ? promptOverride : currentChapterText;

      // 接続フェーズ: リトライ機構付きでストリーム接続を確立する
      let response: Response | null = null;
      let lastConnectError: Error | null = null;
      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        if (controller.signal.aborted) break;
        try {
          if (attempt > 0) {
            setRetryCount(attempt);
            setGenerationState((prev) => ({
              ...prev,
              isGenerating: true,
              statusText: `接続エラー。再接続中... (${attempt}/${maxRetries})`,
            }));
            options?.onMessage?.(`🔄 接続エラーのため再接続します (${attempt}/${maxRetries})...`);
            await new Promise((r) => setTimeout(r, retryDelayMs));
            if (controller.signal.aborted) break;
          }
          response = await generateContentStream(
            {
              chapter_history: promptText ? [promptText] : [],
              current_chapter: promptText || "冒険のプロット",
              character_params: character,
              content_length_limit: contentLengthLimit || 2000,
              target_episodes: targetEpisodes || 1,
              ...( (llmConfig && (llmConfig.api_key || llmConfig.provider)) ? { llm_config: llmConfig } : {} ),
            },
            controller.signal
          );
          lastConnectError = null;
          setRetryCount(0);
          break;
        } catch (err: any) {
          // ユーザーキャンセルはリトライしない
          if (controller.signal.aborted) break;
          lastConnectError = err instanceof Error ? err : new Error(err?.message || "不明なエラー");
        }
      }

      // 全リトライ失敗時は明示エラーで終了
      if (!response) {
        const message = lastConnectError?.message || "接続に失敗しました";
        setIsStreaming(false);
        setStreamOutput("");
        accumulatedTextRef.current = "";
        setRetryCount(0);
        setGenerationState((prev) => ({
          ...prev,
          isGenerating: false,
          statusText: `接続エラー: ${message}`,
          error: message,
        }));
        options?.onError?.(`❌ 接続エラー (${maxRetries + 1}回試行): ${message}`);
        options?.onMessage?.(`❌ 接続エラー (${maxRetries + 1}回試行): ${message}`);
        return;
      }

      try {
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

        // ストリーム読み取り中のエラーはフォールバックせず明示エラーで停止する
        const message = err?.message || "不明なエラー";
        setIsStreaming(false);
        setStreamOutput("");
        accumulatedTextRef.current = "";
        setRetryCount(0);
        setGenerationState((prev) => ({
          ...prev,
          isGenerating: false,
          statusText: `接続エラー: ${message}`,
          error: message,
        }));
        options?.onError?.(`❌ 接続エラー: ${message}`);
        options?.onMessage?.(`❌ 接続エラー: ${message}`);
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
      maxRetries,
      retryDelayMs,
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
    retryCount,
    startStreaming,
    pauseStreaming,
    resumeStreaming,
    cancelStreaming,
  };
}
