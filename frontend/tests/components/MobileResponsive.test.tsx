import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MobileBottomNav } from "../../src/components/mobile/MobileBottomNav";
import { MobileQuickActionBar } from "../../src/components/mobile/MobileQuickActionBar";
import { MobileChapterDrawer } from "../../src/components/mobile/MobileChapterDrawer";

describe("Mobile Responsive Components (Plan 17)", () => {
  it("renders MobileBottomNav with tabs and triggers onTabChange", () => {
    const onTabChange = vi.fn();
    render(<MobileBottomNav activeTab="writing" onTabChange={onTabChange} />);

    expect(screen.getByText("作品一覧")).toBeInTheDocument();
    expect(screen.getByText("プロット")).toBeInTheDocument();
    expect(screen.getByText("執筆・推敲")).toBeInTheDocument();
    expect(screen.getByText("設定")).toBeInTheDocument();

    fireEvent.click(screen.getByText("プロット"));
    expect(onTabChange).toHaveBeenCalledWith("plots");
  });

  it("renders MobileQuickActionBar and triggers text insertion", () => {
    const onInsert = vi.fn();
    const onAiContinue = vi.fn();
    render(
      <MobileQuickActionBar
        onInsertText={onInsert}
        onAiContinue={onAiContinue}
      />
    );

    expect(screen.getByText("「」")).toBeInTheDocument();
    expect(screen.getByText("🤖 続き")).toBeInTheDocument();

    fireEvent.click(screen.getByText("「」"));
    expect(onInsert).toHaveBeenCalledWith("「」");

    fireEvent.click(screen.getByText("🤖 続き"));
    expect(onAiContinue).toHaveBeenCalled();
  });

  it("renders MobileChapterDrawer and selects chapter", () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();
    const chapters = [
      { id: 1, ep_num: 1, title: "第1話 冒険", status: "完成" },
      { id: 2, ep_num: 2, title: "第2話 遭遇", status: "下書き" },
    ];

    render(
      <MobileChapterDrawer
        isOpen={true}
        onClose={onClose}
        chapters={chapters}
        currentChapterId={1}
        onSelectChapter={onSelect}
      />
    );

    expect(screen.getByText("第1話 冒険")).toBeInTheDocument();
    expect(screen.getByText("第2話 遭遇")).toBeInTheDocument();

    fireEvent.click(screen.getByText("第2話 遭遇"));
    expect(onSelect).toHaveBeenCalledWith(2);
    expect(onClose).toHaveBeenCalled();
  });
});
