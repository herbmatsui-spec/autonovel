import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConflictReportPanel, ConflictReport } from "../../src/components/editor/ConflictReportPanel";

describe("ConflictReportPanel component", () => {
  const sampleReport: ConflictReport = {
    book_id: 1,
    ep_num: 1,
    patch_review_id: 101,
    summary: "スコア80点。文長リズムに若干の乱れあり。",
    total_count: 2,
    critical_count: 1,
    high_count: 1,
    medium_count: 0,
    low_count: 0,
    conflicts: [
      {
        category: "cliche",
        severity: "critical",
        title: "AI定型表現: 言うまでもない",
        description: "頻出表現が含まれています",
        field_path: "p1",
        current_value: "言うまでもないが彼が勇者だ。",
        suggested_value: "彼こそが選ばれし勇者だった。",
        evidence_past: "",
        evidence_current: "",
        constraint_for_next: "",
        confidence: 0.95,
      },
      {
        category: "dialogue",
        severity: "high",
        title: "会話文比率の低下",
        description: "会話文比率が低めです",
        field_path: null,
        current_value: null,
        suggested_value: null,
        evidence_past: "",
        evidence_current: "",
        constraint_for_next: "",
        confidence: 0.85,
      },
    ],
  };

  it("renders conflict cards and severity badges correctly", () => {
    render(<ConflictReportPanel report={sampleReport} />);

    expect(screen.getByText("⚠️ 矛盾・二層監査レポート - 第1話")).toBeInTheDocument();
    expect(screen.getByText("AI定型表現: 言うまでもない")).toBeInTheDocument();
    expect(screen.getByText("会話文比率の低下")).toBeInTheDocument();
    expect(screen.getByText("緊急")).toBeInTheDocument();
    expect(screen.getByText("高")).toBeInTheDocument();
  });

  it("switches to diff tab when conflict is selected", async () => {
    const user = userEvent.setup();
    render(<ConflictReportPanel report={sampleReport} />);

    // 最初は詳細diffボタンは無効
    const diffTab = screen.getByRole("button", { name: "詳細diff" });
    expect(diffTab).toBeDisabled();

    // カードをクリックして選択
    const card = screen.getByText("AI定型表現: 言うまでもない");
    await user.click(card);

    expect(diffTab).not.toBeDisabled();
    await user.click(diffTab);

    expect(screen.getByText("現在の値")).toBeInTheDocument();
    expect(screen.getByText("推奨値")).toBeInTheDocument();
    expect(screen.getByText("言うまでもないが彼が勇者だ。")).toBeInTheDocument();
    expect(screen.getByText("彼こそが選ばれし勇者だった。")).toBeInTheDocument();
  });

  it("triggers onApprove when approve button is clicked in actions tab", async () => {
    const user = userEvent.setup();
    const handleApprove = vi.fn();

    render(
      <ConflictReportPanel
        report={sampleReport}
        onApprove={handleApprove}
      />
    );

    const actionsTab = screen.getByRole("button", { name: "アクション" });
    await user.click(actionsTab);

    const approveBtn = screen.getByRole("button", { name: "パッチを適用して承認" });
    await user.click(approveBtn);

    expect(handleApprove).toHaveBeenCalledWith(101);
  });

  it("renders empty state with AI audit trigger button when no conflicts exist", async () => {
    const user = userEvent.setup();
    const handleRunAudit = vi.fn();

    const emptyReport: ConflictReport = {
      book_id: 1,
      ep_num: 1,
      patch_review_id: null,
      summary: "",
      total_count: 0,
      critical_count: 0,
      high_count: 0,
      medium_count: 0,
      low_count: 0,
      conflicts: [],
    };

    render(
      <ConflictReportPanel
        report={emptyReport}
        onRunAudit={handleRunAudit}
      />
    );

    expect(screen.getByText("矛盾やAI定型表現は検出されませんでした")).toBeInTheDocument();
    const runBtn = screen.getByTestId("btn-run-audit-panel");
    expect(runBtn).toHaveTextContent("🧠 AI二層診断を実行する");

    await user.click(runBtn);
    expect(handleRunAudit).toHaveBeenCalledTimes(1);
  });
});
