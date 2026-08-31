import "@testing-library/jest-dom/vitest";
import { beforeAll, afterEach, afterAll, vi } from "vitest";

beforeAll(() => {
  if (typeof window !== "undefined") {
    window.URL.createObjectURL = vi.fn(() => "blob:http://localhost/mock");
    window.URL.revokeObjectURL = vi.fn();
  }
});

afterEach(() => {
  vi.clearAllMocks();
});

afterAll(() => {});
