import {
  AssetPackRequest,
  AssetPackResponse,
  ArtifactMetaResponse,
  EbookExportRequest,
  EbookExportResponse,
  IFRouteGenerateRequest,
  IFRouteResponse,
  MediaMixRequest,
  MediaMixResponse,
  TaskStatusResponse,
} from "../types/multimedia";

const BASE = "/multimedia";

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`multimedia ${path} failed: ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`multimedia GET ${path} failed: ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export const generateMediaMix = (req: MediaMixRequest) =>
  postJson<MediaMixResponse>("/media-mix", req);

export const exportEbook = (req: EbookExportRequest) =>
  postJson<EbookExportResponse>("/ebook", req);

export const generateIFRoutes = (req: IFRouteGenerateRequest) =>
  postJson<IFRouteResponse>("/if-routes", req);

export const generateAssetPack = (req: AssetPackRequest) =>
  postJson<AssetPackResponse>("/asset-pack", req);

export const getArtifact = (assetId: number) =>
  getJson<ArtifactMetaResponse>(`/artifacts/${assetId}`);

export const getTaskStatus = (taskId: string) =>
  getJson<TaskStatusResponse>(`/tasks/${taskId}`);

export async function downloadAssetPack(assetId: number): Promise<Blob> {
  const res = await fetch(`${BASE}/artifacts/${assetId}/download`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`download failed: ${res.status} ${text}`);
  }
  return res.blob();
}
