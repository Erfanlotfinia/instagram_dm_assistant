import { useShop } from '../contexts/ShopContext';
import { HubPage } from '../components/shell/HubPage';
import { Badge } from '../components/ui';
import { Card, CardBody, CardHeader } from '../components/ui';
import { QuickReplyPanel } from '../components/operator/QuickReplyPanel';
import { DEFAULT_QUICK_REPLY_TEMPLATES } from '../lib/quickReplies';

/**
 * Sprint 5 — Quick replies manager page at /operator/quick-replies.
 * Frontend-first: default templates plus per-shop custom templates stored in
 * localStorage (TEMPORARY until a backend template API exists).
 */
export function QuickRepliesPage() {
  const { selectedShopId } = useShop();

  return (
    <HubPage
      eyebrow="Operations"
      title="Quick Replies"
      description="Reusable reply drafts. Copy or insert — review and approve before sending. No auto-send."
      actions={<Badge tone="neutral">{DEFAULT_QUICK_REPLY_TEMPLATES.length} defaults</Badge>}
    >
      <Card>
        <CardHeader
          title="Reply library"
          description="Custom templates are stored in your browser (per shop) until backend persistence is added."
        />
        <CardBody>
          <QuickReplyPanel shopId={selectedShopId} allowCreate />
        </CardBody>
      </Card>
    </HubPage>
  );
}
