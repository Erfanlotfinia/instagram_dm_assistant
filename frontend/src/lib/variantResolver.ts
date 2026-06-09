import type { VariantAlternative, VariantResolverResult } from '../types/fashion';

const MISMATCH_LABELS: Record<string, string> = {
  product_not_found: 'Product not found',
  missing_color: 'Color not provided',
  missing_size: 'Size not provided',
  unknown_color_alias: 'Unknown color alias',
  unknown_size_alias: 'Unknown size alias',
  color_unavailable: 'Color not available for this product',
  size_unavailable: 'Size not available for this product',
  variant_combination_unavailable: 'Color/size combination not found',
  insufficient_stock: 'Insufficient stock',
  out_of_stock: 'Out of stock',
  variant_not_found: 'Variant not found',
  color_not_found: 'Color not found',
  size_not_found: 'Size not found',
};

export type NormalizedVariantResolverResult = VariantResolverResult & {
  mismatch_reasons: string[];
  alternatives: VariantAlternative[];
  available_alternatives: VariantAlternative[];
};

export function normalizeResolverResult(raw: VariantResolverResult): NormalizedVariantResolverResult {
  const confidence = typeof raw.confidence === 'number' ? raw.confidence : 0;
  return {
    ...raw,
    confidence,
    color_confidence: typeof raw.color_confidence === 'number' ? raw.color_confidence : confidence,
    size_confidence: typeof raw.size_confidence === 'number' ? raw.size_confidence : confidence,
    mismatch_reasons: Array.isArray(raw.mismatch_reasons) ? raw.mismatch_reasons : [],
    alternatives: Array.isArray(raw.alternatives) ? raw.alternatives : [],
    available_alternatives: Array.isArray(raw.available_alternatives) ? raw.available_alternatives : [],
  };
}

export function formatMismatchReason(reason: string): string {
  return MISMATCH_LABELS[reason] ?? reason.replaceAll('_', ' ');
}

export type DemandReasonTone = 'success' | 'warning' | 'danger' | 'neutral';

export function demandReasonTone(reason: string): DemandReasonTone {
  if (reason === 'out_of_stock' || reason === 'insufficient_stock') {
    return 'warning';
  }
  if (
    reason === 'variant_not_found' ||
    reason === 'color_not_found' ||
    reason === 'size_not_found' ||
    reason === 'product_not_found'
  ) {
    return 'danger';
  }
  return 'neutral';
}

export function formatConfidence(value: number | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '—';
  }
  return `${Math.round(value * 100)}%`;
}

export function stockStatus(stock: number | null | undefined): {
  label: string;
  tone: 'success' | 'warning' | 'danger';
} {
  if (stock == null) {
    return { label: 'Unknown', tone: 'warning' };
  }
  if (stock <= 0) {
    return { label: 'Out of stock', tone: 'danger' };
  }
  if (stock <= 3) {
    return { label: 'Low stock', tone: 'warning' };
  }
  return { label: 'In stock', tone: 'success' };
}

export function uniqueAlternatives(
  alternatives: VariantAlternative[],
  availableAlternatives: VariantAlternative[],
): VariantAlternative[] {
  if (alternatives.length === 0) {
    return availableAlternatives;
  }
  const seen = new Set<string>();
  const merged: VariantAlternative[] = [];
  for (const row of [...alternatives, ...availableAlternatives]) {
    if (seen.has(row.variant_id)) {
      continue;
    }
    seen.add(row.variant_id);
    merged.push(row);
  }
  return merged;
}
