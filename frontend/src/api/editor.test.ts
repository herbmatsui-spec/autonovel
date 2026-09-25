import { describe, it, expect, vi, beforeEach } from "vitest";
import { runHybridAudit, assistContent, askBible, auditConsistency } from "./editor";

describe("editor API client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("calls runHybridAudit with correct payload and returns UnifiedAuditReport", async () => {
    const mockReport = {
      is_acceptable: true,
      final_score: 85.0,
      quantitative_score: 80.0,
      qualitative: {
        hook_score: 90.0,
        emotional_score: 85.0,
        character_consistency: 80.0,
        overall_score: 88.0,
        critique: "良い展開です",
      },
      detected_cliches: [],
      dialogue_ratio: 0.25,
      conflicts: [],
    };

    const mockResponse = new Response(JSON.stringify(mockReport), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });

    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    const result = await runHybridAudit({
      draft_text: "冒険の始まり。",
      character_profiles: "主人公: アルト",
      plot_spec: "第1話",
    });

    expect(result.final_score).toBe(85.0);
    expect(result.is_acceptable).toBe(true);
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/editor/audit",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          draft_text: "冒険の始まり。",
          character_profiles: "主人公: アルト",
          plot_spec: "第1話",
        }),
      })
    );
  });

  it("handles network error or HTTP error in runHybridAudit", async () => {
    const errorResponse = new Response(
      JSON.stringify({ detail: "サーバー内部エラーが発生しました" }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );

    global.fetch = vi.fn().mockResolvedValue(errorResponse);

    await expect(
      runHybridAudit({
        draft_text: "エラー検証テキスト",
      })
    ).rejects.toMatchObject({
      detail: "サーバー内部エラーが発生しました",
    });
  });
});
