import type { ReactNode } from 'react';

import { cn } from '../../lib/cn';

interface RadioCardProps {
  active?: boolean;
  label: string;
  description?: string;
  onClick: () => void;
  className?: string;
}

export function RadioCard({ active, label, description, onClick, className }: RadioCardProps) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      onClick={onClick}
      className={cn(
        'grid gap-1.5 rounded-lg border bg-surface p-4 text-left transition-colors',
        active
          ? 'border-accent bg-accent-soft shadow-[inset_0_0_0_1px_var(--color-accent)]'
          : 'border-border hover:border-accent/40',
        className,
      )}
    >
      <span className="font-semibold text-fg">{label}</span>
      {description ? <span className="text-sm leading-snug text-muted">{description}</span> : null}
    </button>
  );
}

interface RadioCardGridProps {
  label?: string;
  children: ReactNode;
  className?: string;
  'aria-label'?: string;
}

export function RadioCardGrid({ label, children, className, 'aria-label': ariaLabel }: RadioCardGridProps) {
  return (
    <div className={cn('grid gap-2', className)}>
      {label ? <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p> : null}
      <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label={ariaLabel}>
        {children}
      </div>
    </div>
  );
}
