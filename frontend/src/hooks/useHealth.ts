import { useEffect, useState } from 'react';

import { apiClient } from '../services/apiClient';
import type { HealthResponse } from '../types/health';

export function useHealth() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    apiClient
      .getHealth()
      .then((response) => {
        if (isMounted) setData(response);
      })
      .catch((caughtError: Error) => {
        if (isMounted) setError(caughtError);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return { data, error, isLoading };
}
