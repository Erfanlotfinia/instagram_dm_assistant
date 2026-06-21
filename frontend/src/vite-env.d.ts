/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_PUBLIC_API_BASE_URL?: string;
  readonly VITE_LANDING_URL?: string;
  readonly VITE_DEFAULT_ADMIN_EMAIL?: string;
  readonly VITE_DEFAULT_ADMIN_PASSWORD?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module '*.css' {
  const content: string;
  export default content;
}
