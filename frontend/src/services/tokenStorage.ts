// JWTs are stored in HttpOnly cookies by the backend. This compatibility shim
// intentionally never persists tokens in browser storage.
export const tokenStorage = {
  get: (): string | null => null,
  set: (_token: string): void => {},
  clear: (): void => {},
};
