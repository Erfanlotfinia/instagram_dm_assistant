export interface RecoveryRule {
  id: string;
  shop_id: string;
  is_active: boolean;
  trigger_after_minutes: number;
  max_attempts: number;
  message_template: string;
  only_inside_allowed_messaging_window: boolean;
  created_at: string;
  updated_at: string;
}

export interface RecoveryRuleCreate {
  is_active?: boolean;
  trigger_after_minutes: number;
  max_attempts: number;
  message_template: string;
  only_inside_allowed_messaging_window?: boolean;
}

export interface RecoveryRuleUpdate {
  is_active?: boolean;
  trigger_after_minutes?: number;
  max_attempts?: number;
  message_template?: string;
  only_inside_allowed_messaging_window?: boolean;
}

export interface ProductUpsellRule {
  id: string;
  shop_id: string;
  source_product_id: string;
  target_product_id: string;
  message_template: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductUpsellCreate {
  source_product_id: string;
  target_product_id: string;
  message_template?: string | null;
  is_active?: boolean;
}

export interface ProductUpsellUpdate {
  message_template?: string | null;
  is_active?: boolean;
}

export interface PostRevenueRow {
  instagram_post_url: string;
  product_id: string | null;
  conversations: number;
  draft_orders: number;
  paid_orders: number;
  revenue: string;
  conversion_rate: number;
  abandoned_rate: number;
}

export interface CustomerPreferences {
  id: string;
  customer_id: string;
  preferred_size: string | null;
  preferred_colors: string[];
  preferred_categories: string[];
  last_successful_size: string | null;
  last_successful_city: string | null;
  last_successful_address_id: string | null;
  updated_at: string;
}
