"use client";

import { renderHook, act } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { useToast } from "../../src/hooks/useToast";

describe("useToast hook", () => {
  it("initially has no toasts", () => {
    const { result } = renderHook(() => useToast());
    expect(result.current.toasts).toHaveLength(0);
  });

  it("addToast adds a new toast", () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.addToast("Test message", "success", 3000);
    });
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe("Test message");
    expect(result.current.toasts[0].type).toBe("success");
    expect(result.current.toasts[0].durationMs).toBe(3000);
  });

  it("removeToast removes a toast by id", () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.addToast("msg1");
      result.current.addToast("msg2");
    });
    // State updates are async, so wait for re-render
    expect(result.current.toasts).toHaveLength(2);
    const firstId = result.current.toasts[0].id;
    act(() => {
      result.current.removeToast(firstId);
    });
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe("msg2");
  });

  it("auto-dismisses after durationMs", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.addToast("Auto-dismiss", "info", 100);
    });
    expect(result.current.toasts).toHaveLength(1);
    act(() => {
      vi.advanceTimersByTime(150);
    });
    expect(result.current.toasts).toHaveLength(0);
    vi.useRealTimers();
  });

  it("multiple toasts can be managed", () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.addToast("First", "success", 0);
      result.current.addToast("Second", "error", 0);
      result.current.addToast("Third", "info", 0);
    });
    expect(result.current.toasts).toHaveLength(3);
    
    // Remove middle one
    act(() => {
      result.current.removeToast(result.current.toasts[1].id);
    });
    expect(result.current.toasts).toHaveLength(2);
    expect(result.current.toasts[0].message).toBe("First");
    expect(result.current.toasts[1].message).toBe("Third");
  });
});