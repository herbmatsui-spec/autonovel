import { describe, it, expect, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { generateReversePlot } from "../../src/api/reversePlot";

const mockPlotResponse = {
  arcs: [
    {
      arc_num: 1,
      start_ep: 1,
      end_ep: 3,
      title: "第1部",
      summary: "理想を掲げ旅立つ",
      conflictType: "ideal_vs_reality",
    },
  ],
  episodes: [
    {
      ep_num: 1,
      title: "第1話",
      one_line_summary: "冒険の始まり",
      tension: 40,
      catharsis: 0,
      is_catharsis: false,
      thematic_milestone: "冒険の始まり",
      burned_cost_or_loot: "なし",
      antagonist_status: "強化",
      resolution_style: "Cheat",
    },
  ],
  catharsis_pattern: {
    pattern_type: "explosion",
    catharsis_points: [10],
    tension_wave: [30, 40, 50, 60, 70, 80, 85, 90, 92, 95],
  },
};

const server = setupServer(
  http.post("/easy_mode/reverse-generate", () => {
    return HttpResponse.json(mockPlotResponse);
  })
);

describe("reversePlot API client", () => {
  server.listen();

  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  it("generateReversePlot returns GeneratedPlotStructure on 200", async () => {
    const result = await generateReversePlot(
      {
        emotionalGoal: "triumph",
        sacrifice: "peace",
        coreConflict: "ideal_vs_reality",
        openingHook: "isekai_awakening",
      },
      10,
      "ハイファンタジー (R15)"
    );

    expect(result.arcs).toHaveLength(1);
    expect(result.arcs[0].title).toBe("第1部");
    expect(result.episodes[0].ep_num).toBe(1);
    expect(result.catharsisPattern?.pattern_type).toBe("explosion");
    expect(result.catharsis_pattern?.pattern_type).toBe("explosion");
  });

  it("generateReversePlot throws on error response", async () => {
    server.use(
      http.post("/easy_mode/reverse-generate", () => {
        return HttpResponse.json({ detail: "生成失敗" }, { status: 500 });
      })
    );

    await expect(
      generateReversePlot({ emotionalGoal: "triumph" }, 10, "ファンタジー")
    ).rejects.toThrow("生成失敗");
  });
});
