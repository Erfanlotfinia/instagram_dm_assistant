export type ChannelProvider = 'instagram' | 'whatsapp' | 'telegram' | 'bale' | 'rubika';
export type ChannelAccountStatus = 'draft' | 'connected' | 'webhook_configured' | 'disabled' | 'error';

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
  webhook_verify_token?: string | null;
  status: ChannelAccountStatus;
  capabilities_json: Partial<ChannelCapabilities>;
  settings_json: Record<string, unknown>;
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
  webhook_secret?: string;
  access_token?: string;
  bot_token?: string;
  app_secret?: string;
  default_language_code?: string;
  settings_json?: Record<string, unknown>;
}


export interface TelegramWebhookInfo {
  ok?: boolean;
  result?: Record<string, unknown>;
  description?: string;
}
