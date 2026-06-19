export type ChannelProvider = 'instagram' | 'whatsapp' | 'telegram' | 'bale' | 'rubika';
export type ChannelAccountStatus = 'draft' | 'connected' | 'webhook_configured' | 'disconnected' | 'disabled' | 'error';

export type TelegramConnectionMode = 'bot' | 'business' | 'hybrid';

export type TelegramConnectionSessionStatus =
  | 'pending'
  | 'waiting_bot_token'
  | 'waiting_managed_bot_approval'
  | 'waiting_business_connection'
  | 'connected'
  | 'failed'
  | 'expired';

export interface ChannelCapabilities {
  supports_webhook: boolean;
  supports_long_polling: boolean;
  supports_text: boolean;
  supports_images: boolean;
  supports_video: boolean;
  supports_voice: boolean;
  supports_files: boolean;
  supports_buttons: boolean;
  supports_reply_keyboard: boolean;
  supports_inline_keyboard: boolean;
  supports_templates: boolean;
  supports_payments: boolean;
  supports_catalog_messages: boolean;
  supports_message_edit: boolean;
  supports_delete_message: boolean;
  supports_typing_indicator: boolean;
  max_text_length: number;
  webhook_security_type: string;
  supports_customer_service_window: boolean;
  default_customer_service_window_hours?: number | null;
}

export interface ChannelAccount {
  id: string;
  shop_id: string;
  provider: ChannelProvider;
  display_name: string;
  external_account_id?: string | null;
  phone_number_id?: string | null;
  bot_username?: string | null;
  bot_id?: string | null;
  webhook_url?: string | null;
  status: ChannelAccountStatus;
  capabilities_json: Partial<ChannelCapabilities>;
  settings_json: Record<string, unknown>;
  connection_mode?: TelegramConnectionMode | null;
  telegram_business_connection_id?: string | null;
  telegram_user_id?: string | null;
  telegram_username?: string | null;
  telegram_chat_id?: string | null;
  telegram_rights_json?: Record<string, unknown>;
  telegram_capabilities_json?: Record<string, unknown>;
  telegram_last_sync_at?: string | null;
  telegram_business_enabled?: boolean;
  managed_bot?: boolean;
  manager_bot_id?: string | null;
  managed_bot_id?: string | null;
  token_configured: boolean;
  bot_token_configured: boolean;
  webhook_secret_configured: boolean;
  webhook_verify_token_configured?: boolean;
  last_validation_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChannelAccountCreate {
  provider: ChannelProvider;
  display_name: string;
  external_account_id?: string;
  phone_number_id?: string;
  bot_username?: string;
  bot_id?: string;
  webhook_verify_token?: string;
  settings?: Record<string, unknown>;
  connection_mode?: TelegramConnectionMode;
}

export interface ChannelAccountUpdate {
  display_name?: string;
  external_account_id?: string;
  phone_number_id?: string;
  bot_username?: string;
  bot_id?: string;
  webhook_verify_token?: string;
  settings?: Record<string, unknown>;
  status?: ChannelAccountStatus;
  connection_mode?: TelegramConnectionMode;
}

export interface ChannelAccountCredentials {
  webhook_secret?: string;
  access_token?: string;
  bot_token?: string;
  webhook_verify_token?: string;
}

export interface WebhookTestResponse {
  status: string;
  provider: ChannelProvider;
  channel_account_id: string;
}

export type ChannelConnectionSessionStatus =
  | 'pending'
  | 'redirected'
  | 'authorized'
  | 'account_selection_required'
  | 'connected'
  | 'failed'
  | 'expired'
  | 'cancelled';

export interface InstagramConnectStartResponse {
  authorization_url: string;
  session_id: string;
  expires_at: string;
}

export interface InstagramCandidateAccount {
  page_id: string;
  page_name: string;
  instagram_business_account_id: string;
  instagram_username?: string | null;
  instagram_profile_picture_url?: string | null;
}

export interface InstagramConnectSession {
  id: string;
  shop_id: string;
  status: ChannelConnectionSessionStatus;
  expires_at: string;
  completed_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  candidate_accounts: InstagramCandidateAccount[];
  channel_account_id?: string | null;
}

export interface InstagramSelectAccountRequest {
  page_id: string;
  instagram_business_account_id: string;
}

export interface InstagramReadiness {
  meta_app_id_configured: boolean;
  meta_app_secret_configured: boolean;
  oauth_redirect_uri: string;
  data_deletion_callback_configured: boolean;
  privacy_policy_url?: string | null;
  required_scopes: string[];
  app_mode: string;
  webhook_callback_reachable: boolean;
  webhook_callback_url: string;
  app_review_status: string;
}

export interface TelegramConnectStartResponse {
  session_id: string;
  expires_at: string;
  status: TelegramConnectionSessionStatus;
  deep_link?: string | null;
  suggested_bot_username?: string | null;
  managed_bot?: boolean;
}

export interface TelegramConnectSession {
  id: string;
  shop_id: string;
  mode: TelegramConnectionMode;
  status: TelegramConnectionSessionStatus;
  expires_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  channel_account_id?: string | null;
  bot_username?: string | null;
  bot_id?: string | null;
  telegram_business_enabled?: boolean;
  deep_link?: string | null;
  suggested_bot_username?: string | null;
  managed_bot?: boolean;
  metadata_json?: Record<string, unknown>;
}

export interface TelegramConnectStartRequest {
  mode: TelegramConnectionMode;
  display_name?: string;
  channel_account_id?: string;
  managed_bot?: boolean;
}

export interface TelegramWebhookInfo {
  ok?: boolean;
  result?: Record<string, unknown>;
  description?: string;
}
