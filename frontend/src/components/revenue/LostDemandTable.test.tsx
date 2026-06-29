import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import { LostDemandTable } from './LostDemandTable';
import type { LostDemandInsight } from '../../types/sprint4Revenue';

const insights: LostDemandInsight[] = [
  {
    product_id: 'p1',
    product_name: 'Oversized Tee',
    variant_label: 'red · L',
    demand_count: 7,
    lost_reason: 'out_of_stock',
    estimated_lost_value: 1500000,
    severity: 'high',
    action_to: '/catalog/products/p1',
  },
  {
    product_id: 'p2',
    product_name: 'Hoodie',
    variant_label: null,
    demand_count: 2,
    lost_reason: 'missing_variant',
    estimated_lost_value: null,
    severity: 'low',
    action_to: '/catalog/products/p2',
  },
];

describe('LostDemandTable', () => {
  it('renders grouped demand rows', () => {
    render(
      <MemoryRouter>
        <LostDemandTable insights={insights} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Oversized Tee — red · L')).toBeInTheDocument();
    expect(screen.getByText('Hoodie')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
  });

  it('renders an empty state when there are no insights', () => {
    render(
      <MemoryRouter>
        <LostDemandTable insights={[]} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/No lost demand grouped yet/i)).toBeInTheDocument();
  });
});
