import { NavLink } from 'react-router-dom';

import { hubsForRole } from './navConfig';
import type { HubDef } from './navConfig';
import { useShellBadges } from '../../hooks/useShellBadges';
import { useAuth } from '../../contexts/AuthContext';
import { cn } from '../../lib/cn';

interface SidebarNavProps {
  collapsed: boolean;
  onNavigate?: () => void;
}

export function SidebarNav({ collapsed, onNavigate }: SidebarNavProps) {
  const { user } = useAuth();
  const badges = useShellBadges();
  const hubs = hubsForRole(user?.role);

  function badgeCount(hub: HubDef): number {
    if (hub.badge === 'handoffs') {
      return badges.handoffs;
    }
    if (hub.badge === 'failedJobs') {
      return badges.failedJobs;
    }
    return 0;
  }

  return (
    <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-3 py-3" aria-label="Primary">
      {hubs.map((hub) => {
        const Icon = hub.icon;
        const count = badgeCount(hub);
        return (
          <NavLink
            key={hub.id}
            to={hub.path}
            end={hub.path === '/'}
            onClick={onNavigate}
            title={collapsed ? hub.label : undefined}
            className={({ isActive }) =>
              cn(
                'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                collapsed && 'justify-center px-0',
                isActive
                  ? 'bg-accent-soft text-accent'
                  : 'text-muted hover:bg-surface-sunken hover:text-fg',
              )
            }
          >
            <span className="shrink-0">
              <Icon size={19} />
            </span>
            {!collapsed ? <span className="flex-1 truncate">{hub.label}</span> : null}
            {count > 0 ? (
              <span
                className={cn(
                  'inline-flex min-w-5 items-center justify-center rounded-full bg-accent px-1.5 text-xs font-semibold text-accent-fg',
                  collapsed && 'absolute right-1 top-1 min-w-4 px-1 text-[10px]',
                )}
              >
                {count > 99 ? '99+' : count}
              </span>
            ) : null}
          </NavLink>
        );
      })}
    </nav>
  );
}
