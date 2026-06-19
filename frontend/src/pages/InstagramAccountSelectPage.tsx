import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { InstagramAccountSelection } from '../components/channels/InstagramAccountSelection';
import { Card, CardBody, CardHeader } from '../components/ui';
import { useToast } from '../contexts/ToastContext';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';
import type { InstagramCandidateAccount, InstagramConnectSession } from '../types/channel';

export function InstagramAccountSelectPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const [session, setSession] = useState<InstagramConnectSession | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedShopId || !sessionId) {
      setError('Missing shop or session context.');
      return;
    }
    void apiClient
      .getInstagramConnectSession(selectedShopId, sessionId)
      .then((value) => {
        setSession(value);
        if (value.status !== 'account_selection_required') {
          setError('This session does not require account selection.');
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Could not load session');
      });
  }, [selectedShopId, sessionId]);

  async function handleSelect(candidate: InstagramCandidateAccount) {
    if (!selectedShopId || !sessionId) {
      return;
    }
    await apiClient.selectInstagramAccount(selectedShopId, sessionId, {
      page_id: candidate.page_id,
      instagram_business_account_id: candidate.instagram_business_account_id,
    });
    showToast('Instagram connected successfully.', 'success');
    navigate('/system/channels');
  }

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-4 p-6">
      <Card>
        <CardHeader title="Select Instagram account" />
        <CardBody>
          {error ? <p className="text-sm text-danger">{error}</p> : null}
          {session?.candidate_accounts?.length ? (
            <InstagramAccountSelection
              candidates={session.candidate_accounts}
              onSelect={handleSelect}
            />
          ) : !error ? (
            <p className="text-sm text-muted">Loading accounts…</p>
          ) : null}
        </CardBody>
      </Card>
    </div>
  );
}
