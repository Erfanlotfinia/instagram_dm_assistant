import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { RiskSettingsPage } from './RiskSettingsPage';

vi.mock('../contexts/ShopContext', () => ({ useShop: () => ({ selectedShop: null }) }));

describe('RiskSettingsPage', () => {
  it('asks for a selected shop before rendering the form', () => {
    render(<RiskSettingsPage />);
    expect(screen.getByText(/Select a shop/)).toBeInTheDocument();
  });
});
