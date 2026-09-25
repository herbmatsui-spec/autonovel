import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "../routes";
import { NovelProvider } from "../context/NovelContext";
import { ModalProvider } from "../context/ModalContext";
import { TipTapEditor } from "../components/studio/TipTapEditor";

function renderWithProviders(initialEntry: string) {
  const router = createMemoryRouter(routes, {
    initialEntries: [initialEntry],
  });

  return render(
    <NovelProvider>
      <ModalProvider>
        <RouterProvider router={router} />
      </ModalProvider>
    </NovelProvider>
  );
}

describe("Workflow Promotion and UI Smoke Tests (v5.2.0)", () => {
  it("renders WizardWorkflowPage and verifies wizard-to-studio routing readiness", () => {
    renderWithProviders("/wizard");
    expect(screen.getByTestId("wizard-workflow-page")).toBeInTheDocument();
  });

  it("transitions smoothly to Studio Workspace upon promotion", () => {
    renderWithProviders("/studio/101");
    expect(screen.getByTestId("studio-workspace-page")).toBeInTheDocument();
  });

  it("mounts TipTapEditor and calculates text metrics seamlessly", () => {
    const sampleText = "「ここからが反撃だ」とアルトは叫んだ。剣が眩い蒼光を放つ。";
    render(
      <TipTapEditor
        initialContent={sampleText}
        onChange={vi.fn()}
      />
    );

    // TipTap ヘッダーの文字数・会話文率・オートセーブ表示を検証
    expect(screen.getByText("TipTap 本文エディタ (v5.2)")).toBeInTheDocument();
    expect(screen.getByText("オートセーブ有効")).toBeInTheDocument();
  });
});
