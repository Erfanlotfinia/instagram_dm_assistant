import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { hubsForRole } from './navConfig';
import { Icons } from '../icons';
import { useAuth } from '../../contexts/AuthContext';
import { fuzzyScore } from '../../lib/fuzzy';
import { useCommandPaletteStore } from '../../stores/commandPaletteStore';
import { themeStore } from '../../stores/themeStore';
import { cn } from '../../lib/cn';

interface Command {
  id: string;
  label: string;
  group: string;
  keywords?: string;
  run: () => void;
}

export function CommandPalette() {
  const open = useCommandPaletteStore((state) => state.open);
  const setOpen = useCommandPaletteStore((state) => state.setOpen);
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands = useMemo<Command[]>(() => {
    const go = (path: string) => () => {
      navigate(path);
      setOpen(false);
    };
    const navCommands: Command[] = [];
    for (const hub of hubsForRole(user?.role)) {
      navCommands.push({ id: `hub-${hub.id}`, label: hub.label, group: 'Navigate', run: go(hub.path) });
      for (const tab of hub.tabs ?? []) {
        navCommands.push({
          id: `tab-${tab.to}`,
          label: `${hub.label}: ${tab.label}`,
          group: 'Navigate',
          keywords: tab.label,
          run: go(tab.to),
        });
      }
    }

    const actions: Command[] = [
      { id: 'act-inbox', label: 'Open Unified Inbox', group: 'Actions', run: go('/inbox') },
      { id: 'act-handoffs', label: 'Review Handoff Queue', group: 'Actions', run: go('/handoffs') },
      { id: 'act-new-product', label: 'Create Product', group: 'Actions', run: go('/catalog/products?new=1') },
      { id: 'act-theme-light', label: 'Theme: Light', group: 'Preferences', run: () => { themeStore.setPreference('light'); setOpen(false); } },
      { id: 'act-theme-dark', label: 'Theme: Dark', group: 'Preferences', run: () => { themeStore.setPreference('dark'); setOpen(false); } },
      { id: 'act-theme-system', label: 'Theme: System', group: 'Preferences', run: () => { themeStore.setPreference('system'); setOpen(false); } },
      { id: 'act-logout', label: 'Sign out', group: 'Account', run: () => { setOpen(false); logout(); } },
    ];

    return [...navCommands, ...actions];
  }, [navigate, setOpen, user?.role, logout]);

  const results = useMemo(() => {
    if (!query.trim()) {
      return commands;
    }
    return commands
      .map((command) => ({ command, score: fuzzyScore(query, `${command.label} ${command.keywords ?? ''}`) }))
      .filter((entry): entry is { command: Command; score: number } => entry.score !== null)
      .sort((a, b) => b.score - a.score)
      .map((entry) => entry.command);
  }, [commands, query]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query, open]);

  useEffect(() => {
    if (open) {
      setQuery('');
      const timer = window.setTimeout(() => inputRef.current?.focus(), 10);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [open]);

  if (!open) {
    return null;
  }

  function handleKeyDown(event: React.KeyboardEvent) {
    if (event.key === 'Escape') {
      setOpen(false);
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((index) => Math.min(index + 1, results.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      results[activeIndex]?.run();
    }
  }

  let lastGroup = '';

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center bg-overlay p-4 pt-[12vh]"
      role="presentation"
      onMouseDown={(event) => event.target === event.currentTarget && setOpen(false)}
    >
      <div
        className="cc-themed w-full max-w-xl overflow-hidden rounded-xl border border-border bg-surface shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
      >
        <div className="flex items-center gap-3 border-b border-border px-4">
          <Icons.search size={18} className="text-subtle" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search pages and actions…"
            className="h-12 w-full bg-transparent text-sm text-fg placeholder:text-subtle focus:outline-none"
            aria-label="Command search"
          />
          <kbd className="rounded border border-border px-1.5 py-0.5 text-[10px] text-subtle">Esc</kbd>
        </div>
        <ul className="max-h-80 overflow-y-auto py-2" role="listbox">
          {results.length === 0 ? (
            <li className="px-4 py-6 text-center text-sm text-muted">No matches found.</li>
          ) : (
            results.map((command, index) => {
              const showGroup = command.group !== lastGroup;
              lastGroup = command.group;
              return (
                <li key={command.id}>
                  {showGroup ? (
                    <p className="px-4 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wide text-subtle">
                      {command.group}
                    </p>
                  ) : null}
                  <button
                    type="button"
                    role="option"
                    aria-selected={index === activeIndex}
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => command.run()}
                    className={cn(
                      'flex w-full items-center gap-2 px-4 py-2 text-left text-sm',
                      index === activeIndex ? 'bg-accent-soft text-accent' : 'text-fg hover:bg-surface-sunken',
                    )}
                  >
                    <Icons.chevronRight size={14} className="text-subtle" />
                    {command.label}
                  </button>
                </li>
              );
            })
          )}
        </ul>
      </div>
    </div>
  );
}
