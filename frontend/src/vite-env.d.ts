/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_DEMO_MODE?: "true" | "false";
  readonly VITE_PUBLIC_DEMO_ONLY?: "true" | "false";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
