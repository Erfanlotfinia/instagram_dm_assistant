import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { CustomerProfilePanel } from './CustomerProfilePanel';

describe('CustomerProfilePanel', () => {
  it('renders customer preferences and purchase stats', () => {
    render(
      <CustomerProfilePanel
        profile={{
          id: 'c1',
          instagram_user_id: 'ig-1',
          full_name: 'Sara',
          phone: '0912',
          city: 'Tehran',
          address: 'Street 1',
          postal_code: '123',
          notes: null,
          previous_orders: [],
          preferred_size: 'M',
          preferred_colors: ['Black', 'Navy'],
          last_successful_size: 'M',
          last_purchase_at: '2026-01-01T00:00:00Z',
          total_paid_amount: '99.00',
          order_count: 2,
          is_repeat_customer: true,
        }}
        onSave={vi.fn()}
      />,
    );

    expect(screen.getByText('Preferred size').closest('div')).toHaveTextContent('M');
    expect(screen.getByText('Previous successful size').closest('div')).toHaveTextContent('M');
    expect(screen.getByText('Total paid').closest('div')).toHaveTextContent('99.00');
    expect(screen.getByText(/Black, Navy/)).toBeInTheDocument();
  });
});
