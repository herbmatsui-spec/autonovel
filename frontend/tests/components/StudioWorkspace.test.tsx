import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StudioWorkspace } from "../../src/components/studio/StudioWorkspace";
import { NovelProvider } from "../../src/context/NovelContext";
import * as editorApi from "../../src/api/editor";

vi.mock("../../src/api/editor", () => ({
  askBible: vi.fn().mockResolvedValue({
    answer: "アルトの古代魔導剣術は、300年前の王国滅亡時に失われた秘術です。",
    evidence_nodes: [
      { id: "concept_ancient_sword", label: "設定", source_reference: "設定資料p.1" },
    ],
  }),
  auditConsistency: vi.fn().mockResolvedValue({
    has_issues: false,
    issues: [],
  }),
  assistContent: vi.fn().mockResolvedValue({
    result_text: "冷たい刃が月光に青く妖しく輝いていた。",
    diff_summary: "視覚描写の補強",
  }),
  generateNextBeats: vi.fn().mockResolvedValue({
    beats: [
      {
        beat_id: "beat_1",
        label: "伏兵の出現",
        summary: "影から暗殺者が襲いかかる",
        expected_development: "戦闘勃発",
        tension_score: 80,
      },
    ],
  }),
}));

describe("StudioWorkspace component", () => {
  it("renders studio components with synchronized context data", async () => {
    const user = userEvent.setup();

    render(
      <NovelProvider>
        <StudioWorkspace />
      </NovelProvider>
    );

    // 左ペインに NovelContext の初期値が反映されていること
    expect(screen.getByDisplayValue("アルト")).toBeInTheDocument();

    // 中央エディタに初期テキストが存在すること
    expect(screen.getByTestId("editor-textarea")).toHaveValue(
      "薄暗いダンジョンの中、15歳の青年アルトは古代の剣を手に取った。"
    );

    // Ask Bible の Q&A 送信
    const input = screen.getByTestId("input-ask-bible");
    await user.type(input, "古代魔導剣術の歴史は？");
    await user.click(screen.getByTestId("btn-submit-ask-bible"));

    expect(await screen.findByText(/300年前の王国滅亡時に失われた秘術/)).toBeInTheDocument();
  });
});
