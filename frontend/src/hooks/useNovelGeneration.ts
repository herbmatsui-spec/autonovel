import { useCallback, useRef } from "react";
import { generateContent, pollGenerationStatus, cancelTask as apiCancelTask } from "../api/easyMode";
import { useNovelContext } from "../context/NovelContext";

const POLL_INTERVAL_MS = 100;
const POLL_TIMEOUT_MS = 60_000;

export function useNovelGeneration(
  onSuccess?: (output: string, suggestions: string[]) => void,
  onMessage?: (msg: string) => void,
  onError?: (msg: string) => void
) {
  const { character, currentChapterText, setGenerationState } = useNovelContext();
  const isCancelledRef = useRef<boolean>(false);

  const startGeneration = useCallback(async () => {
    isCancelledRef.current = false;
    setGenerationState((prev) => ({
      ...prev,
      isGenerating: true,
      statusText: "生成リクエストを送信中...",
      error: null,
    }));

    try {
      const response = await generateContent({
        chapter_history: [currentChapterText],
        current_chapter: currentChapterText,
        character_params: character,
        content_length_limit: 2000,
      });

      const taskId =
        response.task_id ||
        response.suggestions
          .join("\n")
          .match(/(?:ステータスを\s*)?\/easy_mode\/status\/([^\s]+)/)?.[1];

      if (taskId) {
        setGenerationState((prev) => ({
          ...prev,
          currentTaskId: taskId,
          statusText: "AIが執筆中...",
        }));

        const deadline = Date.now() + POLL_TIMEOUT_MS;
        while (Date.now() < deadline) {
          if (isCancelledRef.current) {
            throw new Error("生成がキャンセルされました");
          }

          const status = await pollGenerationStatus(taskId);
          if (status.status === "completed") {
            const rawResult = status.result;
            const parsed =
              typeof rawResult === "string"
                ? JSON.parse(rawResult || "{}")
                : rawResult || {};

            const out = parsed.output || "生成が完了しました。";
            const sug = parsed.suggestions || [];

            setGenerationState((prev) => ({
              ...prev,
              isGenerating: false,
              statusText: "",
              currentOutput: out,
              suggestions: sug,
              currentTaskId: null,
            }));
            onSuccess?.(out, sug);
            onMessage?.("✨ 本文のAI生成が完了しました。");
            return;
          }

          if (status.status === "failed") {
            throw new Error(status.error || "生成タスクが失敗しました");
          }

          setGenerationState((prev) => ({
            ...prev,
            statusText: `執筆ステータス: ${status.status}...`,
          }));
          await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
        }

        throw new Error("生成タイムアウト（60秒を超過しました）");
      } else {
        // 即時レスポンス
        const out = response.output || "生成が完了しました。";
        const sug = response.suggestions || [];
        setGenerationState((prev) => ({
          ...prev,
          isGenerating: false,
          statusText: "",
          currentOutput: out,
          suggestions: sug,
          currentTaskId: null,
        }));
        onSuccess?.(out, sug);
        onMessage?.("✨ 本文のAI生成が完了しました。");
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "不明なエラーが発生しました";
      setGenerationState((prev) => ({
        ...prev,
        isGenerating: false,
        statusText: "",
        error: msg,
        currentTaskId: null,
      }));
      onError?.(`❌ エラー: ${msg}`);
    }
  }, [character, currentChapterText, setGenerationState, onSuccess, onMessage, onError]);

  const cancelGeneration = useCallback(
    async (taskId: string | null) => {
      isCancelledRef.current = true;
      if (taskId) {
        try {
          await apiCancelTask(taskId);
        } catch {
          // ignore cancel error
        }
      }
      setGenerationState((prev) => ({
        ...prev,
        isGenerating: false,
        statusText: "キャンセルされました",
        currentTaskId: null,
      }));
      onError?.("執筆タスクをキャンセルしました。");
    },
    [setGenerationState, onError]
  );

  return { startGeneration, cancelGeneration };
}
