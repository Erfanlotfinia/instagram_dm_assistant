import type { ReactNode } from 'react';

import { cn } from '../../lib/cn';

interface StatusBannerProps {
  tone: 'ok' | 'failed' | 'warning';
  title: string;
  description: ReactNode;
  icon?: ReactNode;
  className?: string;
}

const toneStyles = {
  ok: {
    border: 'border-success/30',
    bg: 'bg-success-soft',
    dot: 'bg-success',
    label: 'Success',
  },
  failed: {
    border: 'border-danger/30',
    bg: 'bg-danger-soft',
    dot: 'bg-danger',
    label: 'Error',
  },
  warning: {
    border: 'border-warning/30',
    bg: 'bg-warning-soft',
    dot: 'bg-warning',
    label: 'Warning',
  },
} as const;

export function StatusBanner({ tone, title, description, icon, className }: StatusBannerProps) {
  const styles = toneStyles[tone];
  return (
    <div
      className={cn('flex gap-3 rounded-lg border p-4', styles.border, styles.bg, className)}
      role="status"
      aria-label={styles.label}
    >
      {icon ? (
        <span className="mt-0.5 shrink-0 text-fg" aria-hidden="true">
          {icon}
        </span>
      ) : (
        <span className={cn('mt-1 h-2.5 w-2.5 shrink-0 rounded-full', styles.dot)} aria-hidden="true" />
      )}
      <div>
        <p className="font-semibold text-fg">{title}</p>
        <p className="mt-0.5 text-sm text-muted">{description}</p>
      </div>
    </div>
  );
}
