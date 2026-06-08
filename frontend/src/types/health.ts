export interface HealthResponse {
  status: 'ok';
}

export type ReadinessCheckStatus = 'ok' | 'error';

export interface ReadinessResponse {
  status: 'ok' | 'degraded' | 'failed';
  checks: {
    postgres: ReadinessCheckStatus;
    redis: ReadinessCheckStatus;
    rabbitmq: ReadinessCheckStatus;
    qdrant: ReadinessCheckStatus;
    openai_config: ReadinessCheckStatus;
  };
}

export interface FailedJob {
  id: string;
  shop_id: string | null;
  queue_name: string;
  job_type: string;
  payload: Record<string, unknown>;
  error_message: string | null;
  traceback: string | null;
  retry_count: number;
  max_retries: number;
  status: 'failed' | 'retried' | 'ignored';
  created_at: string;
  updated_at: string;
}

export interface FailedJobListResponse {
  items: FailedJob[];
  total: number;
  page: number;
  page_size: number;
}
