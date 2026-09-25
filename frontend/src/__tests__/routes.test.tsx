import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "../routes";
import { NovelProvider } from "../context/NovelContext";
import { ModalProvider } from "../context/ModalContext";

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

describe("Declarative Routes", () => {
  it("renders EasyModePage at root path '/'", () => {
    renderWithProviders("/");
    expect(screen.getByTestId("easy-mode-page")).toBeInTheDocument();
  });

  it("renders StudioWorkspacePage at '/studio'", () => {
    renderWithProviders("/studio");
    expect(screen.getByTestId("studio-workspace-page")).toBeInTheDocument();
  });

  it("renders StudioWorkspacePage with bookId param at '/studio/42'", () => {
    renderWithProviders("/studio/42");
    expect(screen.getByTestId("studio-workspace-page")).toBeInTheDocument();
  });

  it("renders WizardWorkflowPage at '/wizard'", () => {
    renderWithProviders("/wizard");
    expect(screen.getByTestId("wizard-workflow-page")).toBeInTheDocument();
  });
});
