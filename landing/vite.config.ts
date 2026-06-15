import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { loadEnv } from 'vite';
import { defineConfig } from 'vite';

const DEFAULT_LANDING_PORT = 5174;

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const port = Number(env.LANDING_PORT || process.env.LANDING_PORT || DEFAULT_LANDING_PORT);

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port,
      host: true,
      strictPort: true,
    },
    preview: {
      port,
      host: true,
      strictPort: true,
    },
  };
});
