import { useQuery } from '@tanstack/react-query';

import { EmptyState, LoadingState } from '../data';
import { queryKeys } from '../../lib/queryClient';
import { apiClient } from '../../services/apiClient';

interface OrderTimelineTabProps {
  orderId: string;
}

export function OrderTimelineTab({ orderId }: OrderTimelineTabProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: queryKeys.orderTimeline(orderId),
    queryFn: () => apiClient.getOrderTimeline(orderId),
  });

  if (isLoading) {
    return <LoadingState label="Loading timeline…" />;
  }

  if (isError || !data) {
    return <EmptyState title="Unable to load timeline" />;
  }

  if (data.entries.length === 0) {
    return <EmptyState title="No timeline events yet" />;
  }

  return (
    <ol className="timeline-list" aria-label="Order audit timeline">
      {data.entries.map((entry, index) => (
        <li key={`${entry.entry_type}-${entry.occurred_at}-${index}`} className="timeline-list__item">
          <div className="timeline-list__marker" />
          <div className="timeline-list__content">
            <p className="timeline-list__label">{entry.label}</p>
            <p className="timeline-list__meta">
              {entry.entry_type} · {new Date(entry.occurred_at).toLocaleString()}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
