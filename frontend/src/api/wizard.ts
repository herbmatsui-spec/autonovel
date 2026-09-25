import { apiFetch, handleResponse, ApiNetworkError, ApiTimeoutError } from "./client";

const PLOTS_BASE_URL = "/api/plots";
const STREAM_BASE_URL = "/api/stream";

export interface ExpandBeatsRequest {
  title: string;
  genre: string;
  synopsis: string;
  target_chapters: number;
  cheat_scale: number;
  growth_curve: string;
  system_assist: number;
  cost_severity: number;
}

export interface BeatItem {
  episode: number;
  title: string;
  outline: string;
  cliffhanger_type: string;
  sensory_focus: string[];
  foreshadowing_notes: string;
}

export interface WizardBookData {
  title: string;
  genre: string;
  synopsis: string;
  target_chapters: number;
  cheat_scale: number;
  growth_curve: string;
  system_assist: number;
  cost_severity: number;
  beats: BeatItem[];
}

export interface SaveWizardBookResponse {
  book_id: number;
  branch_id: number;
  success: boolean;
}

export interface WritingStreamEvent {
  phase: "ContextBuilding" | "Drafting" | "Auditing" | "Complete" | "Error";
  progress: number;
  message: string;
  timestamp: number;
  book_id?: number;
  ep_num?: number;
  branch_id?: number;
  content?: string;
}

/**
 * 拡張ビート生成API呼び出し
 */
export async function expandBeats(request: ExpandBeatsRequest): Promise<BeatItem[]> {
  const res = await apiFetch(`${PLOTS_BASE_URL}/expand-beats`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return handleResponse<BeatItem[]>(res, "Failed to generate beats");
}

/**
 * ウィザード書籍データ保存
 */
export async function saveWizardBook(data: WizardBookData): Promise<SaveWizardBookResponse> {
  const res = await apiFetch(`${PLOTS_BASE_URL}/wizard-save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<SaveWizardBookResponse>(res, "Failed to save wizard book");
}

/**
 * 執筆ストリーム購読 (SSE)
 * 
 * @param book_id 書籍ID
 * @param ep_num エピソード番号
 * @param branch_id ブランチID
 * @param onEvent イベント受信時のコールバック
 * @returns アンsubsribe関数
 */
export function subscribeWritingStream(
  book_id: number,
  ep_num: number,
  branch_id: number = 1,
  onEvent: (event: WritingStreamEvent) => void
): () => void {
  const token = localStorage.getItem("auth_token");
  const url = `${STREAM_BASE_URL}/writing/${book_id}/${ep_num}?branch_id=${branch_id}${token ? `&token=${encodeURIComponent(token)}` : ""}`;
  
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as WritingStreamEvent;
      onEvent(data);
    } catch (err) {
      console.error("Failed to parse SSE event:", err);
    }
  };

  eventSource.onerror = (err) => {
    console.error("SSE connection error:", err);
    eventSource.close();
  };

  // Return cleanup function
  return () => {
    eventSource.close();
  };
}

/**
 * 執筆ストリーム購読 (fetch + ReadableStream版)
 * EventSourceが使えない環境向け
 */
export async function subscribeWritingStreamFetch(
  book_id: number,
  ep_num: number,
  branch_id: number = 1,
  onEvent: (event: WritingStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const url = `${STREAM_BASE_URL}/writing/${book_id}/${ep_num}?branch_id=${branch_id}`;
  
  const res = await apiFetch(url, {
    method: "GET",
    signal,
  });

  if (!res.ok) {
    throw new Error(`SSE connection failed: ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) {
    throw new Error("Response body is not readable");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6)) as WritingStreamEvent;
            onEvent(data);
          } catch (err) {
            console.error("Failed to parse SSE event:", err);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export { ApiNetworkError, ApiTimeoutError };