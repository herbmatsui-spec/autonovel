import { ChapterChunkItem, GraphDataResponse } from "../types/graph";

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
