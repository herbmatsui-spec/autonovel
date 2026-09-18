import { ChapterChunkItem, GraphDataResponse } from "../types/graph";
import { GraphNodeDetail, EdgeCreationPayload } from "../types/graphInspector";
import { apiFetch, handleResponse } from "./client";

export async function fetchGraphData(bookId: number): Promise<GraphDataResponse> {
  const query = `?book_id=${encodeURIComponent(bookId.toString())}`;
  const res = await apiFetch(`/api/graph${query}`);
  return handleResponse<GraphDataResponse>(res);
}

export async function fetchChapterChunks(chapterId?: number, limit = 20): Promise<ChapterChunkItem[]> {
  const params = new URLSearchParams();
  if (chapterId !== undefined) params.append("chapter_id", chapterId.toString());
  params.append("limit", limit.toString());

  const res = await apiFetch(`/api/graph/chunks?${params.toString()}`);
  return handleResponse<ChapterChunkItem[]>(res);
}

export async function upsertNode(payload: GraphNodeDetail): Promise<void> {
  const res = await apiFetch(`/api/graph/nodes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  await handleResponse<void>(res);
}

export async function fetchNodeSummary(nodeName: string): Promise<{ summary: string; properties: Record<string, any> }> {
  const res = await apiFetch(`/api/graph/nodes/${encodeURIComponent(nodeName)}/summary`);
  return handleResponse<{ summary: string; properties: Record<string, any> }>(res);
}

export async function upsertEdge(payload: EdgeCreationPayload): Promise<void> {
  const res = await apiFetch(`/api/graph/edges`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  await handleResponse<void>(res);
}

export async function deleteNode(nodeName: string): Promise<void> {
  const res = await apiFetch(`/api/graph/nodes/${encodeURIComponent(nodeName)}`, {
    method: 'DELETE',
  });
  await handleResponse<void>(res);
}