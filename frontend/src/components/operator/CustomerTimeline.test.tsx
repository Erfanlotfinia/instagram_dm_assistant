import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { CustomerTimeline } from './CustomerTimeline';
import type { CustomerTimelineItem } from '../../types/sprint5Operator';

describe('CustomerTimeline', () => {
  it('renders empty state when no items', () => {
    render(<CustomerTimeline items={[]} />);
    expect(screen.getByText('No timeline yet')).toBeInTheDocument();
  });

  it('renders items with type badges and titles', () => {
    const items: CustomerTimelineItem[] = [
      {
        id: 'a',
        type: 'order',
        title: 'Order placed',
        description: '$55',
        created_at: new Date(Date.now() - 60_000).toISOString(),
      },
      {
        id: 'b',
        type: 'message',
        title: 'Customer message',
        description: 'hello',
        created_at: new Date(Date.now() - 120_000).toISOString(),
      },
      {
        id: 'c',
        type: 'handoff',
        title: 'Handoff required',
        created_at: new Date(Date.now() - 180_000).toISOString(),
        action_to: '/inbox/c1/intelligence',
      },
    ];
    render(
      <MemoryRouter>
        <CustomerTimeline items={items} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Order placed')).toBeInTheDocument();
    expect(screen.getByText('Customer message')).toBeInTheDocument();
    expect(screen.getByText('Handoff required')).toBeInTheDocument();
    // Action link rendered
    expect(screen.getByText('Open →').closest('a')).toHaveAttribute('href', '/inbox/c1/intelligence');
  });

  it('renders error message when error prop set', () => {
    render(<CustomerTimeline items={[]} error="Failed to load" />);
    expect(screen.getByText('Failed to load')).toBeInTheDocument();
  });
});
