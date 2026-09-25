import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { ModalProvider, useModal } from "../context/ModalContext";

function TestComponent() {
  const {
    isOpen,
    openModal,
    closeModal,
    showConfig,
    setShowConfig,
    closeAll,
  } = useModal();

  return (
    <div>
      <div data-testid="graph-status">{isOpen("graph") ? "open" : "closed"}</div>
      <div data-testid="config-status">{showConfig ? "open" : "closed"}</div>
      <button onClick={() => openModal("graph")} data-testid="btn-open-graph">
        Open Graph
      </button>
      <button onClick={() => closeModal("graph")} data-testid="btn-close-graph">
        Close Graph
      </button>
      <button onClick={() => setShowConfig(true)} data-testid="btn-open-config">
        Open Config
      </button>
      <button onClick={closeAll} data-testid="btn-close-all">
        Close All
      </button>
    </div>
  );
}

describe("ModalContext", () => {
  it("initializes with all modals closed", () => {
    render(
      <ModalProvider>
        <TestComponent />
      </ModalProvider>
    );

    expect(screen.getByTestId("graph-status").textContent).toBe("closed");
    expect(screen.getByTestId("config-status").textContent).toBe("closed");
  });

  it("opens and closes specific modal via openModal/closeModal", () => {
    render(
      <ModalProvider>
        <TestComponent />
      </ModalProvider>
    );

    act(() => {
      screen.getByTestId("btn-open-graph").click();
    });
    expect(screen.getByTestId("graph-status").textContent).toBe("open");

    act(() => {
      screen.getByTestId("btn-close-graph").click();
    });
    expect(screen.getByTestId("graph-status").textContent).toBe("closed");
  });

  it("opens modal via explicit setter and closes all via closeAll", () => {
    render(
      <ModalProvider>
        <TestComponent />
      </ModalProvider>
    );

    act(() => {
      screen.getByTestId("btn-open-graph").click();
      screen.getByTestId("btn-open-config").click();
    });
    expect(screen.getByTestId("graph-status").textContent).toBe("open");
    expect(screen.getByTestId("config-status").textContent).toBe("open");

    act(() => {
      screen.getByTestId("btn-close-all").click();
    });
    expect(screen.getByTestId("graph-status").textContent).toBe("closed");
    expect(screen.getByTestId("config-status").textContent).toBe("closed");
  });

  it("throws error when useModal is called outside ModalProvider", () => {
    // Suppress console.error for expected error boundary test
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<TestComponent />)).toThrow(
      "useModal must be used within a ModalProvider"
    );
    spy.mockRestore();
  });
});
