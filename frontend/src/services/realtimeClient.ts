import { tokenStorage } from './tokenStorage';

export interface RealtimeEvent {
  type: string;
  payload: Record<string, unknown>;
  timestamp?: string;
}

type Listener = (event: RealtimeEvent) => void;

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

function wsUrl(shopId: string, token: string): string {
  const base = API_BASE_URL || window.location.origin;
  const url = new URL(`/api/v1/ws/shops/${shopId}`, base);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.searchParams.set('token', token);
  return url.toString();
}

/**
 * Resilient WebSocket wrapper for shop realtime events with automatic
 * reconnection and exponential backoff. Polling remains the source of truth,
 * so a dropped socket only delays freshness, never breaks the UI.
 */
export class RealtimeClient {
  private socket: WebSocket | null = null;
  private listeners = new Set<Listener>();
  private reconnectAttempts = 0;
  private reconnectTimer: number | null = null;
  private closedByUser = false;

  constructor(private readonly shopId: string) {}

  connect(): void {
    const token = tokenStorage.get();
    if (!token || !this.shopId) {
      return;
    }
    this.closedByUser = false;
    try {
      this.socket = new WebSocket(wsUrl(this.shopId, token));
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
    };
    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as RealtimeEvent;
        if (data.type === 'ping') {
          return;
        }
        for (const listener of this.listeners) {
          listener(data);
        }
      } catch {
        // Ignore malformed frames.
      }
    };
    this.socket.onclose = () => {
      if (!this.closedByUser) {
        this.scheduleReconnect();
      }
    };
    this.socket.onerror = () => {
      this.socket?.close();
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null) {
      return;
    }
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30_000);
    this.reconnectAttempts += 1;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  close(): void {
    this.closedByUser = true;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.socket?.close();
    this.socket = null;
    this.listeners.clear();
  }
}
