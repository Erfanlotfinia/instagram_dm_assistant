import { useEffect, useState } from 'react';
import type { PropsWithChildren } from 'react';
import { useLocation } from 'react-router-dom';

import { CommandPalette } from './CommandPalette';
import { SidebarNav } from './SidebarNav';
import { TopBar } from './TopBar';
import { Icons } from '../icons';
import { useCommandPaletteStore } from '../../stores/commandPaletteStore';
import { useRealtime } from '../../hooks/useRealtime';
import { cn } from '../../lib/cn';

const COLLAPSE_KEY = 'modira:sidebar-collapsed';

export function AppShell({ children }: PropsWithChildren) {
  const location = useLocation();
  const togglePalette = useCommandPaletteStore((state) => state.toggle);
  useRealtime();
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === '1');
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        togglePalette();
      }
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [togglePalette]);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  function toggleCollapse() {
    if (window.innerWidth < 1024) {
      setMobileOpen((open) => !open);
      return;
    }
    setCollapsed((current) => {
      const next = !current;
      localStorage.setItem(COLLAPSE_KEY, next ? '1' : '0');
      return next;
    });
  }

  return (
    <div className="cc-themed flex min-h-screen bg-canvas text-fg">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[70] focus:rounded-md focus:bg-accent focus:px-3 focus:py-2 focus:text-sm focus:text-accent-fg"
      >
        Skip to content
      </a>

      {mobileOpen ? (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-overlay lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      ) : null}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-border bg-surface transition-[width,transform] duration-200 lg:static lg:translate-x-0',
          collapsed ? 'w-[68px]' : 'w-60',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        )}
        aria-label="Sidebar"
      >
        <div className={cn('flex h-14 items-center gap-2 border-b border-border px-4', collapsed && 'justify-center px-0')}>
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent text-sm font-bold text-accent-fg">
            M
          </span>
          {!collapsed ? (
            <div className="leading-tight">
              <p className="text-sm font-semibold text-fg">Modira</p>
              <p className="text-[10px] uppercase tracking-wide text-subtle">Command Center</p>
            </div>
          ) : null}
        </div>

        <SidebarNav collapsed={collapsed} onNavigate={() => setMobileOpen(false)} />

        <button
          type="button"
          onClick={toggleCollapse}
          className="hidden items-center justify-center gap-2 border-t border-border px-3 py-2.5 text-xs text-subtle hover:text-fg lg:flex"
        >
          {collapsed ? <Icons.chevronRight size={16} /> : <Icons.menu size={16} />}
          {!collapsed ? <span>Collapse</span> : null}
        </button>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onToggleSidebar={toggleCollapse} />
        <main id="main-content" className="flex-1 px-4 py-5 sm:px-6">
          {children}
        </main>
      </div>

      <CommandPalette />
    </div>
  );
}
