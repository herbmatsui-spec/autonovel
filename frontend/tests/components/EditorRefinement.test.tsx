import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Editor } from "../../src/components/editor/Editor";
import { ChapterOutlineTree } from "../../src/components/studio/ChapterOutlineTree";
import { StudioWorkspace } from "../../src/components/studio/StudioWorkspace";
import { NovelProvider } from "../../src/context/NovelContext";

describe("Editor component refinements", () => {
  it("displays character count, line count and estimated reading time", () => {
    const handleChange = vi.fn();
    const content = "1行目テストテキスト\n2行目テストテキスト\n3行目テストテキスト";

    render(
      <NovelProvider>
        <Editor content={content} onChange={handleChange} />
      </NovelProvider>
    );

    expect(screen.getByText("3")).toBeInTheDocument(); // 行数: 3行
    expect(screen.getByTestId("editor-char-count")).toHaveTextContent("30");
    expect(screen.getByText(/読了目安:/)).toBeInTheDocument();
  });

  it("inserts ruby syntax when ruby button is clicked", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    const onToast = vi.fn();

    render(
      <NovelProvider>
        <Editor content="勇者アルト" onChange={handleChange} onToast={onToast} />
      </NovelProvider>
    );

    const rubyBtn = screen.getByTestId("btn-insert-ruby");
    await user.click(rubyBtn);

    expect(handleChange).toHaveBeenCalled();
    expect(onToast).toHaveBeenCalledWith(
      expect.stringContaining("ルビ記法"),
      "info"
    );
  });
});

describe("ChapterOutlineTree inline editing", () => {
  it("allows inline editing of chapter title", async () => {
    const user = userEvent.setup();

    render(
      <NovelProvider>
        <ChapterOutlineTree />
      </NovelProvider>
    );

    // タイトル編集ボタンをクリック
    const editBtn = screen.getByTestId("btn-edit-title-1");
    await user.click(editBtn);

    // インライン入力フォームが表示される
    const editInput = screen.getByTestId("input-edit-chapter-title");
    expect(editInput).toBeInTheDocument();

    await user.clear(editInput);
    await user.type(editInput, "第1話 運命の剣{Enter}");

    expect(screen.getByText("第1話 運命の剣")).toBeInTheDocument();
  });
});

describe("StudioWorkspace collapsible sidebars", () => {
  it("toggles left and right sidebars smoothly", async () => {
    const user = userEvent.setup();

    render(
      <NovelProvider>
        <StudioWorkspace />
      </NovelProvider>
    );

    // 初期状態: 左ペイン・右ペインが表示されている
    expect(screen.getByTestId("btn-toggle-left-pane")).toBeInTheDocument();
    expect(screen.getByTestId("btn-toggle-right-pane")).toBeInTheDocument();

    // 左ペインを折りたたむ
    await user.click(screen.getByTestId("btn-toggle-left-pane"));
    expect(screen.queryByTestId("btn-toggle-left-pane")).not.toBeInTheDocument();
    expect(screen.getByTestId("btn-restore-left-pane")).toBeInTheDocument();

    // 左ペインを展開する
    await user.click(screen.getByTestId("btn-restore-left-pane"));
    expect(screen.getByTestId("btn-toggle-left-pane")).toBeInTheDocument();
  });
});
