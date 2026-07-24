import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers({
    shouldAdvanceTime: true,
    advanceTimeDelta: 0,
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});
