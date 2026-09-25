import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AudioPlayer } from "../../src/components/common/AudioPlayer";

describe("AudioPlayer Component (Step 35)", () => {
  it("renders with default title and controls", () => {
    render(<AudioPlayer src="/dummy.wav" title="テスト朗読" duration={120} />);
    expect(screen.getByText("🔊 テスト朗読")).toBeInTheDocument();
    expect(screen.getByText("02:00")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "再生" })).toBeInTheDocument();
  });

  it("changes playback speed on speed button click", () => {
    render(<AudioPlayer src="/dummy.wav" duration={60} />);
    const speed15Btn = screen.getByText("1.5x");
    fireEvent.click(speed15Btn);
    expect(speed15Btn).toHaveClass("active");
  });
});
