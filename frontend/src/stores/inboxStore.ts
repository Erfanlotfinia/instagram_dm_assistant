import { create } from 'zustand';

import type { ConversationListFilters } from '../types/conversation';

export type InboxRightPanelTab = 'trace' | 'order' | 'customer';

interface InboxState {
  listFilters: ConversationListFilters;
  rightPanelTab: InboxRightPanelTab;
  setListFilters: (filters: ConversationListFilters) => void;
  setRightPanelTab: (tab: InboxRightPanelTab) => void;
}

export const useInboxStore = create<InboxState>((set) => ({
  listFilters: {},
  rightPanelTab: 'trace',
  setListFilters: (listFilters) => set({ listFilters }),
  setRightPanelTab: (rightPanelTab) => set({ rightPanelTab }),
}));
