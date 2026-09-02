/**
 * apiFetch — authenticated fetch wrapper for HireEngine.
 *
 * Usage:
 *   const api = createApiFetch(token, onUnauthorized);
 *   const data = await api('/api/v1/candidates');
 *
 * Automatically:
 *  - Injects Authorization: Bearer <token> header
 *  - Calls onUnauthorized() on any 401 response (triggers logout)
 */
export const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export function createApiFetch(token: string, onUnauthorized: () => void) {
  return async function apiFetch(
    url: string,
    options: RequestInit = {}
  ): Promise<Response> {
    const headers = new Headers(options.headers ?? {});
    headers.set('Authorization', `Bearer ${token}`);

    const fullUrl = `${API_BASE_URL}${url}`;
    const res = await fetch(fullUrl, { ...options, headers });

    if (res.status === 401) {
      onUnauthorized();
      // Return the response so callers can still inspect it if needed
    }

    return res;
  };
}

export type ApiFetch = ReturnType<typeof createApiFetch>;
