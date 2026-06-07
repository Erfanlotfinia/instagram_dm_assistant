export type ConversationState = 'open' | 'closed' | 'pending_handoff' | 'archived';

export type AgentWorkflowState =
  | 'idle'
  | 'waiting_for_product'
  | 'waiting_for_variant'
  | 'waiting_for_customer_info'
  | 'waiting_for_confirmation'
  | 'waiting_for_payment'
  | 'paid'
  | 'sent_to_shipping'
  | 'completed'
  | 'cancelled'
  | 'human_handoff';

export type MessageDirection = 'inbound' | 'outbound';
export type MessageType = 'text' | 'shared_post' | 'attachment' | 'system';

export interface CustomerSummary {
  id: string;
  instagram_user_id: string;
  full_name: string | null;
}

export interface Customer extends CustomerSummary {
  phone: string | null;
  city: string | null;
  address: string | null;
  postal_code: string | null;
  notes: string | null;
}

export interface CustomerUpdate {
  full_name?: string | null;
  phone?: string | null;
  city?: string | null;
  address?: string | null;
  postal_code?: string | null;
  notes?: string | null;
}

export interface ConversationListFilters {
  state?: ConversationState;
  handoff_required?: boolean;
  assigned_operator_id?: string;
  updated_from?: string;
  updated_to?: string;
  search?: string;
}

export interface LinkedProductSummary {
  id: string;
  title: string;
}

export interface LinkedOrderSummary {
  id: string;
  status: string;
  payment_status: string;
  total_amount: string;
}

export interface ConversationSlots {
  id: string;
  conversation_id: string;
  product_id: string | null;
  product_variant_id: string | null;
  instagram_post_url: string | null;
  color: string | null;
  normalized_color?: string | null;
  size: string | null;
  normalized_size?: string | null;
  variant_alternatives?: Array<Record<string, unknown>>;
  quantity: number | null;
  customer_name: string | null;
  phone: string | null;
  city: string | null;
  address: string | null;
  postal_code: string | null;
  missing_fields: string[];
  confidence: Record<string, number>;
  updated_at: string;
}

export interface AgentAction {
  id: string;
  conversation_id: string;
  action_name: string;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  confidence: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface AgentRun {
  id: string;
  conversation_id: string;
  input_message_id: string;
  model_name: string;
  prompt_version: string;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  status: 'success' | 'failed';
  error_message: string | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  shop_id: string;
  instagram_account_id: string;
  customer_id: string;
  state: ConversationState;
  workflow_state: AgentWorkflowState;
  agent_paused: boolean;
  suggested_outbound?: string | null;
  preview_required?: boolean;
  preview_reason?: string | null;
  last_intent: string | null;
  assigned_operator_id: string | null;
  handoff_required: boolean;
  handoff_reason: string | null;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
  customer?: CustomerSummary | null;
  last_message_text?: string | null;
  last_message_direction?: MessageDirection | null;
  confidence_score?: number | null;
}

export interface Message {
  id: string;
  conversation_id: string;
  direction: MessageDirection;
  message_type: MessageType;
  text: string | null;
  created_at: string;
  raw_payload?: Record<string, unknown> | null;
}

export interface MessageCreate {
  text: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
  slots: ConversationSlots | null;
  agent_runs: AgentRun[];
  agent_actions: AgentAction[];
  customer?: Customer | null;
  linked_product?: LinkedProductSummary | null;
  linked_order?: LinkedOrderSummary | null;
}

export interface ConversationHandoffResponse {
  conversation_id: string;
  workflow_state: AgentWorkflowState;
  handoff_required: boolean;
  handoff_reason: string | null;
  agent_paused: boolean;
  suggested_outbound?: string | null;
  preview_required?: boolean;
  preview_reason?: string | null;
  assigned_operator_id: string | null;
}

export interface ConversationResolveResponse {
  conversation_id: string;
  state: ConversationState;
}
