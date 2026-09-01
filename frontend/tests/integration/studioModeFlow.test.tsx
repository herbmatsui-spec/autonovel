import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../../src/App";

describe("Studio Mode Flow Integration Test", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders Studio mode by default and allows mode switching", async () => {
    render(<App />);

    // 初期表示で Studio ワークスペースが表示されている
    expect(screen.getByTestId("studio-workspace")).toBeInTheDocument();
    expect(screen.getByTestId("editorial-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("next-beats-panel")).toBeInTheDocument();

    // かんたんモードに切り替え
    const easyBtn = screen.getByTestId("btn-mode-easy");
    fireEvent.click(easyBtn);

    // かんたんモードの UI が表示される
    expect(screen.getByText("⚙️ 制作設定 & プロンプト")).toBeInTheDocument();
    expect(screen.getByText("📦 ZIP・EPUB 出力パッケージ")).toBeInTheDocument();

    // 再度 Studio モードに切り替え
    const studioBtn = screen.getByTestId("btn-mode-studio");
    fireEvent.click(studioBtn);
    expect(screen.getByTestId("studio-workspace")).toBeInTheDocument();
  });

  it("allows asking questions in EditorialSidebar (Ask Bible)", async () => {
    const mockBibleResponse = {
      answer: "アルトは第1章で王都ルミナスの地下遺跡から古代魔導剣を入手しました。",
      evidence_nodes: [
        { id: "古代魔導剣", label: "Item", properties: {}, source_reference: "第1章" },
      ],
      related_characters: ["アルト"],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockBibleResponse,
    } as any);

    render(<App />);

    const input = screen.getByTestId("input-ask-bible");
    fireEvent.change(input, { target: { value: "アルトの剣はどこで手に入れた？" } });

    const submitBtn = screen.getByTestId("btn-submit-ask-bible");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/アルトは第1章で王都ルミナスの地下遺跡から/)).toBeInTheDocument();
      expect(screen.getAllByText(/古代魔導剣/).length).toBeGreaterThan(0);
    });
  });

  it("generates Next Beats and applies content to editor", async () => {
    const mockNextBeatsResponse = {
      beats: [
        {
          card_id: "card_a",
          branch_type: "royal",
          title: "【王道】逆転の一閃",
          summary: "アルトの反撃",
          content: "アルトの剣が閃光を放ち、敵を圧倒した。",
          hook_text: "しかし背後に新たな影が。",
        },
      ],
      original_tail: "...",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockNextBeatsResponse,
    } as any);

    render(<App />);

    const generateBeatsBtn = screen.getByTestId("btn-generate-beats");
    fireEvent.click(generateBeatsBtn);

    await waitFor(() => {
      expect(screen.getByTestId("beat-card-card_a")).toBeInTheDocument();
      expect(screen.getByText("【王道】逆転の一閃")).toBeInTheDocument();
    });

    // 「本文に追記」ボタンをクリック
    const applyBtn = screen.getByTestId("btn-apply-beat-card_a");
    fireEvent.click(applyBtn);

    const textarea = screen.getByTestId("editor-textarea") as HTMLTextAreaElement;
    expect(textarea.value).toContain("アルトの剣が閃光を放ち、敵を圧倒した。");
  });
});
