import { Icons } from '../icons';
import type { IconName } from '../icons';
import type { ConversationDetail } from '../../types/conversation';

interface GraphNode {
  id: string;
  label: string;
  sub?: string;
  icon: IconName;
  present: boolean;
}

/**
 * Compact relationship map for a conversation: how the customer connects to the
 * resolved product, draft order, channel, and detected intent. Answers part of
 * "why did the system respond this way" by showing the resolved context.
 */
export function ContextGraph({ conversation }: { conversation: ConversationDetail }) {
  const customerName =
    conversation.customer?.full_name ?? conversation.customer?.instagram_user_id ?? 'Customer';

  const center: GraphNode = {
    id: 'conversation',
    label: 'Conversation',
    sub: conversation.workflow_state.replace(/_/g, ' '),
    icon: 'inbox',
    present: true,
  };

  const satellites: GraphNode[] = [
    { id: 'customer', label: customerName, sub: 'Customer', icon: 'user', present: true },
    {
      id: 'channel',
      label: conversation.channel_provider ?? 'instagram',
      sub: 'Channel',
      icon: 'inbox',
      present: true,
    },
    {
      id: 'intent',
      label: conversation.last_intent ?? 'Unknown',
      sub: 'Detected intent',
      icon: 'spark',
      present: Boolean(conversation.last_intent),
    },
    {
      id: 'product',
      label: conversation.linked_product?.title ?? 'Not resolved',
      sub: 'Product',
      icon: 'catalog',
      present: Boolean(conversation.linked_product),
    },
    {
      id: 'order',
      label: conversation.linked_order ? `${conversation.linked_order.status}` : 'No order',
      sub: 'Order',
      icon: 'orders',
      present: Boolean(conversation.linked_order),
    },
  ];

  function Node({ node, primary = false }: { node: GraphNode; primary?: boolean }) {
    const IconCmp = Icons[node.icon];
    return (
      <div
        className={`flex items-center gap-2 rounded-lg border px-3 py-2 ${
          primary
            ? 'border-accent bg-accent-soft text-accent'
            : node.present
            ? 'border-border bg-surface text-fg'
            : 'border-dashed border-border bg-surface text-subtle'
        }`}
      >
        <IconCmp size={16} />
        <div className="min-w-0">
          <p className="truncate text-xs font-medium">{node.label}</p>
          {node.sub ? <p className="truncate text-[11px] opacity-70">{node.sub}</p> : null}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-stretch gap-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {satellites.slice(0, 3).map((node) => (
          <Node key={node.id} node={node} />
        ))}
      </div>
      <div className="flex justify-center">
        <div className="w-full max-w-xs">
          <Node node={center} primary />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-2">
        {satellites.slice(3).map((node) => (
          <Node key={node.id} node={node} />
        ))}
      </div>
    </div>
  );
}
