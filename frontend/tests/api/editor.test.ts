import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  assistContent,
  askBible,
  auditConsistency,
  generateNextBeats,
} from "../../src/api/editor";

describe("Editor API Client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("assistContent sends POST request and returns AssistResponse", async () => {
    const mockResponse = {
      original_text: "男は扉を開けた。",
      result_text: "重厚な鉄の扉がゆっくり開かれた。",
      action: "describe",
      diff_summary: "五感描写を拡張",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    const result = await assistContent({
      text: "男は扉を開けた。",
      action: "describe",
      sensory_type: "visual",
    });

    expect(result.result_text).toBe("重厚な鉄の扉がゆっくり開かれた。");
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/editor/assist",
      expect.objectContaining({
        method: "POST",
      })
    );
  });

  it("askBible sends POST request and returns AskBibleResponse", async () => {
    const mockResponse = {
      answer: "魔剣グラムは第1章で発見されました。",
      evidence_nodes: [],
      related_characters: ["アルト"],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    const result = await askBible({
      book_id: 1,
      query: "魔剣について教えて",
    });

    expect(result.answer).toContain("魔剣グラム");
  });

  it("auditConsistency sends POST request and handles errors", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => ({ detail: "Database connection failed" }),
    } as any);

    await expect(
      auditConsistency({
        book_id: 1,
        content: "テスト本文",
      })
    ).rejects.toThrow("Database connection failed");
  });

  it("generateNextBeats sends POST request and returns 3 cards", async () => {
    const mockResponse = {
      beats: [
        {
          card_id: "card_a",
          branch_type: "royal",
          title: "王道の一撃",
          summary: "概要",
          content: "本文",
          hook_text: "引き",
        },
      ],
      original_tail: "直前本文",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    const result = await generateNextBeats({
      book_id: 1,
      current_text: "直前本文",
    });

    expect(result.beats.length).toBe(1);
    expect(result.beats[0].title).toBe("王道の一撃");
  });
});
