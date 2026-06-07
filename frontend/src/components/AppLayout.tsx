import { Link } from 'react-router-dom';
import type { PropsWithChildren } from 'react';

export function AppLayout({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <h1 className="sidebar__brand">DM Assistant</h1>
        <nav className="sidebar__nav">
          <Link className="sidebar__link" to="/">
            Dashboard
          </Link>
        </nav>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
