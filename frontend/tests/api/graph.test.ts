import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchGraphData, fetchChapterChunks } from "../../src/api/graph";

describe("graph API client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetchGraphData returns graph data successfully", async () => {
    const mockData = {
      graph_name: "autonovel_graph",
      nodes: [],
      edges: [],
    };
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    } as unknown as Response);

    const result = await fetchGraphData("custom_graph");
    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith("/api/graph?graph_name=custom_graph");
  });

  it("fetchGraphData throws error when response is not ok", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: false,
      text: async () => "Internal Server Error",
    } as unknown as Response);

    await expect(fetchGraphData()).rejects.toThrow("Internal Server Error");
  });

  it("fetchChapterChunks returns chunk list successfully", async () => {
    const mockChunks = [
      {
        id: "chunk-1",
        chapter_id: 1,
        chunk_index: 0,
        content: "テスト段落",
        has_embedding: true,
        created_at: "2026-01-01T00:00:00Z",
      },
    ];
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockChunks,
    } as unknown as Response);

    const result = await fetchChapterChunks(1, 10);
    expect(result).toEqual(mockChunks);
    expect(global.fetch).toHaveBeenCalledWith("/api/graph/chunks?chapter_id=1&limit=10");
  });

  it("fetchChapterChunks throws error when response is not ok", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: false,
      text: async () => "Not Found",
    } as unknown as Response);

    await expect(fetchChapterChunks()).rejects.toThrow("Not Found");
  });
});
