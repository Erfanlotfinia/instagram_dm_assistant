import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { LoginPage } from '../pages/LoginPage';
import { AuthProvider } from '../contexts/AuthContext';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    login: vi.fn(),
    getMe: vi.fn().mockRejectedValue(new Error('not authenticated')),
  },
}));

describe('LoginPage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('shows validation errors for invalid credentials input', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>,
    );

    const emailInput = screen.getByLabelText('Email');
    await user.clear(emailInput);
    await user.type(emailInput, 'not-an-email');

    const passwordInput = screen.getByLabelText('Password');
    await user.clear(passwordInput);
    await user.type(passwordInput, 'short');

    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByText('Enter a valid email address')).toBeInTheDocument();
    expect(screen.getByText('Password must be at least 8 characters')).toBeInTheDocument();
  });
});
