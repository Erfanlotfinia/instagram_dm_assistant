import { cn } from '../../lib/cn';

type Channel = 'instagram' | 'whatsapp' | 'telegram' | 'bale' | 'rubika' | 'web_chat';

const CHANNEL_META: Record<Channel, { short: string; label: string; className: string }> = {
  instagram: { short: 'IG', label: 'Instagram', className: 'bg-accent-soft text-accent' },
  whatsapp: { short: 'WA', label: 'WhatsApp', className: 'bg-success-soft text-success' },
  telegram: { short: 'TG', label: 'Telegram', className: 'bg-info-soft text-info' },
  bale: { short: 'BA', label: 'Bale', className: 'bg-warning-soft text-warning' },
  rubika: { short: 'RU', label: 'Rubika', className: 'border border-border-strong bg-surface-sunken text-muted' },
  web_chat: { short: 'WB', label: 'Web Chat', className: 'bg-surface-sunken text-muted' },
};

interface ChannelBadgeProps {
  channel?: string | null;
  showLabel?: boolean;
  className?: string;
}

export function ChannelBadge({ channel, showLabel = false, className }: ChannelBadgeProps) {
  const key = (channel ?? 'instagram') as Channel;
  const meta = CHANNEL_META[key] ?? CHANNEL_META.web_chat;
  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <span
        className={cn('inline-flex h-5 min-w-5 items-center justify-center rounded px-1 text-[10px] font-bold', meta.className)}
        title={meta.label}
      >
        {meta.short}
      </span>
      {showLabel ? <span className="text-xs text-muted">{meta.label}</span> : null}
    </span>
  );
}
