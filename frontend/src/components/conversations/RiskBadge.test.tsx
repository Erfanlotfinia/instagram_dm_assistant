import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RiskBadge } from './RiskBadge';

describe('RiskBadge', () => {
  it('renders risk level and score', () => {
    render(<RiskBadge level="critical" score={0.95} />);
    expect(screen.getByText(/Critical risk/)).toBeInTheDocument();
    expect(screen.getByText(/95%/)).toBeInTheDocument();
  });
});
