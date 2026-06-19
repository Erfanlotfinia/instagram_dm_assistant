import { Suspense, type ReactNode } from 'react';

import { LoadingState } from '../components/data';

export function RouteSuspense({ children }: { children: ReactNode }) {
  return <Suspense fallback={<LoadingState label="Loading page…" />}>{children}</Suspense>;
}
