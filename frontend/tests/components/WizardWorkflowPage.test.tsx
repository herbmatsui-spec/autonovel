import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, waitForElementToBeRemoved } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WizardWorkflowPage } from "../../src/pages/WizardWorkflowPage";
import * as wizardApi from "../../src/api/wizard";

// モック用のビートデータ
const mockBeats: wizardApi.BeatItem[] = [
  {
    episode: 1,
    title: "日常の崩壊",
    outline: "主人公の平穏な日常が崩れる",
    cliffhanger_type: "New Crisis",
    sensory_focus: ["visual", "auditory"],
    foreshadowing_notes: "不穏な予兆",
  },
  {
    episode: 2,
    title: "運命の告知",
    outline: "使命が課せられる",
    cliffhanger_type: "Shocking Truth",
    sensory_focus: ["tactile"],
    foreshadowing_notes: "古い予言",
  },
  {
    episode: 3,
    title: "覚悟の決意",
    outline: "立ち向かうことを決意",
    cliffhanger_type: "Quiet Foreshadowing",
    sensory_focus: ["visual"],
    foreshadowing_notes: "",
  },
];

describe("WizardWorkflowPage - 3ステップ進行", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("Step 1 が表示される", () => {
    render(<WizardWorkflowPage />);
    expect(screen.getByText("Step 1: 企画アイデアと成長曲線の設計")).toBeInTheDocument();
  });

  it("フォームバリデーション: タイトル未入力でエラー表示", async () => {
    const user = userEvent.setup();
    render(<WizardWorkflowPage />);

    // あらすじだけ入力してタイトルは空のまま
    const synopsisInput = screen.getByPlaceholderText("主人公の特技、最初の事件、物語のゴールなどを自由に記述");
    await user.type(synopsisInput, "テストあらすじ");

    const submitBtn = screen.getByRole("button", { name: /次へ/ });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("作品タイトルを入力してください")).toBeInTheDocument();
    });
  });

  it("フォームバリデーション: あらすじ未入力でエラー表示", async () => {
    const user = userEvent.setup();
    render(<WizardWorkflowPage />);

    const titleInput = screen.getByPlaceholderText("例: 魔王の娘に転生した鍛冶屋の日常");
    await user.type(titleInput, "テスト作品");

    const submitBtn = screen.getByRole("button", { name: /次へ/ });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("あらすじ・コアアイデアを入力してください")).toBeInTheDocument();
    });
  });

  it("Step 1 → Step 2 正常遷移: expandBeats を呼び出しビート確認画面へ", async () => {
    const user = userEvent.setup();
    const expandBeatsSpy = vi.spyOn(wizardApi, "expandBeats").mockResolvedValue(mockBeats);

    render(<WizardWorkflowPage />);

    const titleInput = screen.getByPlaceholderText("例: 魔王の娘に転生した鍛冶屋の日常");
    const synopsisInput = screen.getByPlaceholderText("主人公の特技、最初の事件、物語のゴールなどを自由に記述");
    await user.type(titleInput, "テスト作品");
    await user.type(synopsisInput, "テストあらすじ");

    const submitBtn = screen.getByRole("button", { name: /次へ/ });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Step 2: 全章構成と五感ビート・引きの確認")).toBeInTheDocument();
    });

    expect(expandBeatsSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "テスト作品",
        synopsis: "テストあらすじ",
      })
    );

    // 生成されたビートが表示されている
    expect(screen.getByDisplayValue("日常の崩壊")).toBeInTheDocument();
  });

  it("Step 1: expandBeats 失敗時にエラー表示され遷移しない", async () => {
    const user = userEvent.setup();
    vi.spyOn(wizardApi, "expandBeats").mockRejectedValue(new Error("ネットワークエラー"));

    render(<WizardWorkflowPage />);

    const titleInput = screen.getByPlaceholderText("例: 魔王の娘に転生した鍛冶屋の日常");
    const synopsisInput = screen.getByPlaceholderText("主人公の特技、最初の事件、物語のゴールなどを自由に記述");
    await user.type(titleInput, "テスト作品");
    await user.type(synopsisInput, "テストあらすじ");

    const submitBtn = screen.getByRole("button", { name: /次へ/ });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("ネットワークエラー")).toBeInTheDocument();
    });

    // Step 1 のまま
    expect(screen.getByText("Step 1: 企画アイデアと成長曲線の設計")).toBeInTheDocument();
  });

  it("Step 1 ローディングスピナー表示", async () => {
    const user = userEvent.setup();
    // 遅延Promiseでローディング状態を再現
    vi.spyOn(wizardApi, "expandBeats").mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(mockBeats), 100))
    );

    render(<WizardWorkflowPage />);

    const titleInput = screen.getByPlaceholderText("例: 魔王の娘に転生した鍛冶屋の日常");
    const synopsisInput = screen.getByPlaceholderText("主人公の特技、最初の事件、物語のゴールなどを自由に記述");
    await user.type(titleInput, "テスト作品");
    await user.type(synopsisInput, "テストあらすじ");

    const submitBtn = screen.getByRole("button", { name: /次へ/ });
    await user.click(submitBtn);

    // ローディング中
    expect(screen.getByText("AIアイデア生成中...")).toBeInTheDocument();

    // 完了後 Step 2 へ
    await waitFor(() => {
      expect(screen.getByText("Step 2: 全章構成と五感ビート・引きの確認")).toBeInTheDocument();
    });
  });

  it("Step 2 → Step 3 正常遷移: saveWizardBook を呼び出し執筆画面へ", async () => {
    const user = userEvent.setup();
    vi.spyOn(wizardApi, "expandBeats").mockResolvedValue(mockBeats);
    const saveWizardBookSpy = vi.spyOn(wizardApi, "saveWizardBook").mockResolvedValue({
      book_id: 1,
      branch_id: 1,
      success: true,
    });

    render(<WizardWorkflowPage />);

    // Step 1 完了
    const titleInput = screen.getByPlaceholderText("例: 魔王の娘に転生した鍛冶屋の日常");
    const synopsisInput = screen.getByPlaceholderText("主人公の特技、最初の事件、物語のゴールなどを自由に記述");
    await user.type(titleInput, "テスト作品");
    await user.type(synopsisInput, "テストあらすじ");
    await user.click(screen.getByRole("button", { name: /次へ/ }));

    await waitFor(() => {
      expect(screen.getByText("Step 2: 全章構成と五感ビート・引きの確認")).toBeInTheDocument();
    });

    // Step 2 確定
    await user.click(screen.getByRole("button", { name: /構成を確定して執筆を開始する/ }));

    await waitFor(() => {
      expect(saveWizardBookSpy).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText(/第1話/)).toBeInTheDocument();
    });
  });

  it("Step 2: saveWizardBook 失敗時も Step 3 へ遷移する（オフライン許容）", async () => {
    const user = userEvent.setup();
    vi.spyOn(wizardApi, "expandBeats").mockResolvedValue(mockBeats);
    vi.spyOn(wizardApi, "saveWizardBook").mockRejectedValue(new Error("DB保存エラー"));

    render(<WizardWorkflowPage />);

    // Step 1 完了
    const titleInput = screen.getByPlaceholderText("例: 魔王の娘に転生した鍛冶屋の日常");
    const synopsisInput = screen.getByPlaceholderText("主人公の特技、最初の事件、物語のゴールなどを自由に記述");
    await user.type(titleInput, "テスト作品");
    await user.type(synopsisInput, "テストあらすじ");
    await user.click(screen.getByRole("button", { name: /次へ/ }));

    await waitFor(() => {
      expect(screen.getByText("Step 2: 全章構成と五感ビート・引きの確認")).toBeInTheDocument();
    });

    // Step 2 確定
    await user.click(screen.getByRole("button", { name: /構成を確定して執筆を開始する/ }));

    // エラー表示されるが Step 3 へ遷移
    await waitFor(() => {
      expect(screen.getByText(/第1話/)).toBeInTheDocument();
    });
  });

  it("Step 2: ビート追加・削除機能", async () => {
    const user = userEvent.setup();
    vi.spyOn(wizardApi, "expandBeats").mockResolvedValue(mockBeats);
    vi.spyOn(wizardApi, "saveWizardBook").mockResolvedValue({
      book_id: 1,
      branch_id: 1,
      success: true,
    });

    render(<WizardWorkflowPage />);

    // Step 1 完了
    const titleInput = screen.getByPlaceholderText("例: 魔王の娘に転生した鍛冶屋の日常");
    const synopsisInput = screen.getByPlaceholderText("主人公の特技、最初の事件、物語のゴールなどを自由に記述");
    await user.type(titleInput, "テスト作品");
    await user.type(synopsisInput, "テストあらすじ");
    await user.click(screen.getByRole("button", { name: /次へ/ }));

    await waitFor(() => {
      expect(screen.getByText("Step 2: 全章構成と五感ビート・引きの確認")).toBeInTheDocument();
    });

    // ビートを追加
    await user.click(screen.getByRole("button", { name: /ビートを追加/ }));
    expect(screen.getByText(/未保存の変更があります/)).toBeInTheDocument();

    // 最初のビートを削除
    const deleteButtons = screen.getAllByTitle("削除");
    await user.click(deleteButtons[0]);
  });

  it("Step 2: 戻るボタンで Step 1 に戻る", async () => {
    const user = userEvent.setup();
    vi.spyOn(wizardApi, "expandBeats").mockResolvedValue(mockBeats);

    render(<WizardWorkflowPage />);

    // Step 1 完了
    const titleInput = screen.getByPlaceholderText("例: 魔王の娘に転生した鍛冶屋の日常");
    const synopsisInput = screen.getByPlaceholderText("主人公の特技、最初の事件、物語のゴールなどを自由に記述");
    await user.type(titleInput, "テスト作品");
    await user.type(synopsisInput, "テストあらすじ");
    await user.click(screen.getByRole("button", { name: /次へ/ }));

    await waitFor(() => {
      expect(screen.getByText("Step 2: 全章構成と五感ビート・引きの確認")).toBeInTheDocument();
    });

    // 戻る
    await user.click(screen.getByRole("button", { name: /戻ってプロットを修正/ }));

    await waitFor(() => {
      expect(screen.getByText("Step 1: 企画アイデアと成長曲線の設計")).toBeInTheDocument();
    });
  });

  it("タイムアウト時のエラーハンドリング", async () => {
    const user = userEvent.setup();
    vi.spyOn(wizardApi, "expandBeats").mockRejectedValue(
      new Error("リクエストがタイムアウトしました（30秒）。しばらくしてから再試行してください。")
    );

    render(<WizardWorkflowPage />);

    const titleInput = screen.getByPlaceholderText("例: 魔王の娘に転生した鍛冶屋の日常");
    const synopsisInput = screen.getByPlaceholderText("主人公の特技、最初の事件、物語のゴールなどを自由に記述");
    await user.type(titleInput, "テスト作品");
    await user.type(synopsisInput, "テストあらすじ");

    await user.click(screen.getByRole("button", { name: /次へ/ }));

    await waitFor(() => {
      expect(screen.getByText(/タイムアウト/)).toBeInTheDocument();
    });
  });
});