import type { ReactNode } from 'react';

import { cn } from '../../lib/cn';

interface SectionPanelProps {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  variant?: 'default' | 'compose';
  className?: string;
}

export function SectionPanel({ title, actions, children, variant = 'default', className }: SectionPanelProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-border p-4',
        variant === 'compose' ? 'bg-surface' : 'bg-surface-sunken',
        className,
      )}
    >
      {title || actions ? (
        <div className="mb-3 flex items-center justify-between gap-2">
          {title ? (
            <p className="text-xs font-bold uppercase tracking-wide text-muted">{title}</p>
          ) : (
            <span />
          )}
          {actions}
        </div>
      ) : null}
      {children}
    </div>
  );
}
