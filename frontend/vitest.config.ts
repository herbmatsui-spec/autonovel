import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  test: {
    globals: true,
    setupFilesAfterEnv: ['./src/test/setup.ts'],
    environment: 'jsdom',
    exclude: ['e2e/**/*.spec.ts', '**/node_modules/**'],
  },
});
