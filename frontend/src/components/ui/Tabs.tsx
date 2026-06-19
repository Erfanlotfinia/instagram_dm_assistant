import { NavLink } from 'react-router-dom';

import { cn } from '../../lib/cn';

export interface TabItem {
  to: string;
  label: string;
  /** Match nested routes (e.g. detail pages) as active. */
  end?: boolean;
}

interface TabsProps {
  items: TabItem[];
  className?: string;
}

/** Horizontal sub-navigation rendered as route links for a hub. */
export function Tabs({ items, className }: TabsProps) {
  return (
    <nav className={cn('flex gap-1 overflow-x-auto border-b border-border', className)} aria-label="Section tabs">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) =>
            cn(
              '-mb-px whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors',
              isActive
                ? 'border-accent text-fg'
                : 'border-transparent text-muted hover:text-fg',
            )
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
