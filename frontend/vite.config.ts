/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';

// Env files live in the repo root (one level above this frontend package).
const repoRoot = '..';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, repoRoot, '');
  // Reuse the public API base URL so the dev proxy and the app agree on one target.
  const proxyTarget = env.VITE_API_BASE_URL || 'http://localhost:8800';

  return {
    plugins: [react()],
    envDir: repoRoot,
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
        '/health': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/app/testSetup.ts',
      include: ['src/**/*.test.{ts,tsx}'],
      exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    },
  };
});
