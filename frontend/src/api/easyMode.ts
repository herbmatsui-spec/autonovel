import {
  EasyModeInput,
  GenerationResponse,
  ExportPackage,
  TaskStatusResponse,
  GachaRequest,
  GachaResponse,
  DigestRequest,
  DigestResponse,
  PromotionRequest,
  PromotionResponse,
  ExportRequestPayload,
} from "../types/easyMode";
import { apiFetch } from "./client";

const BASE = "/easy_mode";

export async function generateContent(input: EasyModeInput): Promise<GenerationResponse> {
  const res = await apiFetch(`${BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function generateContentStream(
  input: EasyModeInput,
  signal?: AbortSignal
): Promise<Response> {
  const res = await apiFetch(`${BASE}/generate/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal,
  });
  if (!res.ok) {
    let errorMessage = await res.text();
    try {
      const errorJson = await res.json();
      if (errorJson.detail) {
        errorMessage = errorJson.detail;
      } else if (errorJson.message) {
        errorMessage = errorJson.message;
      }
    } catch (e) {
      // If not JSON, use the text we already have
    }
    throw new Error(errorMessage);
  }
  return res;
}

export async function pollGenerationStatus(
  taskId: string,
  signal?: AbortSignal
): Promise<TaskStatusResponse> {
  const res = await apiFetch(`${BASE}/status/${taskId}`, { signal });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function cancelTask(taskId: string): Promise<{ task_id: string; status: string }> {
  const res = await apiFetch(`${BASE}/task/${taskId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function exportPackage(bookId: number): Promise<ExportPackage> {
  const res = await apiFetch(`${BASE}/export/${bookId}`);
  if (!res.ok) throw new Error(await res.text());
  const blob = await res.blob();
  const contentDisposition = res.headers.get("Content-Disposition");
  // RFC6266 形式: filename="ascii.zip"; filename*=UTF-8''encoded.zip
  const utf8Match = contentDisposition?.match(/filename\*=UTF-8''([^;]+)/i);
  const asciiMatch = contentDisposition?.match(/filename="([^"]+)"/i);
  const filename =
    (utf8Match && decodeURIComponent(utf8Match[1])) ||
    asciiMatch?.[1] ||
    `export_${bookId}.zip`;
  return { zipBlob: blob, filename };
}

export async function exportPackageWithData(
  bookId: number,
  payload?: ExportRequestPayload
): Promise<ExportPackage> {
  const res = await apiFetch(`${BASE}/export-with-data?book_id=${bookId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  if (!res.ok) throw new Error(await res.text());
  const blob = await res.blob();
  const contentDisposition = res.headers.get("Content-Disposition");
  const utf8Match = contentDisposition?.match(/filename\*=UTF-8''([^;]+)/i);
  const asciiMatch = contentDisposition?.match(/filename="([^"]+)"/i);
  const filename =
    (utf8Match && decodeURIComponent(utf8Match[1])) ||
    asciiMatch?.[1] ||
    `export_${bookId}.zip`;
  return { zipBlob: blob, filename };
}

export async function generateGachaPlans(req: GachaRequest): Promise<GachaResponse> {
  const res = await apiFetch(`${BASE}/gacha`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function generateDigest(req: DigestRequest): Promise<DigestResponse> {
  const res = await apiFetch(`${BASE}/digest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function promoteToStudio(req: PromotionRequest): Promise<PromotionResponse> {
  const res = await apiFetch(`${BASE}/promote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

