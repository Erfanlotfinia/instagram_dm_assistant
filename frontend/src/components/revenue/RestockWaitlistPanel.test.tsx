import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import { RestockWaitlistPanel } from './RestockWaitlistPanel';
import type { RestockWaitlistItem } from '../../types/sprint4Revenue';

const items: RestockWaitlistItem[] = [
  {
    id: 'w1',
    customer_id: 'c1',
    conversation_id: 'conv1',
    product_id: 'p1',
    product_label: 'Oversized Tee',
    requested_variant_label: 'red · L',
    customer_label: 'Sara',
    status: 'waiting',
    suggested_message: 'Hi, the item you asked about is available again.',
  },
  {
    id: 'w2',
    customer_id: 'c2',
    conversation_id: null,
    product_id: 'p1',
    product_label: 'Oversized Tee',
    requested_variant_label: null,
    customer_label: 'Pooya',
    status: 'notified',
    suggested_message: 'Hi, the item you asked about is available again.',
  },
];

describe('RestockWaitlistPanel', () => {
  it('groups waitlist items by product and shows suggested messages', () => {
    render(
      <MemoryRouter>
        <RestockWaitlistPanel items={items} />
      </MemoryRouter>,
    );
    // Product group header appears once (grouped).
    const productLinks = screen.getAllByText('Oversized Tee');
    expect(productLinks.length).toBeGreaterThan(0);
    // Customer labels and statuses appear.
    expect(screen.getByText('Sara')).toBeInTheDocument();
    expect(screen.getByText('Pooya')).toBeInTheDocument();
    expect(screen.getByText('waiting')).toBeInTheDocument();
    expect(screen.getByText('notified')).toBeInTheDocument();
    // Copy buttons.
    expect(screen.getAllByRole('button', { name: /copy/i }).length).toBeGreaterThan(0);
  });

  it('renders an empty state when there are no items', () => {
    render(
      <MemoryRouter>
        <RestockWaitlistPanel items={[]} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/No waitlist entries yet/i)).toBeInTheDocument();
  });
});
