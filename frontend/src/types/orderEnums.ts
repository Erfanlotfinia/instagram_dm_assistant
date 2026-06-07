export type OrderStatus =
  | 'draft'
  | 'waiting_for_confirmation'
  | 'confirmed'
  | 'waiting_for_payment'
  | 'paid'
  | 'preparing'
  | 'shipped'
  | 'completed'
  | 'cancelled'
  | 'expired';

export type OrderPaymentStatus = 'unpaid' | 'pending' | 'paid' | 'failed' | 'refunded';

export type OrderShippingStatus = 'not_started' | 'preparing' | 'shipped' | 'delivered';

export type PaymentProvider = 'manual' | 'zarinpal' | 'nextpay' | 'idpay' | 'mock';

export type PaymentRecordStatus = 'created' | 'pending' | 'paid' | 'failed' | 'cancelled';

export type ShipmentProvider = 'manual' | 'post' | 'tipax' | 'chapar' | 'other';

export type ShipmentStatus = 'pending' | 'preparing' | 'shipped' | 'delivered' | 'failed';

export const ORDER_STATUS_OPTIONS: OrderStatus[] = [
  'draft',
  'waiting_for_confirmation',
  'confirmed',
  'waiting_for_payment',
  'paid',
  'preparing',
  'shipped',
  'completed',
  'cancelled',
  'expired',
];

export const PAYMENT_STATUS_OPTIONS: OrderPaymentStatus[] = [
  'unpaid',
  'pending',
  'paid',
  'failed',
  'refunded',
];

export const SHIPPING_STATUS_OPTIONS: OrderShippingStatus[] = [
  'not_started',
  'preparing',
  'shipped',
  'delivered',
];
