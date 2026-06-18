import type { ButtonHTMLAttributes, ReactNode } from 'react';

import { cn } from '../../lib/cn';

interface FilterChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
  children: ReactNode;
}

export function FilterChip({ active, children, className, type = 'button', ...props }: FilterChipProps) {
  return (
    <button
      type={type}
      aria-pressed={active}
      className={cn(
        'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
        active ? 'border-accent bg-accent-soft text-accent' : 'border-border bg-surface text-muted hover:text-fg',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
