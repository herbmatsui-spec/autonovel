import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";
import GraphVisualization from "../../src/components/GraphVisualization";

// Mock react-force-graph-2d for jsdom canvas compatibility
vi.mock("react-force-graph-2d", () => {
  return {
    default: React.forwardRef(({ graphData, onNodeClick }: { graphData: { nodes: Array<{ id: string; label?: string }>; links: unknown[] }; onNodeClick?: (node: { id: string; label?: string }) => void }, ref: React.ForwardedRef<{ zoomToFit: () => void }>) => {
      React.useImperativeHandle(ref, () => ({
        zoomToFit: vi.fn(),
      }));

      return (
        <div data-testid="mock-force-graph">
          <div data-testid="nodes-count">{graphData.nodes.length}</div>
          <div data-testid="links-count">{graphData.links.length}</div>
          {graphData.nodes.map((node: { id: string; label?: string }) => (
            <button
              key={node.id}
              data-testid={`node-${node.id}`}
              onClick={() => onNodeClick && onNodeClick(node)}
            >
              {node.id} ({node.label})
            </button>
          ))}
        </div>
      );
    }),
  };
});

describe("GraphVisualization Component", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state initially and then displays force graph data", async () => {
    const mockData = {
      graph_name: "autonovel_graph",
      nodes: [
        { id: "アルス", label: "Character", properties: { level: 10 } },
        { id: "聖剣", label: "Item", properties: { type: "weapon" } },
      ],
      edges: [
        { source: "アルス", target: "聖剣", type: "POSSESSES" },
      ],
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    } as unknown as Response);

    render(<GraphVisualization />);

    expect(screen.getByText("⚡ グラフデータをロード中...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("mock-force-graph")).toBeInTheDocument();
      expect(screen.getByText("アルス (Character)")).toBeInTheDocument();
      expect(screen.getByText("聖剣 (Item)")).toBeInTheDocument();
    });
  });

  it("selects a node on click and displays properties in sidebar", async () => {
    const mockData = {
      graph_name: "autonovel_graph",
      nodes: [
        { id: "アルス", label: "Character", properties: { is_alive: true, level: 99 } },
      ],
      edges: [],
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    } as unknown as Response);

    render(<GraphVisualization />);

    await waitFor(() => {
      expect(screen.getByText("アルス (Character)")).toBeInTheDocument();
    });

    const nodeBtn = screen.getByTestId("node-アルス");
    fireEvent.click(nodeBtn);

    expect(screen.getByText("アルス")).toBeInTheDocument();
    expect(screen.getAllByText("Character").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/is_alive/)).toBeInTheDocument();
  });

  it("filters nodes by type when filter button is clicked", async () => {
    const mockData = {
      graph_name: "autonovel_graph",
      nodes: [
        { id: "アルス", label: "Character" },
        { id: "王都ルミナス", label: "Location" },
      ],
      edges: [],
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    } as unknown as Response);

    render(<GraphVisualization />);

    await waitFor(() => {
      expect(screen.getByText("アルス (Character)")).toBeInTheDocument();
      expect(screen.getByText("王都ルミナス (Location)")).toBeInTheDocument();
    });

    // Click Location filter
    fireEvent.click(screen.getByText("Location"));

    expect(screen.queryByText("アルス (Character)")).not.toBeInTheDocument();
    expect(screen.getByText("王都ルミナス (Location)")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", async () => {
    const onClose = vi.fn();
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({ graph_name: "test", nodes: [], edges: [] }),
    } as unknown as Response);

    render(<GraphVisualization onClose={onClose} />);

    const closeBtn = screen.getByLabelText("閉じる");
    fireEvent.click(closeBtn);

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
