import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { ShopSwitcher } from './ShopSwitcher';
import { ThemeToggle } from './ThemeToggle';
import { Icons } from '../icons';
import { useAuth } from '../../contexts/AuthContext';
import { useCommandPaletteStore } from '../../stores/commandPaletteStore';
import { useShellBadges } from '../../hooks/useShellBadges';
import { cn } from '../../lib/cn';

interface TopBarProps {
  onToggleSidebar: () => void;
}

export function TopBar({ onToggleSidebar }: TopBarProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const openPalette = useCommandPaletteStore((state) => state.setOpen);
  const badges = useShellBadges();
  const alerts = badges.handoffs + badges.failedJobs;
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setMenuOpen(false);
      }
    }

    function onPointerDown(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }

    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('mousedown', onPointerDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('mousedown', onPointerDown);
    };
  }, [menuOpen]);

  function handleSignOut() {
    setMenuOpen(false);
    logout();
  }

  function handleProfile() {
    setMenuOpen(false);
    navigate('/profile');
  }

  const menuItemClass = 'flex w-full items-center gap-2 px-3 py-2 text-sm text-fg hover:bg-surface-sunken';

  return (
    <header className="cc-themed sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-surface/95 px-4 backdrop-blur">
      <button
        type="button"
        onClick={onToggleSidebar}
        aria-label="Toggle navigation"
        className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted hover:bg-surface-sunken hover:text-fg lg:hidden"
      >
        <Icons.menu size={20} />
      </button>

      <ShopSwitcher />

      <button
        type="button"
        onClick={() => openPalette(true)}
        className="ml-auto hidden h-9 items-center gap-2 rounded-lg border border-border bg-surface-sunken px-3 text-sm text-muted hover:text-fg sm:flex"
      >
        <Icons.search size={15} />
        <span>Search</span>
        <kbd className="rounded border border-border bg-surface px-1.5 py-0.5 text-[10px]">Ctrl K</kbd>
      </button>

      <button
        type="button"
        onClick={() => openPalette(true)}
        aria-label="Open command palette"
        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-muted hover:bg-surface-sunken hover:text-fg sm:hidden"
      >
        <Icons.search size={18} />
      </button>

      <button
        type="button"
        onClick={() => navigate('/handoffs')}
        aria-label={`Notifications${alerts ? `, ${alerts} pending` : ''}`}
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-muted hover:bg-surface-sunken hover:text-fg"
      >
        <Icons.bell size={18} />
        {alerts > 0 ? (
          <span className="absolute -right-1 -top-1 inline-flex min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold text-white">
            {alerts > 99 ? '99+' : alerts}
          </span>
        ) : null}
      </button>

      <ThemeToggle />

      <div className="relative" ref={menuRef}>
        <button
          type="button"
          onClick={() => setMenuOpen((open) => !open)}
          aria-expanded={menuOpen}
          aria-haspopup="menu"
          aria-label="Account menu"
          className={cn(
            'flex items-center gap-2 rounded-lg border border-border px-2 py-1 transition-colors hover:bg-surface-sunken',
            menuOpen && 'bg-surface-sunken',
          )}
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-fg">
            {user?.full_name?.charAt(0).toUpperCase() ?? '?'}
          </span>
          <div className="hidden leading-tight md:block">
            <p className="max-w-[140px] truncate text-left text-xs font-medium text-fg">{user?.full_name}</p>
            <p className="text-left text-[11px] capitalize text-subtle">{user?.role}</p>
          </div>
          <Icons.chevronDown
            size={14}
            className={cn('hidden shrink-0 text-subtle transition-transform md:block', menuOpen && 'rotate-180')}
          />
        </button>

        {menuOpen ? (
          <div
            role="menu"
            aria-label="Account actions"
            className="absolute right-0 top-[calc(100%+0.375rem)] z-40 min-w-[180px] overflow-hidden rounded-lg border border-border bg-surface py-1 shadow-[0_12px_32px_rgba(15,23,42,0.12)] dark:shadow-[0_12px_32px_rgba(0,0,0,0.45)]"
          >
            <button
              type="button"
              role="menuitem"
              onClick={handleProfile}
              className={menuItemClass}
            >
              <Icons.user size={16} className="text-muted" />
              Profile
            </button>
            <div className="my-1 border-t border-border" role="separator" />
            <button
              type="button"
              role="menuitem"
              onClick={handleSignOut}
              className={menuItemClass}
            >
              <Icons.logOut size={16} className="text-muted" />
              Sign out
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}
