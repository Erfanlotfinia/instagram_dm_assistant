import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { Button, Card, CardBody, CardHeader } from '../components/ui';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';
import { INSTAGRAM_CONNECT_ERROR_MESSAGES } from '../lib/channelAccounts';

export function InstagramConnectCallbackPage() {
  const { selectedShopId } = useShop();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [message, setMessage] = useState('Finishing Instagram connection…');

  const sessionId = searchParams.get('session_id');
  const status = searchParams.get('status');
  const errorCode = searchParams.get('error');

  useEffect(() => {
    if (!selectedShopId || !sessionId) {
      if (status === 'failed' && errorCode) {
        setMessage(
          INSTAGRAM_CONNECT_ERROR_MESSAGES[errorCode] ?? 'Instagram connection failed. Try again.',
        );
      } else if (status === 'connected') {
        setMessage('Instagram connected successfully.');
      }
      return;
    }

    void apiClient
      .getInstagramConnectSession(selectedShopId, sessionId)
      .then((session) => {
        if (session.status === 'connected') {
          setMessage('Instagram connected successfully.');
          return;
        }
        if (session.error_code || session.error_message) {
          setMessage(
            session.error_message ??
              INSTAGRAM_CONNECT_ERROR_MESSAGES[session.error_code ?? ''] ??
              'Instagram connection failed.',
          );
        }
      })
      .catch(() => {
        if (errorCode) {
          setMessage(
            INSTAGRAM_CONNECT_ERROR_MESSAGES[errorCode] ?? 'Instagram connection failed. Try again.',
          );
        }
      });
  }, [selectedShopId, sessionId, status, errorCode]);

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-4 p-6">
      <Card>
        <CardHeader title="Instagram connection" />
        <CardBody className="flex flex-col gap-4">
          <p className="text-sm text-fg">{message}</p>
          <Button type="button" onClick={() => navigate('/system/channels')}>
            Back to channels
          </Button>
          {status === 'failed' ? (
            <Link className="text-sm text-info" to="/system/channels">
              Try Connect Instagram again
            </Link>
          ) : null}
        </CardBody>
      </Card>
    </div>
  );
}
