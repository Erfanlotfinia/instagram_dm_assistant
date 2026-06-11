import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import type { PropsWithChildren, ReactNode } from 'react';

import { useAuth } from '../contexts/AuthContext';

type NavItem = { to: string; label: string; icon: string };
type NavGroup = { label?: string; items: NavItem[]; defaultCollapsed?: boolean };

const navGroups: NavGroup[] = [
  {
    items: [{ to: '/', label: 'Dashboard', icon: 'home' }],
  },
  {
    label: 'Inbox',
    items: [
      { to: '/conversations', label: 'Conversations', icon: 'message' },
      { to: '/orders', label: 'Orders', icon: 'bag' },
    ],
  },
  {
    label: 'Catalog',
    items: [
      { to: '/products', label: 'Products', icon: 'box' },
      { to: '/instagram-mapping', label: 'Post Mapping', icon: 'image' },
      { to: '/catalog-copilot', label: 'Catalog Copilot', icon: 'sparkles' },
      { to: '/variant-resolver', label: 'Variant Resolver', icon: 'sliders' },
      { to: '/fashion-dictionary', label: 'Fashion Dictionary', icon: 'book' },
    ],
  },
  {
    label: 'Insights',
    items: [
      { to: '/analytics', label: 'Analytics', icon: 'bar-chart' },
      { to: '/post-revenue', label: 'Post Revenue', icon: 'trending-up' },
      { to: '/unavailable-demand', label: 'Unavailable Demand', icon: 'alert-circle' },
    ],
  },
  {
    label: 'Automation',
    items: [
      { to: '/agent-studio', label: 'Agent Studio', icon: 'cpu' },
      { to: '/triggers', label: 'Trigger Rules', icon: 'zap' },
      { to: '/recovery-rules', label: 'Recovery Rules', icon: 'refresh' },
      { to: '/upsell-rules', label: 'Upsell Rules', icon: 'trending-up' },
      { to: '/risk-settings', label: 'Risk Settings', icon: 'shield' },
    ],
  },
  {
    label: 'Testing & rollout',
    defaultCollapsed: true,
    items: [
      { to: '/simulator', label: 'DM Simulator', icon: 'play' },
      { to: '/onboarding', label: 'Onboarding', icon: 'rocket' },
      { to: '/pilot-control', label: 'Pilot Control', icon: 'compass' },
      { to: '/pilot-readiness', label: 'Pilot Readiness', icon: 'check-circle' },
      { to: '/incidents', label: 'Incidents', icon: 'alert-triangle' },
      { to: '/trl-validation', label: 'TRL Validation', icon: 'clipboard' },
    ],
  },
  {
    label: 'Administration',
    defaultCollapsed: true,
    items: [
      { to: '/shops', label: 'Shops', icon: 'store' },
      { to: '/instagram-accounts', label: 'Instagram Accounts', icon: 'at-sign' },
      { to: '/settings', label: 'Settings', icon: 'gear' },
      { to: '/system-health', label: 'System Health', icon: 'activity' },
      { to: '/failed-jobs', label: 'Failed Jobs', icon: 'alert-octagon' },
    ],
  },
];

const ICONS: Record<string, ReactNode> = {
  home: <path d="M3 10.5 12 3l9 7.5M5 9.5V21h14V9.5" />,
  message: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
  bag: <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4zM3 6h18M16 10a4 4 0 0 1-8 0" />,
  box: (
    <>
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <path d="M3.27 6.96 12 12.01l8.73-5.05M12 22.08V12" />
    </>
  ),
  image: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="8.5" cy="8.5" r="1.5" />
      <path d="M21 15l-5-5L5 21" />
    </>
  ),
  sparkles: <path d="M12 3l1.9 5.8L20 10.7l-5.1 1.9L12 18.4l-1.9-5.8L5 10.7l5.1-1.9z" />,
  sliders: <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6" />,
  book: <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 19.5A2.5 2.5 0 0 0 6.5 22H20V2H6.5A2.5 2.5 0 0 0 4 4.5z" />,
  'bar-chart': <path d="M12 20V10M18 20V4M6 20v-4" />,
  'trending-up': <path d="M23 6l-9.5 9.5-5-5L1 18M17 6h6v6" />,
  'alert-circle': (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v4M12 16h.01" />
    </>
  ),
  cpu: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <rect x="9" y="9" width="6" height="6" />
      <path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3" />
    </>
  ),
  zap: <path d="M13 2 3 14h7l-1 8 10-12h-7z" />,
  refresh: <path d="M23 4v6h-6M1 20v-6h6M3.5 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.65 4.36A9 9 0 0 0 20.5 15" />,
  shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />,
  play: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M10 8l6 4-6 4z" />
    </>
  ),
  rocket: <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09zM12 15l-3-3a22 22 0 0 1 8-10c4 0 5 1 5 5a22 22 0 0 1-10 8z" />,
  compass: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M16 8l-2 6-6 2 2-6z" />
    </>
  ),
  'check-circle': <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4 12 14.01l-3-3" />,
  'alert-triangle': <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01" />,
  clipboard: (
    <>
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <rect x="8" y="2" width="8" height="4" rx="1" />
      <path d="M9 14l2 2 4-4" />
    </>
  ),
  store: <path d="M3 9l1.5-5h15L21 9M4 9v11h16V9M4 9h16M9 20v-6h6v6" />,
  'at-sign': (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M16 12v1.5a2.5 2.5 0 0 0 5 0V12a9 9 0 1 0-3.5 7.1" />
    </>
  ),
  gear: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </>
  ),
  activity: <path d="M22 12h-4l-3 9L9 3l-3 9H2" />,
  'alert-octagon': (
    <>
      <path d="M7.86 2h8.28L22 7.86v8.28L16.14 22H7.86L2 16.14V7.86z" />
      <path d="M12 8v4M12 16h.01" />
    </>
  ),
};

function NavIcon({ name }: { name: string }) {
  return (
    <svg
      className="sidebar__icon"
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name] ?? <circle cx="12" cy="12" r="3" />}
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg className="sidebar__chevron" viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
      <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true">
      <circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M11 11l3 3" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

const STORAGE_KEY = 'sidebar:collapsed-groups';

function loadCollapsed(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

export function AppLayout({ children }: PropsWithChildren) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [query, setQuery] = useState('');
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() => {
    const stored = loadCollapsed();
    const initial: Record<string, boolean> = {};
    for (const group of navGroups) {
      if (group.label) {
        initial[group.label] = stored[group.label] ?? Boolean(group.defaultCollapsed);
      }
    }
    return initial;
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(collapsed));
    } catch {
      // Ignore storage failures (e.g. private mode).
    }
  }, [collapsed]);

  function isActive(path: string): boolean {
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  }

  function toggleGroup(label: string) {
    setCollapsed((current) => ({ ...current, [label]: !current[label] }));
  }

  const normalizedQuery = query.trim().toLowerCase();
  const isFiltering = normalizedQuery.length > 0;

  const visibleGroups = useMemo(() => {
    if (!isFiltering) {
      return navGroups;
    }
    return navGroups
      .map((group) => ({
        ...group,
        items: group.items.filter((item) => item.label.toLowerCase().includes(normalizedQuery)),
      }))
      .filter((group) => group.items.length > 0);
  }, [isFiltering, normalizedQuery]);

  function renderItems(items: NavItem[]) {
    return items.map((item) => (
      <Link
        key={item.to}
        className={`sidebar__link${isActive(item.to) ? ' sidebar__link--active' : ''}`}
        to={item.to}
        aria-current={isActive(item.to) ? 'page' : undefined}
      >
        <NavIcon name={item.icon} />
        <span className="sidebar__link-label">{item.label}</span>
      </Link>
    ));
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="sidebar__head">
          <h1 className="sidebar__brand">DM Assistant</h1>
        </div>

        <div className="sidebar__search">
          <span className="sidebar__search-icon">
            <SearchIcon />
          </span>
          <input
            type="search"
            className="sidebar__search-input"
            placeholder="Search menu…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="Search navigation"
          />
        </div>

        <nav className="sidebar__nav" aria-label="Sections">
          {visibleGroups.map((group) => {
            if (!group.label) {
              return (
                <div key="home" className="sidebar__nav-group">
                  {renderItems(group.items)}
                </div>
              );
            }

            const hasActive = group.items.some((item) => isActive(item.to));
            const open = isFiltering || hasActive || !collapsed[group.label];
            const panelId = `nav-group-${group.label.replace(/\s+/g, '-').toLowerCase()}`;

            return (
              <div key={group.label} className="sidebar__nav-group">
                <button
                  type="button"
                  className="sidebar__nav-toggle"
                  aria-expanded={open}
                  aria-controls={panelId}
                  onClick={() => toggleGroup(group.label!)}
                  disabled={isFiltering}
                >
                  <span className="sidebar__nav-label">{group.label}</span>
                  <ChevronIcon />
                </button>
                {open ? (
                  <div id={panelId} className="sidebar__nav-items">
                    {renderItems(group.items)}
                  </div>
                ) : null}
              </div>
            );
          })}

          {isFiltering && visibleGroups.length === 0 ? (
            <p className="sidebar__empty">No pages match “{query}”.</p>
          ) : null}
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
