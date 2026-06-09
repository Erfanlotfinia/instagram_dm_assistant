import type {
  Conversation,
  ConversationDetail,
  AgentDecisionTrace,
  AgentRiskSettings,
  ConversationHandoffResponse,
  ConversationListFilters,
  ConversationResolveResponse,
  Customer,
  CustomerUpdate,
  Message,
  MessageCreate,
  SuggestedReply,
} from '../types/conversation';
import type {
  CustomerPreferences,
  PostRevenueRow,
  ProductUpsellCreate,
  ProductUpsellRule,
  ProductUpsellUpdate,
  RecoveryRule,
  RecoveryRuleCreate,
  RecoveryRuleUpdate,
} from '../types/sprintD';
import type { DashboardMetrics } from '../types/dashboard';
import type { AgentPerformanceMetrics, AgentStudioSettings, DMSimulatorRequest, DMSimulatorResponse, FunnelAnalytics, HandoffAnalyticsRow, OnboardingStatus, PaginatedLostDemand, PaginatedOperatorPerformance, PostPerformanceRow, ResponseTimeAnalytics, SimulatorRunSummary, StockDemandRow, TriggerPerformance, TriggerRule, UnavailableDemandRow } from '../types/competitive';
import type { SemanticSearchResponse } from '../types/semanticSearch';
import type { LoginRequest, TokenResponse, User } from '../types/auth';
import type { TRLRiskMetrics, TRLValidationRun, TRLValidationScenarioResult } from '../types/trlValidation';
import type { PilotActionResponse, PilotEventLog, PilotMetrics, PilotReadinessResponse, PilotSettings } from '../types/pilot';
import type { FailedJobListResponse, HealthResponse, ReadinessResponse } from '../types/health';
import type { ColorAlias, SizeAlias, UnavailableDemandLog, VariantResolverResult } from '../types/fashion';
import type { InstagramAccount, InstagramAccountCreate } from '../types/instagramAccount';
import type {
  Order,
  OrderCancelRequest,
  OrderConfirmRequest,
  OrderCorrectnessRead,
  OrderListFilters,
  OrderShipRequest,
  OrderTimelineResponse,
} from '../types/order';
import type {
  InstagramProductMap,
  InstagramProductMapCreate,
  Product,
  ProductCreate,
  ProductUpdate,
  ProductVariant,
  ResolveInstagramProductRequest,
  ResolveInstagramProductResponse,
  VariantCreate,
  VariantUpdate,
} from '../types/product';
import type {
  Shop,
  ShopAgentSettings,
  ShopCreate,
  ShopMember,
  ShopSettings,
  ShopUpdate,
} from '../types/shop';
import { tokenStorage } from './tokenStorage';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = tokenStorage.get();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail = `API request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (typeof body.detail === 'string') {
        detail = body.detail;
      }
    } catch {
      // ignore JSON parse errors
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function buildQuery(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      search.set(key, value);
    }
  }
  const query = search.toString();
  return query ? `?${query}` : '';
}

export const apiClient = {
  getHealth: () => request<HealthResponse>('/api/v1/health'),
  getReady: () => request<ReadinessResponse>('/api/v1/ready'),
  login: (payload: LoginRequest) =>
    request<TokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getMe: () => request<User>('/api/v1/auth/me'),
  listShops: () => request<Shop[]>('/api/v1/shops'),
  createShop: (payload: ShopCreate) =>
    request<Shop>('/api/v1/shops', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getShop: (shopId: string) => request<Shop>(`/api/v1/shops/${shopId}`),
  updateShop: (shopId: string, payload: ShopUpdate) =>
    request<Shop>(`/api/v1/shops/${shopId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  getShopSettings: (shopId: string) => request<ShopSettings>(`/api/v1/shops/${shopId}/settings`),
  updateAgentSettings: (shopId: string, payload: Partial<ShopAgentSettings>) =>
    request<Shop>(`/api/v1/shops/${shopId}/agent-settings`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  getDashboardMetrics: (shopId: string) =>
    request<DashboardMetrics>(`/api/v1/shops/${shopId}/dashboard/metrics`),
  getOnboardingStatus: (shopId: string) =>
    request<OnboardingStatus>(`/api/v1/shops/${shopId}/onboarding-status`),

  getPilotSettings: (shopId: string) => request<PilotSettings>(`/api/v1/shops/${shopId}/pilot-settings`),
  updatePilotSettings: (shopId: string, payload: Partial<PilotSettings>) =>
    request<PilotSettings>(`/api/v1/shops/${shopId}/pilot-settings`, { method: 'PUT', body: JSON.stringify(payload) }),
  getPilotReadiness: (shopId: string) => request<PilotReadinessResponse>(`/api/v1/shops/${shopId}/pilot-readiness`),
  activatePilotEmergencyStop: (shopId: string) =>
    request<PilotActionResponse>(`/api/v1/shops/${shopId}/pilot/emergency-stop`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  resumePilot: (shopId: string) =>
    request<PilotActionResponse>(`/api/v1/shops/${shopId}/pilot/resume`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  getPilotMetrics: (shopId: string) => request<PilotMetrics>(`/api/v1/shops/${shopId}/pilot/metrics`),
  getPilotEvents: (shopId: string) => request<PilotEventLog>(`/api/v1/shops/${shopId}/pilot/events`),

  listTriggerRules: (shopId: string) =>
    request<TriggerRule[]>(`/api/v1/shops/${shopId}/triggers`),
  createTriggerRule: (shopId: string, payload: Partial<TriggerRule>) =>
    request<TriggerRule>(`/api/v1/shops/${shopId}/triggers`, { method: 'POST', body: JSON.stringify(payload) }),
  getTriggerPerformance: (shopId: string) =>
    request<TriggerPerformance[]>(`/api/v1/shops/${shopId}/triggers/performance`),
  getAgentRiskSettings: (shopId: string) =>
    request<AgentRiskSettings>(`/api/v1/shops/${shopId}/agent-risk-settings`),
  updateAgentRiskSettings: (shopId: string, payload: Partial<AgentRiskSettings>) => {
    const {
      shop_id: _shopId,
      intent_confidence_threshold,
      slot_confidence_threshold,
      product_confidence_threshold,
      variant_confidence_threshold,
      address_confidence_threshold,
      high_value_order_threshold,
      handoff_for_high_risk,
      handoff_for_low_variant_confidence,
      preview_required_for_high_value_order,
    } = payload;

    return request<AgentRiskSettings>(`/api/v1/shops/${shopId}/agent-risk-settings`, {
      method: 'PUT',
      body: JSON.stringify({
        ...(intent_confidence_threshold != null ? { intent_confidence_threshold } : {}),
        ...(slot_confidence_threshold != null ? { slot_confidence_threshold } : {}),
        ...(product_confidence_threshold != null ? { product_confidence_threshold } : {}),
        ...(variant_confidence_threshold != null ? { variant_confidence_threshold } : {}),
        ...(address_confidence_threshold != null ? { address_confidence_threshold } : {}),
        ...(high_value_order_threshold != null ? { high_value_order_threshold } : {}),
        ...(handoff_for_high_risk != null ? { handoff_for_high_risk } : {}),
        ...(handoff_for_low_variant_confidence != null ? { handoff_for_low_variant_confidence } : {}),
        ...(preview_required_for_high_value_order != null ? { preview_required_for_high_value_order } : {}),
      }),
    });
  },
  listDecisionTraces: (shopId: string) =>
    request<AgentDecisionTrace[]>(`/api/v1/shops/${shopId}/decision-traces`),
  getDecisionTrace: (shopId: string, traceId: string) =>
    request<AgentDecisionTrace>(`/api/v1/shops/${shopId}/decision-traces/${traceId}`),
  listConversationDecisionTraces: (shopId: string, conversationId: string) =>
    request<AgentDecisionTrace[]>(`/api/v1/shops/${shopId}/conversations/${conversationId}/decision-traces`),
  getAgentStudioSettings: (shopId: string) =>
    request<AgentStudioSettings>(`/api/v1/shops/${shopId}/agent-settings`),
  updateAgentStudioSettings: (shopId: string, payload: Partial<AgentStudioSettings>) =>
    request<AgentStudioSettings>(`/api/v1/shops/${shopId}/agent-settings`, { method: 'PUT', body: JSON.stringify(payload) }),
  runDMSimulator: (shopId: string, payload: DMSimulatorRequest) =>
    request<DMSimulatorResponse>(`/api/v1/shops/${shopId}/simulator/run`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listSimulatorRuns: (shopId: string) =>
    request<SimulatorRunSummary[]>(`/api/v1/shops/${shopId}/simulator/runs`),
  resetDMSimulator: (shopId: string) =>
    request<{ deleted_conversations: number }>(`/api/v1/shops/${shopId}/simulator/reset`, { method: 'DELETE' }),
  runTRLValidation: (shopId: string, payload: { reset_demo_data?: boolean; scenario_limit?: number | null } = {}) =>
    request<TRLValidationRun>(`/api/v1/shops/${shopId}/trl-validation/run`, {
      method: 'POST',
      body: JSON.stringify({
        reset_demo_data: payload.reset_demo_data ?? false,
        ...(payload.scenario_limit != null ? { scenario_limit: payload.scenario_limit } : {}),
      }),
    }),
  listTRLValidationRuns: (shopId: string) =>
    request<TRLValidationRun[]>(`/api/v1/shops/${shopId}/trl-validation/runs`),
  getTRLValidationRun: (shopId: string, runId: string) =>
    request<TRLValidationRun>(`/api/v1/shops/${shopId}/trl-validation/runs/${runId}`),
  getTRLRiskMetrics: (shopId: string, runId: string) =>
    request<TRLRiskMetrics>(`/api/v1/shops/${shopId}/trl-validation/runs/${runId}/risk-metrics`),
  listTRLValidationScenarios: (shopId: string, runId: string, passed?: boolean) =>
    request<TRLValidationScenarioResult[]>(
      `/api/v1/shops/${shopId}/trl-validation/runs/${runId}/scenarios${buildQuery({ passed: passed === undefined ? undefined : String(passed) })}`,
    ),
  resetTRLValidation: (shopId: string) =>
    request<{ deleted_runs: number; deleted_conversations: number; deleted_orders: number; deleted_customers?: number }>(
      `/api/v1/shops/${shopId}/trl-validation/reset`,
      { method: 'DELETE' },
    ),
  getAnalyticsFunnel: (shopId: string, dateFrom?: string, dateTo?: string) =>
    request<FunnelAnalytics>(
      `/api/v1/shops/${shopId}/analytics/funnel${buildQuery({ date_from: dateFrom, date_to: dateTo })}`,
    ),
  getAnalyticsPosts: (shopId: string, dateFrom?: string, dateTo?: string) =>
    request<PostPerformanceRow[]>(
      `/api/v1/shops/${shopId}/analytics/posts${buildQuery({ date_from: dateFrom, date_to: dateTo })}`,
    ),
  getAnalyticsStockDemand: (shopId: string, dateFrom?: string, dateTo?: string) =>
    request<StockDemandRow[]>(
      `/api/v1/shops/${shopId}/analytics/stock-demand${buildQuery({ date_from: dateFrom, date_to: dateTo })}`,
    ),
  getAnalyticsUnavailableDemand: (shopId: string, dateFrom?: string, dateTo?: string) =>
    request<UnavailableDemandRow[]>(
      `/api/v1/shops/${shopId}/analytics/unavailable-demand${buildQuery({ date_from: dateFrom, date_to: dateTo })}`,
    ),
  getAnalyticsResponseTime: (shopId: string, dateFrom?: string, dateTo?: string) =>
    request<ResponseTimeAnalytics>(
      `/api/v1/shops/${shopId}/analytics/response-time${buildQuery({ date_from: dateFrom, date_to: dateTo })}`,
    ),
  getAnalyticsHandoff: (shopId: string, dateFrom?: string, dateTo?: string) =>
    request<HandoffAnalyticsRow[]>(
      `/api/v1/shops/${shopId}/analytics/handoff${buildQuery({ date_from: dateFrom, date_to: dateTo })}`,
    ),
  getAnalyticsLostDemand: (shopId: string, dateFrom?: string, dateTo?: string, page = 1) =>
    request<PaginatedLostDemand>(
      `/api/v1/shops/${shopId}/analytics/lost-demand${buildQuery({ date_from: dateFrom, date_to: dateTo, page: String(page) })}`,
    ),
  getAnalyticsOperatorPerformance: (shopId: string, dateFrom?: string, dateTo?: string, page = 1) =>
    request<PaginatedOperatorPerformance>(
      `/api/v1/shops/${shopId}/analytics/operator-performance${buildQuery({ date_from: dateFrom, date_to: dateTo, page: String(page) })}`,
    ),
  getAnalyticsAgentPerformance: (shopId: string, dateFrom?: string, dateTo?: string) =>
    request<AgentPerformanceMetrics>(
      `/api/v1/shops/${shopId}/analytics/agent-performance${buildQuery({ date_from: dateFrom, date_to: dateTo })}`,
    ),
  getPostRevenueAnalytics: (shopId: string, dateFrom?: string, dateTo?: string) =>
    request<PostRevenueRow[]>(
      `/api/v1/shops/${shopId}/analytics/post-revenue${buildQuery({ date_from: dateFrom, date_to: dateTo })}`,
    ),
  listFailedJobs: (shopId: string, page = 1) =>
    request<FailedJobListResponse>(`/api/v1/shops/${shopId}/failed-jobs${buildQuery({ page: String(page) })}`),
  listAccessibleFailedJobs: (options?: { shopId?: string; unscopedOnly?: boolean; page?: number }) =>
    request<FailedJobListResponse>(
      `/api/v1/failed-jobs${buildQuery({
        shop_id: options?.shopId,
        unscoped_only: options?.unscopedOnly ? 'true' : undefined,
        page: String(options?.page ?? 1),
      })}`,
    ),
  retryFailedJob: (shopId: string, jobId: string) =>
    request<{ id: string; status: string; message: string }>(
      `/api/v1/shops/${shopId}/failed-jobs/${jobId}/retry`,
      { method: 'POST' },
    ),
  retryFailedJobById: (jobId: string) =>
    request<{ id: string; status: string; message: string }>(`/api/v1/failed-jobs/${jobId}/retry`, {
      method: 'POST',
    }),
  ignoreFailedJob: (shopId: string, jobId: string) =>
    request<{ id: string; status: string; message: string }>(
      `/api/v1/shops/${shopId}/failed-jobs/${jobId}/ignore`,
      { method: 'POST' },
    ),
  ignoreFailedJobById: (jobId: string) =>
    request<{ id: string; status: string; message: string }>(`/api/v1/failed-jobs/${jobId}/ignore`, {
      method: 'POST',
    }),
  listRecoveryRules: (shopId: string) =>
    request<RecoveryRule[]>(`/api/v1/shops/${shopId}/recovery-rules`),
  createRecoveryRule: (shopId: string, payload: RecoveryRuleCreate) =>
    request<RecoveryRule>(`/api/v1/shops/${shopId}/recovery-rules`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateRecoveryRule: (shopId: string, ruleId: string, payload: RecoveryRuleUpdate) =>
    request<RecoveryRule>(`/api/v1/shops/${shopId}/recovery-rules/${ruleId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteRecoveryRule: (shopId: string, ruleId: string) =>
    request<void>(`/api/v1/shops/${shopId}/recovery-rules/${ruleId}`, { method: 'DELETE' }),
  listProductUpsells: (shopId: string) =>
    request<ProductUpsellRule[]>(`/api/v1/shops/${shopId}/product-upsells`),
  createProductUpsell: (shopId: string, payload: ProductUpsellCreate) =>
    request<ProductUpsellRule>(`/api/v1/shops/${shopId}/product-upsells`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateProductUpsell: (shopId: string, upsellId: string, payload: ProductUpsellUpdate) =>
    request<ProductUpsellRule>(`/api/v1/shops/${shopId}/product-upsells/${upsellId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteProductUpsell: (shopId: string, upsellId: string) =>
    request<void>(`/api/v1/shops/${shopId}/product-upsells/${upsellId}`, { method: 'DELETE' }),
  getCustomerPreferences: (shopId: string, customerId: string) =>
    request<CustomerPreferences>(`/api/v1/shops/${shopId}/customers/${customerId}/preferences`),

  listColorAliases: (shopId: string) => request<ColorAlias[]>(`/api/v1/shops/${shopId}/color-aliases`),
  createColorAlias: (shopId: string, payload: Pick<ColorAlias, 'raw_value' | 'normalized_value' | 'language'>) =>
    request<ColorAlias>(`/api/v1/shops/${shopId}/color-aliases`, { method: 'POST', body: JSON.stringify(payload) }),
  updateColorAlias: (shopId: string, aliasId: string, payload: Partial<ColorAlias>) =>
    request<ColorAlias>(`/api/v1/shops/${shopId}/color-aliases/${aliasId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteColorAlias: (shopId: string, aliasId: string) =>
    request<void>(`/api/v1/shops/${shopId}/color-aliases/${aliasId}`, { method: 'DELETE' }),
  listSizeAliases: (shopId: string) => request<SizeAlias[]>(`/api/v1/shops/${shopId}/size-aliases`),
  createSizeAlias: (shopId: string, payload: Pick<SizeAlias, 'raw_value' | 'normalized_value' | 'category'>) =>
    request<SizeAlias>(`/api/v1/shops/${shopId}/size-aliases`, { method: 'POST', body: JSON.stringify(payload) }),
  updateSizeAlias: (shopId: string, aliasId: string, payload: Partial<SizeAlias>) =>
    request<SizeAlias>(`/api/v1/shops/${shopId}/size-aliases/${aliasId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteSizeAlias: (shopId: string, aliasId: string) =>
    request<void>(`/api/v1/shops/${shopId}/size-aliases/${aliasId}`, { method: 'DELETE' }),
  testVariantResolver: (shopId: string, payload: { product_id: string; raw_color?: string; raw_size?: string; quantity: number }) =>
    request<VariantResolverResult>(`/api/v1/shops/${shopId}/variant-resolver/test`, { method: 'POST', body: JSON.stringify(payload) }),
  listUnavailableDemand: (shopId: string) => request<UnavailableDemandLog[]>(`/api/v1/shops/${shopId}/unavailable-demand`),
  listShopMembers: (shopId: string) => request<ShopMember[]>(`/api/v1/shops/${shopId}/members`),
  listInstagramAccounts: (shopId: string) =>
    request<InstagramAccount[]>(`/api/v1/shops/${shopId}/instagram-accounts`),
  createInstagramAccount: (shopId: string, payload: InstagramAccountCreate) =>
    request<InstagramAccount>(`/api/v1/shops/${shopId}/instagram-accounts`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listConversations: (shopId: string, filters: ConversationListFilters = {}) =>
    request<Conversation[]>(
      `/api/v1/shops/${shopId}/conversations${buildQuery({
        state: filters.state,
        handoff_required:
          filters.handoff_required === undefined ? undefined : String(filters.handoff_required),
        assigned_operator_id: filters.assigned_operator_id,
        unassigned: filters.unassigned === undefined ? undefined : String(filters.unassigned),
        updated_from: filters.updated_from,
        updated_to: filters.updated_to,
        search: filters.search,
        urgent: filters.urgent === undefined ? undefined : String(filters.urgent),
        high_priority: filters.high_priority === undefined ? undefined : String(filters.high_priority),
        needs_attention: filters.needs_attention === undefined ? undefined : String(filters.needs_attention),
        waiting_for_payment:
          filters.waiting_for_payment === undefined ? undefined : String(filters.waiting_for_payment),
        ready_to_order: filters.ready_to_order === undefined ? undefined : String(filters.ready_to_order),
        low_confidence: filters.low_confidence === undefined ? undefined : String(filters.low_confidence),
        assigned_to_me: filters.assigned_to_me === undefined ? undefined : String(filters.assigned_to_me),
        is_simulation: filters.is_simulation === undefined ? undefined : String(filters.is_simulation),
      })}`,
    ),
  getConversation: (shopId: string, conversationId: string) =>
    request<ConversationDetail>(`/api/v1/shops/${shopId}/conversations/${conversationId}`),
  listSuggestedReplies: (shopId: string, conversationId?: string) =>
    request<SuggestedReply[]>(`/api/v1/shops/${shopId}/suggested-replies${buildQuery({ conversation_id: conversationId })}`),
  approveSuggestedReply: (shopId: string, replyId: string) =>
    request<SuggestedReply>(`/api/v1/shops/${shopId}/suggested-replies/${replyId}/approve`, { method: 'POST' }),
  editAndSendSuggestedReply: (shopId: string, replyId: string, editedText: string) =>
    request<SuggestedReply>(`/api/v1/shops/${shopId}/suggested-replies/${replyId}/edit-and-send`, { method: 'POST', body: JSON.stringify({ edited_text: editedText }) }),
  rejectSuggestedReply: (shopId: string, replyId: string, reason?: string) =>
    request<SuggestedReply>(`/api/v1/shops/${shopId}/suggested-replies/${replyId}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }),
  sendConversationMessage: (shopId: string, conversationId: string, payload: MessageCreate) =>
    request<Message>(`/api/v1/shops/${shopId}/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  takeOverConversation: (shopId: string, conversationId: string) =>
    request<ConversationHandoffResponse>(
      `/api/v1/shops/${shopId}/conversations/${conversationId}/take-over`,
      { method: 'POST' },
    ),
  releaseConversationToAgent: (shopId: string, conversationId: string) =>
    request<ConversationHandoffResponse>(
      `/api/v1/shops/${shopId}/conversations/${conversationId}/release-to-agent`,
      { method: 'POST' },
    ),
  assignConversation: (shopId: string, conversationId: string, operatorId: string) =>
    request<{ conversation_id: string; assigned_operator_id: string; assigned_operator_name: string | null }>(
      `/api/v1/shops/${shopId}/conversations/${conversationId}/assign`,
      { method: 'POST', body: JSON.stringify({ operator_id: operatorId }) },
    ),
  markConversationResolved: (shopId: string, conversationId: string) =>
    request<ConversationResolveResponse>(
      `/api/v1/shops/${shopId}/conversations/${conversationId}/mark-resolved`,
      { method: 'POST' },
    ),
  updateConversationCustomer: (shopId: string, conversationId: string, payload: CustomerUpdate) =>
    request<Customer>(`/api/v1/shops/${shopId}/conversations/${conversationId}/customer`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  createOrderFromConversation: (shopId: string, conversationId: string) =>
    request<Order>(`/api/v1/shops/${shopId}/conversations/${conversationId}/orders`, {
      method: 'POST',
    }),
  semanticProductSearch: (shopId: string, query: string, limit = 5) =>
    request<SemanticSearchResponse>(`/api/v1/shops/${shopId}/semantic-search`, {
      method: 'POST',
      body: JSON.stringify({ query, limit }),
    }),
  listProducts: (shopId: string) => request<Product[]>(`/api/v1/shops/${shopId}/products`),
  createProduct: (shopId: string, payload: ProductCreate) =>
    request<Product>(`/api/v1/shops/${shopId}/products`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getProduct: (shopId: string, productId: string) =>
    request<Product>(`/api/v1/shops/${shopId}/products/${productId}`),
  updateProduct: (shopId: string, productId: string, payload: ProductUpdate) =>
    request<Product>(`/api/v1/shops/${shopId}/products/${productId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteProduct: (shopId: string, productId: string) =>
    request<void>(`/api/v1/shops/${shopId}/products/${productId}`, { method: 'DELETE' }),
  listVariants: (shopId: string, productId: string) =>
    request<ProductVariant[]>(`/api/v1/shops/${shopId}/products/${productId}/variants`),
  createVariant: (shopId: string, productId: string, payload: VariantCreate) =>
    request<ProductVariant>(`/api/v1/shops/${shopId}/products/${productId}/variants`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateVariant: (shopId: string, variantId: string, payload: VariantUpdate) =>
    request<ProductVariant>(`/api/v1/shops/${shopId}/variants/${variantId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  listInstagramProductMaps: (shopId: string) =>
    request<InstagramProductMap[]>(`/api/v1/shops/${shopId}/instagram-product-maps`),
  createInstagramProductMap: (shopId: string, payload: InstagramProductMapCreate) =>
    request<InstagramProductMap>(`/api/v1/shops/${shopId}/instagram-product-maps`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  resolveInstagramProduct: (shopId: string, payload: ResolveInstagramProductRequest) =>
    request<ResolveInstagramProductResponse>(`/api/v1/shops/${shopId}/resolve-instagram-product`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listOrders: (shopId: string, filters: OrderListFilters = {}) =>
    request<Order[]>(
      `/api/v1/shops/${shopId}/orders${buildQuery({
        status: filters.status,
        payment_status: filters.payment_status,
        shipping_status: filters.shipping_status,
        created_from: filters.created_from,
        created_to: filters.created_to,
      })}`,
    ),
  getOrder: (shopId: string, orderId: string) =>
    request<Order>(`/api/v1/shops/${shopId}/orders/${orderId}`),
  confirmOrder: (shopId: string, orderId: string) =>
    request<Order>(`/api/v1/shops/${shopId}/orders/${orderId}/confirm`, { method: 'POST' }),
  cancelOrder: (shopId: string, orderId: string, payload: OrderCancelRequest) =>
    request<Order>(`/api/v1/shops/${shopId}/orders/${orderId}/cancel`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  sendPaymentLink: (shopId: string, orderId: string) =>
    request<Order>(`/api/v1/shops/${shopId}/orders/${orderId}/send-payment-link`, { method: 'POST' }),
  markOrderPaid: (shopId: string, orderId: string) =>
    request<Order>(`/api/v1/shops/${shopId}/orders/${orderId}/mark-paid`, { method: 'POST' }),
  sendTrackingCode: (shopId: string, orderId: string, payload: OrderShipRequest) =>
    request<Order>(`/api/v1/shops/${shopId}/orders/${orderId}/send-tracking-code`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  shipOrder: (shopId: string, orderId: string, payload: OrderShipRequest) =>
    request<Order>(`/api/v1/shops/${shopId}/orders/${orderId}/ship`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getOrderCorrectness: (orderId: string) =>
    request<OrderCorrectnessRead>(`/api/v1/orders/${orderId}`),
  getOrderTimeline: (orderId: string) =>
    request<OrderTimelineResponse>(`/api/v1/orders/${orderId}/timeline`),
  confirmOrderCorrectness: (orderId: string, payload: OrderConfirmRequest = {}) =>
    request<OrderCorrectnessRead>(`/api/v1/orders/${orderId}/confirm`, {
      method: 'POST',
      body: JSON.stringify({ confirmation_source: 'operator', ...payload }),
    }),
  cancelOrderCorrectness: (orderId: string, payload: OrderCancelRequest = {}) =>
    request<OrderCorrectnessRead>(`/api/v1/orders/${orderId}/cancel`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  reserveOrder: (orderId: string, ttl_seconds = 1800) =>
    request<OrderCorrectnessRead>(`/api/v1/orders/${orderId}/reserve`, {
      method: 'POST',
      body: JSON.stringify({ ttl_seconds }),
    }),
  paymentLinkOrder: (orderId: string) =>
    request<OrderCorrectnessRead>(`/api/v1/orders/${orderId}/payment-link`, { method: 'POST' }),
  rejectOrderCorrectness: (orderId: string, reason?: string) =>
    request<OrderCorrectnessRead>(`/api/v1/orders/${orderId}/confirm`, {
      method: 'POST',
      body: JSON.stringify({
        confirmation_source: 'operator',
        operator_decision: 'rejected',
        reason,
      }),
    }),
};
