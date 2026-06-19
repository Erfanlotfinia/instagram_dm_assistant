import { Outlet } from 'react-router-dom';

import type { TabItem } from '../ui';
import { Tabs } from '../ui';

interface HubLayoutProps {
  tabs: TabItem[];
}

/** Renders the sub-tab navigation for a hub above its nested routes. */
export function HubLayout({ tabs }: HubLayoutProps) {
  return (
    <div className="flex flex-col gap-4">
      <Tabs items={tabs} />
      <Outlet />
    </div>
  );
}
