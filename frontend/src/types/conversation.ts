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

export type ConversationPriorityLevel = 'urgent' | 'high' | 'medium' | 'low';

export type ConversationEventType =
  | 'inbound_message_received'
  | 'outbound_message_sent'
  | 'suggested_reply_created'
  | 'suggested_reply_approved'
  | 'product_resolved'
  | 'variant_resolved'
  | 'inventory_checked'
  | 'draft_order_created'
  | 'customer_info_completed'
  | 'confirmation_requested'
  | 'payment_link_sent'
  | 'payment_received'
  | 'order_shipped'
  | 'handoff_required'
  | 'operator_took_over'
  | 'operator_released_to_agent'
  | 'order_cancelled'
  | 'conversation_assigned'
  | 'customer_profile_updated';

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

export interface PreviousOrderSummary {
  id: string;
  status: string;
  payment_status: string;
  total_amount: string;
  created_at: string;
}

export interface CustomerProfile extends Customer {
  previous_orders: PreviousOrderSummary[];
  preferred_size: string | null;
  preferred_colors: string[];
  last_successful_size: string | null;
  last_purchase_at: string | null;
  total_paid_amount: string;
  order_count: number;
  is_repeat_customer: boolean;
}

export interface ConversationListFilters {
  state?: ConversationState;
  handoff_required?: boolean;
  assigned_operator_id?: string;
  unassigned?: boolean;
  updated_from?: string;
  updated_to?: string;
  search?: string;
  urgent?: boolean;
  high_priority?: boolean;
  needs_attention?: boolean;
  waiting_for_payment?: boolean;
  ready_to_order?: boolean;
  low_confidence?: boolean;
  assigned_to_me?: boolean;
  is_simulation?: boolean;
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

export interface OperatorSummary {
  id: string;
  full_name: string;
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

export interface ConversationEvent {
  id: string;
  conversation_id: string;
  event_type: ConversationEventType;
  title: string;
  description: string | null;
  metadata: Record<string, unknown> | null;
  created_by_user_id: string | null;
  created_at: string;
}

export interface InventoryStatus {
  variant_id: string | null;
  in_stock: boolean | null;
  available_quantity: number | null;
}

export interface Conversation {
  id: string;
  shop_id: string;
  instagram_account_id: string;
  customer_id: string;
  state: ConversationState;
  workflow_state: AgentWorkflowState;
  agent_paused: boolean;
  is_simulation?: boolean;
  suggested_outbound?: string | null;
  preview_required?: boolean;
  preview_reason?: string | null;
  priority_score?: number;
  priority_level?: ConversationPriorityLevel;
  priority_reason?: string | null;
  needs_attention?: boolean;
  last_operator_action_at?: string | null;
  last_intent: string | null;
  assigned_operator_id: string | null;
  assigned_operator?: OperatorSummary | null;
  handoff_required: boolean;
  handoff_reason: string | null;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
  customer?: CustomerSummary | null;
  last_message_text?: string | null;
  last_message_direction?: MessageDirection | null;
  confidence_score?: number | null;
  agent_mode?: 'copilot' | 'controlled_autopilot' | 'human_first' | null;
  linked_product?: LinkedProductSummary | null;
  linked_order?: LinkedOrderSummary | null;
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

export interface SuggestedReply {
  id: string;
  shop_id: string;
  conversation_id: string;
  message_id: string | null;
  suggested_text: string;
  status: 'pending' | 'approved' | 'edited' | 'rejected' | 'sent';
  generated_by: 'agent' | 'operator';
  approved_by_user_id: string | null;
  edited_text: string | null;
  reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
  slots: ConversationSlots | null;
  agent_runs: AgentRun[];
  agent_actions: AgentAction[];
  customer?: Customer | null;
  customer_profile?: CustomerProfile | null;
  linked_product?: LinkedProductSummary | null;
  linked_order?: LinkedOrderSummary | null;
  suggested_replies?: SuggestedReply[];
  events?: ConversationEvent[];
  inventory_status?: InventoryStatus | null;
  decision_trace_summary?: string | null;
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
  priority_score?: number;
  priority_level?: ConversationPriorityLevel;
  needs_attention?: boolean;
}

export interface ConversationResolveResponse {
  conversation_id: string;
  state: ConversationState;
}

export interface ConversationAssignRequest {
  operator_id: string;
}

export interface ConversationAssignResponse {
  conversation_id: string;
  assigned_operator_id: string;
  assigned_operator_name: string | null;
}

export interface AgentDecisionTrace {
  id: string;
  conversation_id: string;
  message_id: string | null;
  agent_run_id: string | null;
  intent: string | null;
  extracted_slots: Record<string, unknown>;
  normalized_slots: Record<string, unknown>;
  product_candidates: Array<Record<string, unknown>>;
  selected_product_id: string | null;
  variant_resolution: Record<string, unknown>;
  inventory_result: Record<string, unknown>;
  risk_score: { risk_level?: 'low' | 'medium' | 'high' | 'critical'; score?: number; risk_reasons?: string[]; requires_handoff?: boolean; requires_preview?: boolean } & Record<string, unknown>;
  order_action: Record<string, unknown>;
  next_state: string;
  outbound_message_id: string | null;
  auto_send_allowed: boolean;
  human_handoff_required: boolean;
  reasoning_summary: string | null;
  created_at: string;
}

export interface AgentRiskSettings {
  shop_id: string;
  intent_confidence_threshold: number;
  slot_confidence_threshold: number;
  product_confidence_threshold: number;
  variant_confidence_threshold: number;
  address_confidence_threshold: number;
  high_value_order_threshold: number;
  handoff_for_high_risk: boolean;
  handoff_for_low_variant_confidence: boolean;
  preview_required_for_high_value_order: boolean;
}
