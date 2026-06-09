import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ReservationStatusChip } from './ReservationStatusChip';

describe('ReservationStatusChip', () => {
  it('shows no reservation when empty', () => {
    render(<ReservationStatusChip reservations={[]} />);
    expect(screen.getByText('No reservation')).toBeInTheDocument();
  });

  it('shows active reservation', () => {
    render(
      <ReservationStatusChip
        reservations={[
          {
            id: 'r1',
            product_variant_id: 'v1',
            quantity: 2,
            status: 'active',
            expires_at: '2030-01-01T00:00:00Z',
          },
        ]}
      />,
    );
    expect(screen.getByText(/Reserved: 2/)).toBeInTheDocument();
  });
});
