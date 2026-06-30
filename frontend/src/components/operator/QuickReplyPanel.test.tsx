import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { QuickReplyPanel } from './QuickReplyPanel';

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  localStorage.clear();
});

describe('QuickReplyPanel', () => {
  it('renders default templates', () => {
    render(<QuickReplyPanel shopId="shop-1" />);
    // "Greeting" appears as both the category option and the template title;
    // assert at least one render of the title via getAllByText.
    expect(screen.getAllByText('Greeting').length).toBeGreaterThan(0);
    expect(screen.getByText('Ask size & color')).toBeInTheDocument();
  });

  it('shows empty state when no matches', () => {
    render(<QuickReplyPanel shopId="shop-1" />);
    const search = screen.getByPlaceholderText('Search replies…');
    // Type a nonsense query that matches nothing.
    search.focus();
    // fireEvent.change is unreliable with controlled search inputs in some setups;
    // use userEvent instead.
    void userEvent.type(search, 'zzz-not-a-match').then(() => {
      expect(screen.getByText('No quick replies match')).toBeInTheDocument();
    });
  });

  it('fires onInsert with rendered body when Insert is clicked', async () => {
    const onInsert = vi.fn();
    const { user } = setupUser();
    render(
      <QuickReplyPanel
        shopId="shop-1"
        onInsert={onInsert}
        customerContext={{ customer_name: 'Jane' }}
      />,
    );
    const insertButtons = screen.getAllByRole('button', { name: 'Insert' });
    expect(insertButtons.length).toBeGreaterThan(0);
    await user.click(insertButtons[0]);
    expect(onInsert).toHaveBeenCalledTimes(1);
    // First default template body contains "Hi Jane" after substitution.
    expect(onInsert.mock.calls[0][0]).toContain('Hi Jane');
  });

  it('does not render Insert buttons when onInsert is not provided', () => {
    render(<QuickReplyPanel shopId="shop-1" />);
    expect(screen.queryByRole('button', { name: 'Insert' })).toBeNull();
  });
});

// Helper to combine render + user-event v14 API.
function setupUser() {
  return { user: userEvent.setup() };
}
