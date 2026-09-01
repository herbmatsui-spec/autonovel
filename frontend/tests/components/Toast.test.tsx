import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Toast } from "../../src/components/common/Toast";
import { ToastContainer } from "../../src/components/common/ToastContainer";
import { ToastNotification } from "../../src/types";

describe("Toast Component", () => {
  it("renders success toast with message and icon", () => {
    const toast: ToastNotification = {
      id: "1",
      type: "success",
      message: "生成が完了しました",
    };
    const onClose = vi.fn();
    render(<Toast toast={toast} onClose={onClose} />);

    expect(screen.getByText("生成が完了しました")).toBeInTheDocument();
    expect(screen.getByText("✨")).toBeInTheDocument();

    const closeBtn = screen.getByLabelText("閉じる");
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledWith("1");
  });

  it("renders error and info toasts correctly", () => {
    const errorToast: ToastNotification = {
      id: "2",
      type: "error",
      message: "エラーが発生しました",
    };
    const { rerender } = render(<Toast toast={errorToast} onClose={vi.fn()} />);
    expect(screen.getByText("❌")).toBeInTheDocument();

    const infoToast: ToastNotification = {
      id: "3",
      type: "info",
      message: "進行中",
    };
    rerender(<Toast toast={infoToast} onClose={vi.fn()} />);
    expect(screen.getByText("ℹ️")).toBeInTheDocument();
  });

  it("renders multiple toasts in ToastContainer", () => {
    const toasts: ToastNotification[] = [
      { id: "1", type: "success", message: "Toast 1" },
      { id: "2", type: "info", message: "Toast 2" },
    ];
    render(<ToastContainer toasts={toasts} onClose={vi.fn()} />);
    expect(screen.getByText("Toast 1")).toBeInTheDocument();
    expect(screen.getByText("Toast 2")).toBeInTheDocument();
  });
});
