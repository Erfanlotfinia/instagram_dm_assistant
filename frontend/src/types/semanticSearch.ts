export interface SemanticSearchRequest {
  query: string;
  limit?: number;
}

export interface SemanticSearchHit {
  product_id: string;
  title: string;
  score: number;
  description: string | null;
}

export interface SemanticSearchResponse {
  query: string;
  hits: SemanticSearchHit[];
}
