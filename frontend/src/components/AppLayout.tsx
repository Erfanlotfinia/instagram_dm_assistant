import { Link, useLocation } from 'react-router-dom';
import type { PropsWithChildren } from 'react';

import { useAuth } from '../contexts/AuthContext';
import { useShop } from '../contexts/ShopContext';

export function AppLayout({ children }: PropsWithChildren) {
  const { user, logout } = useAuth();
  const { selectedShop } = useShop();
  const location = useLocation();

  const navItems = [
    { to: '/', label: 'Dashboard' },
    { to: '/onboarding', label: 'Onboarding' },
    { to: '/simulator', label: 'DM Simulator' },
    { to: '/analytics', label: 'Analytics' },
    { to: '/fashion-dictionary', label: 'Fashion Dictionary' },
    { to: '/variant-resolver', label: 'Variant Resolver' },
    { to: '/unavailable-demand', label: 'Unavailable Demand' },
    { to: '/triggers', label: 'Trigger Rules' },
    { to: '/agent-studio', label: 'Agent Studio' },
    { to: '/conversations', label: 'Conversations' },
    { to: '/orders', label: 'Orders' },
    { to: '/products', label: 'Products' },
    { to: '/instagram-mapping', label: 'Post Mapping' },
    { to: '/instagram-accounts', label: 'Instagram Accounts' },
    { to: '/shops', label: 'Shops' },
    { to: '/settings', label: 'Settings' },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <h1 className="sidebar__brand">DM Assistant</h1>
        {selectedShop ? <p className="sidebar__shop">{selectedShop.name}</p> : null}
        <nav className="sidebar__nav">
          {navItems.map((item) => (
            <Link
              key={item.to}
              className={`sidebar__link${
                location.pathname === item.to || location.pathname.startsWith(`${item.to}/`)
                  ? ' sidebar__link--active'
                  : ''
              }`}
              to={item.to}
            >
              {item.label}
            </Link>
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
