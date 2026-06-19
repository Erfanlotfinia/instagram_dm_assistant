import { describe, expect, it } from 'vitest';

import { getAutomationStatus } from './AutomationStatusBadge';
import type { Conversation } from '../../types/conversation';

type Flags = Parameters<typeof getAutomationStatus>[0];

function conv(overrides: Partial<Flags>): Flags {
  return {
    handoff_required: false,
    agent_paused: false,
    workflow_state: 'agent_active' as Conversation['workflow_state'],
    preview_required: false,
    confidence_score: 0.9,
    agent_mode: 'controlled_autopilot',
    ...overrides,
  };
}

describe('getAutomationStatus', () => {
  it('returns human when handoff is required', () => {
    expect(getAutomationStatus(conv({ handoff_required: true }))).toBe('human');
  });

  it('returns human when the agent is paused', () => {
    expect(getAutomationStatus(conv({ agent_paused: true }))).toBe('human');
  });

  it('returns preview when a reply awaits review', () => {
    expect(getAutomationStatus(conv({ preview_required: true }))).toBe('preview');
  });

  it('returns llm for low confidence conversations', () => {
    expect(getAutomationStatus(conv({ confidence_score: 0.4 }))).toBe('llm');
  });

  it('returns automated for confident, unpaused conversations', () => {
    expect(getAutomationStatus(conv({}))).toBe('automated');
  });

  it('prioritises handoff over preview', () => {
    expect(getAutomationStatus(conv({ handoff_required: true, preview_required: true }))).toBe('human');
  });
});
