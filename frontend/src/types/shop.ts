export type ShopStatus = 'active' | 'suspended';
export type HandoffMode = 'automatic' | 'manual_only';

export interface ShopAgentSettings {
  auto_reply_enabled: boolean;
  intent_confidence_threshold: number;
  slots_confidence_threshold: number;
  product_confidence_threshold: number;
  address_confidence_threshold: number;
  auto_send_confidence_threshold: number;
  auto_send_enabled: boolean;
  preview_required_for_low_confidence: boolean;
  preview_required_for_first_24h: boolean;
  high_value_order_threshold: number;
  handoff_mode: HandoffMode;
  default_language: string;
  low_stock_threshold: number;
}

export interface Shop {
  id: string;
  name: string;
  slug: string;
  status: ShopStatus;
  default_currency: string;
  agent_settings?: ShopAgentSettings;
  created_at: string;
  updated_at: string;
  onboarding_flags?: Record<string, unknown>;
}

export interface ShopCreate {
  name: string;
  slug?: string;
  default_currency?: string;
}

export interface ShopUpdate {
  name?: string;
  default_currency?: string;
}

export interface ShopMember {
  id: string;
  shop_id: string;
  user_id: string;
  role: string;
  created_at: string;
  full_name: string;
  email: string;
}

export interface InstagramAccountStatusSummary {
  id: string;
  username: string;
  status: string;
  webhook_enabled: boolean;
  token_expires_at: string | null;
}

export interface ShopSettings {
  shop: Shop;
  instagram_accounts: InstagramAccountStatusSummary[];
  webhook_active: boolean;
}
