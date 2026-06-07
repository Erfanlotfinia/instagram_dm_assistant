export type ProductStatus = 'active' | 'inactive' | 'archived';

export type ConfidenceSource = 'manual' | 'caption_match' | 'image_match' | 'admin_confirmed';

export interface Product {
  id: string;
  shop_id: string;
  title: string;
  description: string | null;
  status: ProductStatus;
  base_price: string;
  currency: string;
  main_image_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductCreate {
  title: string;
  description?: string;
  status?: ProductStatus;
  base_price: string;
  currency?: string;
  main_image_url?: string;
}

export interface ProductUpdate {
  title?: string;
  description?: string;
  status?: ProductStatus;
  base_price?: string;
  currency?: string;
  main_image_url?: string;
}

export interface ProductVariant {
  id: string;
  product_id: string;
  color: string | null;
  size: string | null;
  sku: string;
  price: string;
  stock_quantity: number;
  reserved_quantity: number;
  available_stock: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface VariantCreate {
  color?: string;
  size?: string;
  sku: string;
  price: string;
  stock_quantity?: number;
  is_active?: boolean;
}

export interface VariantUpdate {
  color?: string;
  size?: string;
  sku?: string;
  price?: string;
  stock_quantity?: number;
  is_active?: boolean;
}

export interface InstagramProductMap {
  id: string;
  shop_id: string;
  instagram_account_id: string;
  instagram_media_id: string | null;
  instagram_post_url: string;
  product_id: string;
  confidence_source: ConfidenceSource;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InstagramProductMapCreate {
  instagram_account_id: string;
  instagram_post_url: string;
  instagram_media_id?: string;
  product_id: string;
  confidence_source?: ConfidenceSource;
  is_active?: boolean;
}

export interface ResolveInstagramProductRequest {
  instagram_post_url?: string;
  instagram_media_id?: string;
}

export interface ResolveInstagramProductResponse {
  product: Product | null;
  map_id: string | null;
  confidence_source: ConfidenceSource | null;
}
