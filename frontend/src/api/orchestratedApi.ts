import { apiFetch } from "./client";
import type {
  OrchestratedGenerateRequest,
  OrchestratedGenerateResponse,
  OrchestratedTaskStatus,
  AgentEvent,
} from "../types/orchestrated";

const BASE = "/orchestrated";

export async function generateOrchestrated(
  input: OrchestratedGenerateRequest
): Promise<OrchestratedGenerateResponse> {
  const res = await apiFetch(`${BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getOrchestratedStatus(
  taskId: string,
  signal?: AbortSignal | null
): Promise<OrchestratedTaskStatus> {
  const res = await apiFetch(`${BASE}/status/${taskId}`, { ...(signal ? { signal } : {}) });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function cancelOrchestratedTask(
  taskId: string
): Promise<{ task_id: string; status: string }> {
  const res = await apiFetch(`${BASE}/task/${taskId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function exportOrchestratedPackage(
  bookId: number
): Promise<{ zipBlob: Blob; filename: string }> {
  const res = await apiFetch(`${BASE}/export/${bookId}`);
  if (!res.ok) throw new Error(await res.text());
  const blob = await res.blob();
  const contentDisposition = res.headers.get("Content-Disposition");
  const utf8Match = contentDisposition?.match(/filename\*=UTF-8''([^;]+)/i);
  const asciiMatch = contentDisposition?.match(/filename="([^"]+)"/i);
  const utf8Filename = utf8Match ? decodeURIComponent(utf8Match[1] as string) : undefined;
  const rawFilename = utf8Filename || asciiMatch?.[1] || `export_${bookId}.zip`;
  const filename: string = rawFilename ?? `export_${bookId}.zip`;
  return { zipBlob: blob, filename };
}

/** EventSource経由でAgentEventストリームを購読 */
export function subscribeToAgentEvents(
  correlationId: string,
  onEvent: (event: AgentEvent) => void,
  onError?: (err: Error) => void
): EventSource {
  const es = new EventSource(`${BASE}/events/${correlationId}`);
  es.onmessage = (e) => {
    try {
      onEvent(JSON.parse(e.data) as AgentEvent);
    } catch {
      // parse error ignored
    }
  };
  es.onerror = () => onError?.(new Error("EventSource connection failed"));
  return es;
}