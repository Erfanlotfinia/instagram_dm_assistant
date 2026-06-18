export type ClassValue = string | number | false | null | undefined;

/** Minimal classnames joiner — keeps Tailwind class composition readable. */
export function cn(...values: ClassValue[]): string {
  return values.filter(Boolean).join(' ');
}
