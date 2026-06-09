export interface ProductAlias {
  id: string;
  alias_text: string;
  language: string;
  source: string;
  confidence: number;
  is_active: boolean;
}

export interface ProductNormalized {
  id: string;
  shop_id: string;
  product_id: string;
  normalized_title: string;
  brand?: string | null;
  color?: string | null;
  size?: string | null;
  material?: string | null;
  gender?: string | null;
  collection?: string | null;
  synonym_candidates: string[];
  qdrant_point_id?: string | null;
  embedding_model?: string | null;
  last_normalized_at?: string | null;
  last_indexed_at?: string | null;
  aliases: ProductAlias[];
}

export interface CatalogProductListResponse {
  items: ProductNormalized[];
  total: number;
  page: number;
  page_size: number;
}

export interface CatalogImportJob {
  id: string;
  shop_id: string;
  status: string;
  source_format: string;
  total_rows: number;
  processed_rows: number;
  failed_rows: number;
  checkpoint: Record<string, unknown>;
  error_message?: string | null;
}

export interface CatalogImportRequest {
  shop_id: string;
  rows: Array<{
    title: string;
    description?: string;
    brand?: string;
    aliases?: string[];
    variants?: Array<{ color?: string; size?: string; sku?: string; stock_quantity?: number }>;
  }>;
}

export interface CatalogReindexRequest {
  shop_id: string;
  product_ids?: string[];
  batch_size?: number;
}

export interface ProductAliasesPatchRequest {
  add?: string[];
  remove?: string[];
  language?: string;
}
