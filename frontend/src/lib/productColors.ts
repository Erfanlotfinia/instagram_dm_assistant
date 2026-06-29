import type { ProductColorValidationResult } from '../types/sprint2Readiness';

/**
 * Safe catalog color validation.
 *
 * Used by customer profile swatches and any catalog surface that wants to
 * render a data-driven color. The Modira brand color audit allowlists
 * `style={{ background: ... }}` only inside `CustomerProfilePanel.tsx` —
 * this utility ensures the value placed there can only be a hex color or a
 * known-safe CSS color name. It never throws.
 *
 * Accepted:
 *   - #RGB
 *   - #RRGGBB
 *   - #RRGGBBAA (alpha allowed; rendered via inline style on the swatch only)
 *   - approved safe CSS color names (lowercased)
 *
 * Rejected:
 *   - url, var, expression functions
 *   - rgb, hsl, rgba, hsla functions
 *   - anything containing `;`, `(`, `)`, `<`, `>`, or other unsafe characters
 *   - empty / null / undefined / non-string
 */

export const SAFE_CSS_COLOR_NAMES: ReadonlySet<string> = new Set([
  'black', 'white', 'red', 'green', 'blue', 'navy', 'gray', 'grey', 'silver',
  'maroon', 'olive', 'lime', 'aqua', 'teal', 'fuchsia', 'purple', 'pink',
  'orange', 'yellow', 'brown', 'beige', 'gold', 'ivory', 'khaki', 'coral',
  'crimson', 'cyan', 'magenta', 'indigo', 'violet', 'tan', 'turquoise',
]);

const HEX_PATTERN = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;
const UNSAFE_CHARS = /[;()<>\\]/;
const FUNCTION_PATTERN = /(url|var|expression|rgb|rgba|hsl|hsla)\s*\(/i;

function isHex(value: string): boolean {
  return HEX_PATTERN.test(value);
}

/**
 * Validate a raw catalog color string. Never throws — invalid input returns
 * `{ raw, valid: false, reason }`.
 */
export function validateProductColor(value: unknown): ProductColorValidationResult {
  if (typeof value !== 'string') {
    return { raw: value == null ? '' : String(value), valid: false, reason: 'Color must be a string.' };
  }

  const trimmed = value.trim();
  if (trimmed === '') {
    return { raw: value, valid: false, reason: 'Color is empty.' };
  }

  if (UNSAFE_CHARS.test(trimmed)) {
    return { raw: value, valid: false, reason: 'Color contains unsafe characters.' };
  }

  if (FUNCTION_PATTERN.test(trimmed)) {
    return { raw: value, valid: false, reason: 'CSS functions are not allowed.' };
  }

  if (isHex(trimmed)) {
    return { raw: value, normalized: trimmed.toLowerCase(), valid: true };
  }

  const lower = trimmed.toLowerCase();
  if (SAFE_CSS_COLOR_NAMES.has(lower)) {
    return { raw: value, normalized: lower, valid: true };
  }

  return { raw: value, valid: false, reason: 'Not a recognized hex color or safe CSS color name.' };
}

/**
 * Returns a safe `background` value for a swatch, or `undefined` when the
 * input is invalid. Callers should fall back to a theme token (e.g.
 * `var(--c-border)`) when the result is `undefined`.
 */
export function safeSwatchBackground(value: unknown): string | undefined {
  const result = validateProductColor(value);
  return result.valid ? result.normalized : undefined;
}
