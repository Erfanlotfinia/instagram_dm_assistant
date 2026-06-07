export type InstagramAccountStatus = 'connected' | 'disconnected' | 'expired';

export interface InstagramAccount {
  id: string;
  shop_id: string;
  ig_user_id: string;
  page_id: string | null;
  username: string;
  token_expires_at: string | null;
  webhook_enabled: boolean;
  status: InstagramAccountStatus;
  created_at: string;
  updated_at: string;
}

export interface InstagramAccountCreate {
  ig_user_id: string;
  username: string;
  access_token: string;
  page_id?: string;
  webhook_enabled?: boolean;
}
