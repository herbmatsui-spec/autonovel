import { ChapterChunkItem, GraphDataResponse } from "../types/graph";
import { GraphNodeDetail, EdgeCreationPayload } from "../types/graphInspector";

export async function fetchGraphData(graphName?: string): Promise<GraphDataResponse> {
  const query = graphName ? `?graph_name=${encodeURIComponent(graphName)}` : "";
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
  const res = await fetch(`/api/graph/nodes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
}

export async function fetchNodeSummary(nodeName: string): Promise<{ summary: string; properties: Record<string, any> }> {
  const res = await fetch(`/api/graph/nodes/${encodeURIComponent(nodeName)}/summary`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function upsertEdge(payload: EdgeCreationPayload): Promise<void> {
  const res = await fetch(`/api/graph/edges`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
}

export async function deleteNode(nodeName: string): Promise<void> {
  const res = await fetch(`/api/graph/nodes/${encodeURIComponent(nodeName)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(await res.text());
}
