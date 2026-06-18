import { useParams } from 'react-router-dom';

import { ConversationDetailPanel } from '../components/inbox/ConversationDetailPanel';
import { InboxList } from '../components/inbox/InboxList';
import { Icons } from '../components/icons';

export function InboxPage() {
  const { conversationId } = useParams<{ conversationId: string }>();

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-accent">Inbox</p>
        <h1 className="mt-0.5 text-xl font-semibold text-fg">Unified Inbox</h1>
        <p className="mt-1 text-sm text-muted">
          Every channel in one queue. Automation status, intent, and product context at a glance.
        </p>
      </div>

      <div className="grid h-[calc(100vh-13rem)] grid-cols-1 overflow-hidden rounded-[var(--radius-card)] border border-border bg-surface lg:grid-cols-[360px_1fr]">
        <div className="hidden min-h-0 border-r border-border lg:block">
          <InboxList activeId={conversationId} />
        </div>

        {/* On small screens, show the list when nothing is selected, else the detail. */}
        <div className="min-h-0 lg:hidden">{conversationId ? null : <InboxList activeId={conversationId} />}</div>

        <div className="min-h-0 overflow-y-auto">
          {conversationId ? (
            <ConversationDetailPanel conversationId={conversationId} />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 p-10 text-center">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-sunken text-subtle">
                <Icons.inbox size={24} />
              </span>
              <p className="text-sm font-medium text-fg">Select a conversation</p>
              <p className="max-w-xs text-xs text-muted">
                Pick a thread from the list to view messages, order context, and the AI decision trace.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
