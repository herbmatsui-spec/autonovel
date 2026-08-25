import { vi } from 'vitest';

// mock import.meta.env for Vite
Object.defineProperty(globalThis, 'import', {
  value: {
    meta: {
      env: {
        VITE_API_URL: '/api',
      },
    },
  },
});

vi.stubGlobal('import', globalThis.import);

// mock global config object to avoid undefined errors
globalThis.config = {};
