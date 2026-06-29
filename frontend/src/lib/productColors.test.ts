import { describe, expect, it } from 'vitest';

import { safeSwatchBackground, validateProductColor } from './productColors';

describe('validateProductColor', () => {
  it('accepts and normalizes #FF0000', () => {
    const result = validateProductColor('#FF0000');
    expect(result.valid).toBe(true);
    expect(result.normalized).toBe('#ff0000');
  });

  it('accepts #RGB shorthand', () => {
    const result = validateProductColor('#f00');
    expect(result.valid).toBe(true);
    expect(result.normalized).toBe('#f00');
  });

  it('accepts #RRGGBBAA with alpha', () => {
    const result = validateProductColor('#ff0000ff');
    expect(result.valid).toBe(true);
    expect(result.normalized).toBe('#ff0000ff');
  });

  it('accepts a safe CSS color name and lowercases it', () => {
    const result = validateProductColor('Red');
    expect(result.valid).toBe(true);
    expect(result.normalized).toBe('red');
  });

  it('accepts navy', () => {
    const result = validateProductColor('navy');
    expect(result.valid).toBe(true);
    expect(result.normalized).toBe('navy');
  });

  it('rejects empty string', () => {
    expect(validateProductColor('').valid).toBe(false);
  });

  it('rejects url(...) injection', () => {
    const result = validateProductColor('url(javascript:alert(1))');
    expect(result.valid).toBe(false);
    expect(result.reason).toMatch(/unsafe|functions/i);
  });

  it('rejects var(--x)', () => {
    expect(validateProductColor('var(--c-accent)').valid).toBe(false);
  });

  it('rejects expression(...)', () => {
    expect(validateProductColor('expression(alert(1))').valid).toBe(false);
  });

  it('rejects rgb(...)', () => {
    expect(validateProductColor('rgb(1, 2, 3)').valid).toBe(false);
  });

  it('rejects hsl(...)', () => {
    expect(validateProductColor('hsl(0, 100%, 50%)').valid).toBe(false);
  });

  it('rejects values containing semicolons', () => {
    expect(validateProductColor('red;').valid).toBe(false);
  });

  it('rejects values containing parentheses', () => {
    expect(validateProductColor('red()').valid).toBe(false);
  });

  it('rejects non-strings without throwing', () => {
    expect(validateProductColor(null).valid).toBe(false);
    expect(validateProductColor(undefined).valid).toBe(false);
    expect(validateProductColor(123).valid).toBe(false);
    expect(validateProductColor({ color: 'red' }).valid).toBe(false);
  });

  it('rejects unknown color names', () => {
    expect(validateProductColor('hotpink').valid).toBe(false);
  });

  it('rejects malformed hex', () => {
    expect(validateProductColor('#ff00').valid).toBe(false);
    expect(validateProductColor('#gggggg').valid).toBe(false);
    expect(validateProductColor('ff0000').valid).toBe(false);
  });
});

describe('safeSwatchBackground', () => {
  it('returns normalized value for valid hex', () => {
    expect(safeSwatchBackground('#FF0000')).toBe('#ff0000');
  });

  it('returns undefined for invalid input', () => {
    expect(safeSwatchBackground('url(javascript:alert(1))')).toBeUndefined();
    expect(safeSwatchBackground('')).toBeUndefined();
    expect(safeSwatchBackground(null)).toBeUndefined();
  });
});
