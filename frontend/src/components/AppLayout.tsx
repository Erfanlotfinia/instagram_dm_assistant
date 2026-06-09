import { Link, useLocation } from 'react-router-dom';
import type { PropsWithChildren } from 'react';

import { useAuth } from '../contexts/AuthContext';
import { useShop } from '../contexts/ShopContext';

type NavItem = { to: string; label: string };
type NavGroup = { label?: string; items: NavItem[] };

const navGroups: NavGroup[] = [
  {
    items: [{ to: '/', label: 'Dashboard' }],
  },
  {
    label: 'Operations',
    items: [
      { to: '/conversations', label: 'Conversations' },
      { to: '/orders', label: 'Orders' },
      { to: '/products', label: 'Products' },
      { to: '/instagram-mapping', label: 'Post Mapping' },
    ],
  },
  {
    label: 'Insights',
    items: [
      { to: '/analytics', label: 'Analytics' },
      { to: '/post-revenue', label: 'Post Revenue' },
      { to: '/unavailable-demand', label: 'Unavailable Demand' },
    ],
  },
  {
    label: 'Automation',
    items: [
      { to: '/agent-studio', label: 'Agent Studio' },
      { to: '/triggers', label: 'Trigger Rules' },
      { to: '/recovery-rules', label: 'Recovery Rules' },
      { to: '/upsell-rules', label: 'Upsell Rules' },
      { to: '/risk-settings', label: 'Risk Settings' },
    ],
  },
  {
    label: 'Catalog intelligence',
    items: [
      { to: '/catalog-copilot', label: 'Catalog Copilot' },
      { to: '/fashion-dictionary', label: 'Fashion Dictionary' },
      { to: '/variant-resolver', label: 'Variant Resolver' },
    ],
  },
  {
    label: 'Setup & testing',
    items: [
      { to: '/onboarding', label: 'Onboarding' },
      { to: '/simulator', label: 'DM Simulator' },
      { to: '/pilot-control', label: 'Pilot Control' },
      { to: '/pilot-readiness', label: 'Pilot Readiness' },
      { to: '/incidents', label: 'Incidents' },
      { to: '/trl-validation', label: 'TRL Validation' },
    ],
  },
  {
    label: 'Administration',
    items: [
      { to: '/shops', label: 'Shops' },
      { to: '/instagram-accounts', label: 'Instagram Accounts' },
      { to: '/settings', label: 'Settings' },
      { to: '/system-health', label: 'System Health' },
    ],
  },
];

export function AppLayout({ children }: PropsWithChildren) {
  const { user, logout } = useAuth();
  const { selectedShop } = useShop();
  const location = useLocation();

  function isActive(path: string): boolean {
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <h1 className="sidebar__brand">DM Assistant</h1>
        {selectedShop ? <p className="sidebar__shop">{selectedShop.name}</p> : null}
        <nav className="sidebar__nav">
          {navGroups.map((group) => (
            <div key={group.label ?? 'home'} className="sidebar__nav-group">
              {group.label ? <p className="sidebar__nav-label">{group.label}</p> : null}
              {group.items.map((item) => (
                <Link
                  key={item.to}
                  className={`sidebar__link${isActive(item.to) ? ' sidebar__link--active' : ''}`}
                  to={item.to}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar__footer">
          <p className="sidebar__user">{user?.full_name}</p>
          <button className="button button--ghost" type="button" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
