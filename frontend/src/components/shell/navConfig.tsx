import type { ComponentType } from 'react';

import { Icons } from '../icons';
import type { TabItem } from '../ui';
import type { UserRole } from '../../types/auth';

export interface HubDef {
  id: string;
  label: string;
  /** Top-level path used for active matching and the default landing route. */
  path: string;
  icon: ComponentType<{ size?: number }>;
  /** Roles allowed to see the hub. Undefined means all roles. */
  roles?: UserRole[];
  /** Optional dynamic badge key resolved by the sidebar. */
  badge?: 'handoffs' | 'failedJobs';
  /** Horizontal sub-tabs shown inside the hub. */
  tabs?: TabItem[];
}

export const HUBS: HubDef[] = [
  {
    id: 'overview',
    label: 'Overview',
    path: '/',
    icon: Icons.overview,
  },
  {
    id: 'inbox',
    label: 'Inbox',
    path: '/inbox',
    icon: Icons.inbox,
  },
  {
    id: 'catalog',
    label: 'Catalog',
    path: '/catalog',
    icon: Icons.catalog,
    tabs: [
      { to: '/catalog/products', label: 'Products' },
      { to: '/catalog/attributes', label: 'Attributes' },
      { to: '/catalog/resolver', label: 'Resolver' },
      { to: '/catalog/mapping', label: 'Mapping' },
    ],
  },
  {
    id: 'orders',
    label: 'Orders',
    path: '/orders',
    icon: Icons.orders,
  },
  {
    id: 'automation',
    label: 'Automation',
    path: '/automation',
    icon: Icons.automation,
    roles: ['owner', 'admin'],
    tabs: [
      { to: '/automation/rules', label: 'Rules' },
      { to: '/automation/coverage', label: 'Coverage' },
      { to: '/automation/triggers', label: 'Triggers' },
      { to: '/automation/recovery', label: 'Recovery' },
      { to: '/automation/upsell', label: 'Upsell' },
      { to: '/automation/suggestions', label: 'Suggestions' },
      { to: '/automation/simulator', label: 'Simulator' },
      { to: '/automation/scenario-simulator', label: 'Regression' },
      { to: '/automation/risk', label: 'Risk' },
    ],
  },
  {
    id: 'ai',
    label: 'AI Control',
    path: '/ai',
    icon: Icons.ai,
    roles: ['owner', 'admin'],
    tabs: [
      { to: '/ai/overview', label: 'Overview' },
      { to: '/ai/logs', label: 'LLM Logs' },
      { to: '/ai/fallbacks', label: 'Fallbacks' },
      { to: '/ai/safety', label: 'Safety' },
      { to: '/ai/corrections', label: 'Corrections' },
      { to: '/ai/tasks', label: 'Tasks' },
    ],
  },
  {
    id: 'handoffs',
    label: 'Handoffs',
    path: '/handoffs',
    icon: Icons.handoffs,
    badge: 'handoffs',
  },
  {
    id: 'analytics',
    label: 'Analytics',
    path: '/analytics',
    icon: Icons.analytics,
    tabs: [
      { to: '/analytics/overview', label: 'Overview' },
      { to: '/analytics/revenue', label: 'Revenue' },
      { to: '/analytics/demand', label: 'Demand' },
      { to: '/analytics/recovery', label: 'Recovery' },
      { to: '/analytics/channels', label: 'Channels' },
    ],
  },
  {
    id: 'system',
    label: 'System',
    path: '/system',
    icon: Icons.system,
    roles: ['owner', 'admin'],
    badge: 'failedJobs',
    tabs: [
      { to: '/system/health', label: 'Health' },
      { to: '/system/jobs', label: 'Failed Jobs' },
      { to: '/system/channels', label: 'Channels' },
      { to: '/system/channels/onboarding', label: 'Onboarding' },
      { to: '/system/readiness', label: 'Readiness' },
      { to: '/system/shops', label: 'Shops' },
      { to: '/system/rollout', label: 'Rollout' },
      { to: '/system/settings', label: 'Settings' },
    ],
  },
];

export function hubsForRole(role: UserRole | undefined): HubDef[] {
  if (!role) {
    return HUBS;
  }
  return HUBS.filter((hub) => !hub.roles || hub.roles.includes(role));
}

export function findHub(pathname: string): HubDef | undefined {
  if (pathname === '/') {
    return HUBS[0];
  }
  return HUBS.find((hub) => hub.path !== '/' && pathname.startsWith(hub.path));
}
