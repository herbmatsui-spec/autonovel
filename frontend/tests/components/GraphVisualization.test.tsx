import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import GraphVisualization from "../../src/components/GraphVisualization";

// ForceGraph2D のモック
vi.mock("react-force-graph-2d", () => ({
  default: () => <div data-testid="mock-force-graph">Mock Force Graph</div>,
}));

vi.mock("../../src/api/graph", () => ({
  fetchGraphData: vi.fn().mockResolvedValue({
    graph_name: "autonovel_graph",
    nodes: [
      { id: "アルト", label: "Character", properties: { role: "主人公" } },
      { id: "王都ルミナス", label: "Location", properties: { type: "都市" } },
    ],
    edges: [
      { source: "アルト", target: "王都ルミナス", type: "LOCATED_IN" },
    ],
  }),
}));

describe("GraphVisualization component", () => {
  it("renders graph modal, filters and responds to close", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<GraphVisualization onClose={onClose} />);

    expect(await screen.findByText(/AutoNovel 物理演算ナレッジグラフ/)).toBeInTheDocument();
    expect(screen.getByTestId("mock-force-graph")).toBeInTheDocument();

    // フィルタボタンの存在確認
    expect(screen.getByRole("button", { name: "Character" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Location" })).toBeInTheDocument();

    // 閉じるボタン
    const closeBtn = screen.getByRole("button", { name: "閉じる" });
    await user.click(closeBtn);
    expect(onClose).toHaveBeenCalled();
  });
});
