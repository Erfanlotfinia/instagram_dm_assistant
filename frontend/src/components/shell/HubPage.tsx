import type { ReactNode } from 'react';

import { PageHeader } from '../data';

interface HubPageProps {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** Standard page scaffold for hub sub-routes inside AppShell. */
export function HubPage({ eyebrow, title, description, actions, children, className }: HubPageProps) {
  return (
    <div className={className ?? 'flex flex-col gap-5'}>
      <PageHeader eyebrow={eyebrow} title={title} description={description} actions={actions} />
      {children}
    </div>
  );
}
