import type {
  Conversation,
  ConversationDetail,
  ConversationHandoffResponse,
  ConversationListFilters,
  ConversationResolveResponse,
  Customer,
  CustomerUpdate,
  Message,
  MessageCreate,
} from '../types/conversation';
import type { DashboardMetrics } from '../types/dashboard';
import type { AgentStudioSettings, DMSimulatorRequest, DMSimulatorResponse, FunnelAnalytics, HandoffAnalyticsRow, OnboardingStatus, PostPerformanceRow, ResponseTimeAnalytics, StockDemandRow, TriggerPerformance, TriggerRule, UnavailableDemandRow } from '../types/competitive';
import type { SemanticSearchResponse } from '../types/semanticSearch';
import type { LoginRequest, TokenResponse, User } from '../types/auth';
import type { HealthResponse } from '../types/health';
import type { ColorAlias, SizeAlias, UnavailableDemandLog, VariantResolverResult } from '../types/fashion';
import type { InstagramAccount, InstagramAccountCreate } from '../types/instagramAccount';
import type {
  Order,
  OrderCancelRequest,
  OrderListFilters,
  OrderShipRequest,
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

  listTriggerRules: (shopId: string) =>
    request<TriggerRule[]>(`/api/v1/shops/${shopId}/triggers`),
  createTriggerRule: (shopId: string, payload: Partial<TriggerRule>) =>
    request<TriggerRule>(`/api/v1/shops/${shopId}/triggers`, { method: 'POST', body: JSON.stringify(payload) }),
  getTriggerPerformance: (shopId: string) =>
    request<TriggerPerformance[]>(`/api/v1/shops/${shopId}/triggers/performance`),
  getAgentStudioSettings: (shopId: string) =>
    request<AgentStudioSettings>(`/api/v1/shops/${shopId}/agent-studio-settings`),
  updateAgentStudioSettings: (shopId: string, payload: Partial<AgentStudioSettings>) =>
    request<AgentStudioSettings>(`/api/v1/shops/${shopId}/agent-studio-settings`, { method: 'PATCH', body: JSON.stringify(payload) }),
  runDMSimulator: (shopId: string, payload: DMSimulatorRequest) =>
    request<DMSimulatorResponse>(`/api/v1/shops/${shopId}/simulator/dm`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  resetDMSimulator: (shopId: string) =>
    request<{ deleted_conversations: number }>(`/api/v1/shops/${shopId}/simulator/dm`, { method: 'DELETE' }),
  getAnalyticsFunnel: (shopId: string, start?: string, end?: string) =>
    request<FunnelAnalytics>(`/api/v1/shops/${shopId}/analytics/funnel${buildQuery({ start, end })}`),
  getAnalyticsPosts: (shopId: string, start?: string, end?: string) =>
    request<PostPerformanceRow[]>(`/api/v1/shops/${shopId}/analytics/posts${buildQuery({ start, end })}`),
  getAnalyticsStockDemand: (shopId: string, start?: string, end?: string) =>
    request<StockDemandRow[]>(`/api/v1/shops/${shopId}/analytics/stock-demand${buildQuery({ start, end })}`),
  getAnalyticsUnavailableDemand: (shopId: string, start?: string, end?: string) =>
    request<UnavailableDemandRow[]>(`/api/v1/shops/${shopId}/analytics/unavailable-demand${buildQuery({ start, end })}`),
  getAnalyticsResponseTime: (shopId: string, start?: string, end?: string) =>
    request<ResponseTimeAnalytics>(`/api/v1/shops/${shopId}/analytics/response-time${buildQuery({ start, end })}`),
  getAnalyticsHandoff: (shopId: string, start?: string, end?: string) =>
    request<HandoffAnalyticsRow[]>(`/api/v1/shops/${shopId}/analytics/handoff${buildQuery({ start, end })}`),

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
        updated_from: filters.updated_from,
        updated_to: filters.updated_to,
        search: filters.search,
      })}`,
    ),
  getConversation: (shopId: string, conversationId: string) =>
    request<ConversationDetail>(`/api/v1/shops/${shopId}/conversations/${conversationId}`),
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
  markOrderPaid: (shopId: string, orderId: string) =>
    request<Order>(`/api/v1/shops/${shopId}/orders/${orderId}/mark-paid`, { method: 'POST' }),
  shipOrder: (shopId: string, orderId: string, payload: OrderShipRequest) =>
    request<Order>(`/api/v1/shops/${shopId}/orders/${orderId}/ship`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
