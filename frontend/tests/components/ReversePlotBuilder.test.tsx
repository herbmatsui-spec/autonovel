import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReversePlotBuilder } from "../../src/components/ReversePlotBuilder";

vi.mock("../../src/api/reversePlot", () => ({
  generateReversePlot: vi.fn().mockResolvedValue({
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
        title: "運命の覚醒",
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
    catharsisPattern: {
      pattern_type: "explosion",
      catharsis_points: [10],
      tension_wave: [30, 40, 50],
    },
  }),
}));

describe("ReversePlotBuilder component", () => {
  it("walks through 4 steps and completes generation", async () => {
    const onComplete = vi.fn();
    const onCancel = vi.fn();
    const user = userEvent.setup();

    render(
      <ReversePlotBuilder
        onComplete={onComplete}
        onCancel={onCancel}
        targetEpisodes={10}
        genre="ハイファンタジー (R15)"
      />
    );

    // Step 1: 感情的ゴール
    expect(screen.getAllByText(/最終話で読者に残したい感情/)[0]).toBeInTheDocument();
    const opt1 = screen.getByTestId("option-triumph");
    await user.click(opt1);
    await user.click(screen.getByTestId("btn-next-step"));

    // Step 2: 犠牲
    expect(screen.getAllByText(/主人公が払う最大の代償/)[0]).toBeInTheDocument();
    const opt2 = screen.getByTestId("option-peace");
    await user.click(opt2);
    await user.click(screen.getByTestId("btn-next-step"));

    // Step 3: 核心対立
    expect(screen.getAllByText(/物語を動かす核心の衝突/)[0]).toBeInTheDocument();
    const opt3 = screen.getByTestId("option-ideal_vs_reality");
    await user.click(opt3);
    await user.click(screen.getByTestId("btn-next-step"));

    // Step 4: オープニングフック
    expect(screen.getAllByText(/読者を惹きつける最初のフック/)[0]).toBeInTheDocument();
    const opt4 = screen.getByTestId("option-isekai_awakening");
    await user.click(opt4);

    // プロット構造を生成
    await user.click(screen.getByTestId("btn-generate-plot"));

    // プレビュー表示確認
    expect(await screen.findByTestId("reverse-plot-preview")).toBeInTheDocument();
    expect(screen.getByText(/第1部/)).toBeInTheDocument();
    expect(screen.getByText(/運命の覚醒/)).toBeInTheDocument();

    // 確定
    await user.click(screen.getByTestId("btn-confirm-plot"));
    expect(onComplete).toHaveBeenCalledWith(
      expect.objectContaining({
        arcs: expect.any(Array),
        episodes: expect.any(Array),
      })
    );
  });
});
