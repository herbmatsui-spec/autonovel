import { vi } from 'vitest';

// DEBUG: confirm setup file execution
console.log('✅ setup.ts executed');

// mock import.meta.env for Vite
Object.defineProperty(globalThis, 'import', {
  value: {
    meta: {
      env: {
        VITE_API_URL: '/api',
      },
    },
  },
  writable: true,
  configurable: true,
});

// No need to stub import with vi.stubGlobal; the property is now writable.

// mock global config object to avoid undefined errors
globalThis.config = {};
