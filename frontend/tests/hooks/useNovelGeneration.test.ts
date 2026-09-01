import { renderHook, act } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { NovelProvider } from "../src/context/NovelContext";
import { useNovelGeneration } from "../src/hooks/useNovelGeneration";

describe("useNovelGeneration hook", () => {
  it("initial state has no task ID", () => {
    const { result } = renderHook(
      () => useNovelGeneration(),
      { wrapper: ({ children }) => <NovelProvider>{children}</NovelProvider> }
    );
    expect(typeof result.startGeneration).toBe("function");
    expect(typeof result.cancelGeneration).toBe("function");
  });

  it("startGeneration is a function", () => {
    const { result } = renderHook(
      () => useNovelGeneration(),
      { wrapper: ({ children }) => <NovelProvider>{children}</NovelProvider> }
    );
    expect(typeof result.current.startGeneration).toBe("function");
  });

  it("cancelGeneration is a function", () => {
    const { result } = renderHook(
      () => useNovelGeneration(),
      { wrapper: ({ children }) => <NovelProvider>{children}</NovelProvider> }
    );
    expect(typeof result.current.cancelGeneration).toBe("function");
  });
});