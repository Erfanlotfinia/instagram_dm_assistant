import type {
  OrderPaymentStatus,
  OrderShippingStatus,
  OrderStatus,
  PaymentProvider,
  PaymentRecordStatus,
  ShipmentProvider,
  ShipmentStatus,
} from './orderEnums';

export type OrderItem = {
  id: string;
  product_id: string | null;
  product_variant_id: string | null;
  product_title_snapshot: string;
  variant_color_snapshot: string | null;
  variant_size_snapshot: string | null;
  sku_snapshot: string;
  quantity: number;
  unit_price: string;
  total_price: string;
};

export type Payment = {
  id: string;
  provider: PaymentProvider;
  status: PaymentRecordStatus;
  payment_url: string | null;
  provider_reference: string | null;
  created_at: string;
  updated_at: string;
};

export type Shipment = {
  id: string;
  provider: ShipmentProvider;
  status: ShipmentStatus;
  tracking_code: string | null;
  tracking_url: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  created_at: string;
  updated_at: string;
};

export type OrderTimelineEvent = {
  status: string;
  label: string;
  occurred_at: string;
  source: string;
};

export type Order = {
  id: string;
  shop_id: string;
  customer_id: string;
  conversation_id: string;
  status: OrderStatus;
  subtotal_amount: string;
  shipping_amount: string;
  discount_amount: string;
  total_amount: string;
  currency: string;
  payment_status: OrderPaymentStatus;
  shipping_status: OrderShippingStatus;
  customer_name: string;
  phone: string;
  city: string;
  address: string;
  postal_code: string;
  notes: string | null;
  risk_flags?: string[];
  approval_source?: string | null;
  payment_callback_status?: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
  payments: Payment[];
  shipments: Shipment[];
  timeline: OrderTimelineEvent[];
};

export type OrderListFilters = {
  status?: OrderStatus;
  payment_status?: OrderPaymentStatus;
  shipping_status?: OrderShippingStatus;
  created_from?: string;
  created_to?: string;
};

export type OrderShipRequest = {
  tracking_code: string;
  tracking_url?: string;
  provider?: ShipmentProvider;
};

export type OrderCancelRequest = {
  reason?: string;
};
