import { useSyncExternalStore } from 'react';

export type ThemePreference = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

const STORAGE_KEY = 'modira:theme';
const DEFAULT_PREFERENCE: ThemePreference = 'dark';

function readPreference(): ThemePreference {
  if (typeof localStorage === 'undefined') {
    return DEFAULT_PREFERENCE;
  }
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : DEFAULT_PREFERENCE;
}

function systemTheme(): ResolvedTheme {
  if (typeof window === 'undefined' || !window.matchMedia) {
    return 'dark';
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function resolve(pref: ThemePreference): ResolvedTheme {
  return pref === 'system' ? systemTheme() : pref;
}

let preference: ThemePreference = readPreference();
const listeners = new Set<() => void>();

function applyToDocument() {
  if (typeof document === 'undefined') {
    return;
  }
  document.documentElement.setAttribute('data-theme', resolve(preference));
}

function emit() {
  applyToDocument();
  for (const listener of listeners) {
    listener();
  }
}

// Keep the resolved theme in sync when the OS preference changes (system mode).
if (typeof window !== 'undefined' && window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (preference === 'system') {
      emit();
    }
  });
}

applyToDocument();

export const themeStore = {
  getPreference: () => preference,
  getResolved: () => resolve(preference),
  setPreference(next: ThemePreference) {
    preference = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Ignore storage failures (private mode, etc).
    }
    emit();
  },
  cycle() {
    const order: ThemePreference[] = ['light', 'dark', 'system'];
    const index = order.indexOf(preference);
    themeStore.setPreference(order[(index + 1) % order.length]);
  },
  subscribe(listener: () => void) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};

export function useTheme() {
  const preferenceValue = useSyncExternalStore(
    themeStore.subscribe,
    themeStore.getPreference,
    () => DEFAULT_PREFERENCE as ThemePreference,
  );
  const resolved = useSyncExternalStore(
    themeStore.subscribe,
    themeStore.getResolved,
    () => 'dark' as ResolvedTheme,
  );
  return {
    preference: preferenceValue,
    resolved,
    setPreference: themeStore.setPreference,
    cycle: themeStore.cycle,
  };
}
