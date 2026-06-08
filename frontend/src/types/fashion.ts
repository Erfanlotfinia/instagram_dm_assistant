export interface ColorAlias {
  id: string;
  shop_id?: string | null;
  raw_value: string;
  normalized_value: string;
  language: string;
  is_active: boolean;
}

export interface SizeAlias {
  id: string;
  shop_id?: string | null;
  raw_value: string;
  normalized_value: string;
  category?: string | null;
  is_active: boolean;
}

export interface VariantAlternative {
  variant_id: string;
  sku: string;
  color?: string | null;
  size?: string | null;
  normalized_color?: string | null;
  normalized_size?: string | null;
  available_stock: number;
  reason: string;
}

export interface VariantResolverResult {
  matched: boolean;
  variant_id?: string | null;
  sku?: string | null;
  normalized_color?: string | null;
  normalized_size?: string | null;
  available_stock?: number | null;
  color_confidence?: number;
  size_confidence?: number;
  confidence: number;
  mismatch_reasons?: string[];
  alternatives?: VariantAlternative[];
  available_alternatives?: VariantAlternative[];
}

export interface UnavailableDemandLog {
  id: string;
  product_id?: string | null;
  requested_color_raw?: string | null;
  requested_color_normalized?: string | null;
  requested_size_raw?: string | null;
  requested_size_normalized?: string | null;
  requested_quantity: number;
  reason: string;
  estimated_lost_revenue?: number | null;
}
