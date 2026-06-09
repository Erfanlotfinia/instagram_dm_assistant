import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { DecisionTraceDrawer } from './DecisionTraceDrawer';
import type { AssembledDecisionTrace } from '../../types/trust';

const trace: AssembledDecisionTrace = {
  trace_id: 'trace-1',
  shop_id: 'shop-1',
  header: { intent: 'buy_product', next_state: 'waiting_for_customer_info', auto_send_allowed: false },
  retrieval_evidence: [],
  slots_extracted: [],
  confidence_bands: [],
  policy_checks: [
    {
      id: 'e1',
      trace_id: 'trace-1',
      shop_id: 'shop-1',
      sequence: 1,
      event_type: 'policy_check',
      payload_json: { name: 'explicit_confirmation_required', passed: true },
      created_at: '2026-06-09T00:00:00Z',
    },
  ],
  actions_attempted: [],
  actions_blocked: [],
  all_events: [],
};

describe('DecisionTraceDrawer', () => {
  it('renders trace details when open', () => {
    render(<DecisionTraceDrawer open trace={trace} onClose={vi.fn()} />);

    expect(screen.getByRole('complementary', { name: /decision trace drawer/i })).toBeInTheDocument();
    expect(screen.getByText('trace-1')).toBeInTheDocument();
    expect(screen.getByText('buy_product')).toBeInTheDocument();
    expect(screen.getByText(/explicit_confirmation_required/i)).toBeInTheDocument();
  });

  it('calls onClose when close is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<DecisionTraceDrawer open trace={trace} onClose={onClose} />);

    await user.click(screen.getByRole('button', { name: /close/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it('renders nothing when closed', () => {
    render(<DecisionTraceDrawer open={false} trace={trace} onClose={vi.fn()} />);
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
  });
});
