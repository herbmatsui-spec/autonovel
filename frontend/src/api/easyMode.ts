import {
  EasyModeInput,
  GenerationResponse,
  ExportPackage,
  TaskStatusResponse,
} from "../types/easyMode";

const BASE = "/easy_mode";

export async function generateContent(input: EasyModeInput): Promise<GenerationResponse> {
  const res = await fetch(`${BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function pollGenerationStatus(taskId: string): Promise<TaskStatusResponse> {
  const res = await fetch(`${BASE}/status/${taskId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function exportPackage(bookId: number): Promise<ExportPackage> {
  const res = await fetch(`${BASE}/export/${bookId}`);
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
