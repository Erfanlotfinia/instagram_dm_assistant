import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PriorityBadge } from './PriorityBadge';

describe('PriorityBadge', () => {
  it('renders level and score', () => {
    render(<PriorityBadge level="high" score={62} reason="Payment waiting" />);
    expect(screen.getByText('high (62)')).toBeInTheDocument();
  });
});
