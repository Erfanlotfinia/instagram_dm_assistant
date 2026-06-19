import type { ReactNode } from 'react';

import { Icons } from '../icons';
import { cn } from '../../lib/cn';

interface FilterBarProps {
  search?: string;
  onSearch?: (value: string) => void;
  searchPlaceholder?: string;
  children?: ReactNode;
  className?: string;
}

/** Stripe-style fast filter row: search + inline filter controls. */
export function FilterBar({
  search,
  onSearch,
  searchPlaceholder = 'Search…',
  children,
  className,
}: FilterBarProps) {
  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      {onSearch ? (
        <div className="relative min-w-[200px] flex-1">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-subtle">
            <Icons.search size={15} />
          </span>
          <input
            type="search"
            value={search ?? ''}
            onChange={(event) => onSearch(event.target.value)}
            placeholder={searchPlaceholder}
            className="h-9 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-fg placeholder:text-subtle focus:border-accent focus:outline-none"
          />
        </div>
      ) : null}
      {children}
    </div>
  );
}
