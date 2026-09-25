import { ChapterChunkItem, GraphDataResponse } from "../types/graph";
import { GraphNodeDetail, EdgeCreationPayload } from "../types/graphInspector";
import { apiFetch, handleResponse } from "./client";

export async function fetchGraphData(bookIdOrName?: number | string): Promise<GraphDataResponse> {
  let query = "";
  if (typeof bookIdOrName === "number") {
    query = `?book_id=${encodeURIComponent(bookIdOrName.toString())}`;
  } else if (bookIdOrName) {
    query = `?graph_name=${encodeURIComponent(bookIdOrName)}`;
  }
  const res = await fetch(`/api/graph${query}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchChapterChunks(chapterId?: number, limit = 20): Promise<ChapterChunkItem[]> {
  const params = new URLSearchParams();
  if (chapterId !== undefined) params.append("chapter_id", chapterId.toString());
  params.append("limit", limit.toString());

  const res = await fetch(`/api/graph/chunks?${params.toString()}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
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