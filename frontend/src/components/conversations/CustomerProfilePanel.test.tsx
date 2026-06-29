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

  it('renders a valid hex color swatch and keeps the label visible', () => {
    const { container } = render(
      <CustomerProfilePanel
        profile={{
          id: 'c2',
          instagram_user_id: 'ig-2',
          full_name: 'Pooya',
          phone: null,
          city: null,
          address: null,
          postal_code: null,
          notes: null,
          previous_orders: [],
          preferred_size: null,
          preferred_colors: ['#FF0000', 'Navy'],
          last_successful_size: null,
          last_purchase_at: null,
          total_paid_amount: '0.00',
          order_count: 0,
          is_repeat_customer: false,
        }}
        onSave={vi.fn()}
      />,
    );

    // Label text remains visible for both colors.
    expect(screen.getByText(/#FF0000, Navy/)).toBeInTheDocument();

    // First swatch uses the normalized hex background; second uses the safe name.
    // jsdom normalizes `#ff0000` to `rgb(255, 0, 0)` — accept either form.
    const swatches = container.querySelectorAll('span[style*="background"]');
    expect(swatches).toHaveLength(2);
    expect((swatches[0] as HTMLElement).style.backgroundColor).toMatch(/#ff0000|rgb\(255,\s*0,\s*0\)/i);
    expect((swatches[1] as HTMLElement).style.backgroundColor).toMatch(/navy|rgb\(0,\s*0,\s*128\)/i);
  });

  it('falls back to the border token for an unsafe color while keeping the label visible', () => {
    const { container } = render(
      <CustomerProfilePanel
        profile={{
          id: 'c3',
          instagram_user_id: 'ig-3',
          full_name: 'Sara',
          phone: null,
          city: null,
          address: null,
          postal_code: null,
          notes: null,
          previous_orders: [],
          preferred_size: null,
          preferred_colors: ['url(javascript:alert(1))'],
          last_successful_size: null,
          last_purchase_at: null,
          total_paid_amount: '0.00',
          order_count: 0,
          is_repeat_customer: false,
        }}
        onSave={vi.fn()}
      />,
    );

    // Label text remains visible even when the swatch is sanitized away.
    expect(screen.getByText(/url\(javascript:alert\(1\)\)/)).toBeInTheDocument();
    const swatch = container.querySelector('span[style*="background"]') as HTMLElement | null;
    expect(swatch).not.toBeNull();
    expect((swatch as HTMLElement).style.background).not.toContain('javascript');
  });
});
