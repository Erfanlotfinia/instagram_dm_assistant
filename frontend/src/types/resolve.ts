export interface ProductCandidate {
  product_id: string;
  title: string;
  score: number;
  confidence_band: string;
  rationale: string;
  matched_aliases: string[];
  rules_fired: string[];
}

export interface VariantCandidate {
  variant_id: string;
  product_id: string;
  sku: string;
  color?: string | null;
  size?: string | null;
  normalized_color?: string | null;
  normalized_size?: string | null;
  available_stock: number;
  score: number;
  confidence_band: string;
  rationale: string;
  matched_aliases: string[];
  rules_fired: string[];
}

export interface ResolveProductResponse {
  trace_id: string;
  query: string;
  candidates: ProductCandidate[];
  confidence_band: string;
  confidence_score: number;
  missing_slots: string[];
  rationale?: string | null;
}

export interface ResolveVariantResponse {
  trace_id: string;
  product_id?: string | null;
  candidates: VariantCandidate[];
  confidence_band: string;
  confidence_score: number;
  missing_slots: string[];
  rationale?: string | null;
}

export interface ResolverTrace {
  id: string;
  shop_id: string;
  trace_type: string;
  conversation_id?: string | null;
  input_payload: Record<string, unknown>;
  top_candidates: Record<string, unknown>[];
  matched_aliases: Record<string, unknown>[];
  rules_fired: string[];
  missing_slots: string[];
  confidence_band: string;
  confidence_score: number;
  rationale?: string | null;
  qdrant_query_metadata: Record<string, unknown>;
  created_at: string;
}

export interface ResolverFeedbackRequest {
  shop_id: string;
  action: 'accept_ai' | 'correct_product' | 'correct_variant' | 'taxonomy_issue';
  original_product_id?: string;
  corrected_product_id?: string;
  original_variant_id?: string;
  corrected_variant_id?: string;
  notes?: string;
}

export interface ResolverFeedback {
  id: string;
  shop_id: string;
  trace_id: string;
  action: string;
  operator_id: string;
  notes?: string | null;
  created_at: string;
}
