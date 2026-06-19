import type { ReactNode } from 'react';

import { cn } from '../../lib/cn';

interface CalloutProps {
  icon?: ReactNode;
  title: string;
  children: ReactNode;
  className?: string;
}

export function Callout({ icon, title, children, className }: CalloutProps) {
  return (
    <div
      className={cn(
        'mt-5 flex items-start gap-3 rounded-lg border border-accent/30 bg-gradient-to-br from-accent-soft/50 to-surface p-4',
        className,
      )}
    >
      {icon ? (
        <span
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-bold text-accent-fg"
          aria-hidden="true"
        >
          {icon}
        </span>
      ) : null}
      <div className="min-w-0">
        <p className="font-semibold text-fg">{title}</p>
        <div className="mt-0.5 text-sm leading-relaxed text-muted">{children}</div>
      </div>
    </div>
  );
}
