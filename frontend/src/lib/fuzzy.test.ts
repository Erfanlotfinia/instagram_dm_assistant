import { describe, expect, it } from 'vitest';

import { fuzzyScore } from './fuzzy';

describe('fuzzyScore', () => {
  it('returns a score of 0 for an empty query', () => {
    expect(fuzzyScore('', 'Inbox')).toBe(0);
  });

  it('matches subsequences', () => {
    expect(fuzzyScore('inb', 'Inbox')).not.toBeNull();
    expect(fuzzyScore('hq', 'Handoff Queue')).not.toBeNull();
  });

  it('returns null when characters are missing or out of order', () => {
    expect(fuzzyScore('xyz', 'Inbox')).toBeNull();
    expect(fuzzyScore('xobni', 'Inbox')).toBeNull();
  });

  it('scores word-start matches higher than scattered matches', () => {
    const wordStart = fuzzyScore('ord', 'Orders');
    const scattered = fuzzyScore('ord', 'Recovery rod');
    expect(wordStart).not.toBeNull();
    expect(scattered).not.toBeNull();
    expect(wordStart!).toBeGreaterThan(scattered!);
  });
});
