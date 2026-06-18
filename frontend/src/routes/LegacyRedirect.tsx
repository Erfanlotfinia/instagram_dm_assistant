import { Navigate, useParams, useLocation } from 'react-router-dom';

/**
 * Redirects an old route to its new hub location, preserving a single path
 * param and the existing query string for bookmark compatibility.
 */
export function LegacyRedirect({ to, param }: { to: string; param?: string }) {
  const params = useParams();
  const location = useLocation();
  const resolved = param && params[param] ? `${to}/${params[param]}` : to;
  const search = location.search ?? '';
  return <Navigate to={`${resolved}${search}`} replace />;
}
