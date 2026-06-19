/**
 * Subsequence fuzzy match with a light relevance score.
 * Returns null when the query characters do not appear in order.
 */
export function fuzzyScore(query: string, target: string): number | null {
  const q = query.trim().toLowerCase();
  const t = target.toLowerCase();
  if (q.length === 0) {
    return 0;
  }
  let score = 0;
  let queryIndex = 0;
  let lastMatch = -1;
  for (let i = 0; i < t.length && queryIndex < q.length; i += 1) {
    if (t[i] === q[queryIndex]) {
      // Reward consecutive and word-start matches.
      score += lastMatch === i - 1 ? 3 : 1;
      if (i === 0 || t[i - 1] === ' ') {
        score += 2;
      }
      lastMatch = i;
      queryIndex += 1;
    }
  }
  return queryIndex === q.length ? score : null;
}
