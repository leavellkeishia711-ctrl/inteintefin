const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let refreshPromise: Promise<void> | null = null;

async function refreshToken(): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Refresh failed');
  const data = await res.json();
  if (data?.access_token) {
    sessionToken = data.access_token;
  }
}

let sessionToken: string | null = null;

export function setSessionToken(token: string | null) {
  sessionToken = token;
}

export class ApiError extends Error {
  constructor(public status: number, public statusText: string, public body?: unknown) {
    super(`API Error ${status}: ${statusText}`);
    this.name = 'ApiError';
  }
}

async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (sessionToken) {
    headers.set('Authorization', `Bearer ${sessionToken}`);
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (res.status === 401 && !path.includes('/auth/refresh')) {
    try {
      if (!refreshPromise) {
        refreshPromise = refreshToken().finally(() => {
          refreshPromise = null;
        });
      }
      await refreshPromise;
      // Retry the original request with the new token
      if (sessionToken) {
        headers.set('Authorization', `Bearer ${sessionToken}`);
      }
      const retryRes = await fetch(`${BASE_URL}${path}`, {
        ...options,
        headers,
        credentials: 'include',
      });
      if (retryRes.status === 401) {
        // Refresh didn't help, redirect to login
        if (typeof window !== 'undefined') {
          const lang = window.location.pathname.startsWith('/ru') ? 'ru' : 'en';
          window.location.href = `/${lang}/login`;
        }
        throw new ApiError(401, 'Unauthorized');
      }
      if (!retryRes.ok) throw new ApiError(retryRes.status, retryRes.statusText);
      return retryRes.json() as Promise<T>;
    } catch (err) {
      if (typeof window !== 'undefined') {
        const lang = window.location.pathname.startsWith('/ru') ? 'ru' : 'en';
        window.location.href = `/${lang}/login`;
      }
      throw err;
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => undefined);
    throw new ApiError(res.status, res.statusText, body);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const api = {
  get: <T = unknown>(path: string) => apiFetch<T>(path),
  post: <T = unknown>(path: string, body?: unknown) =>
    apiFetch<T>(path, {
      method: 'POST',
      body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    }),
  put: <T = unknown>(path: string, body?: unknown) =>
    apiFetch<T>(path, {
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  patch: <T = unknown>(path: string, body?: unknown) =>
    apiFetch<T>(path, {
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  delete: <T = unknown>(path: string) => apiFetch<T>(path, { method: 'DELETE' }),
};

export default api;

// Legacy compatibility exports
export const fetchTransactions = async (params: Record<string, unknown>) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) searchParams.append(key, value.toString());
  });
  return api.get(`/api/v1/transactions?${searchParams.toString()}`);
};

export const createTransaction = async (data: Record<string, unknown>) =>
  api.post('/api/v1/transactions', data);

export const uploadCsv = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/api/v1/imports/upload', formData);
};

export const commitImport = async (batchId: string, columnMapping: Record<string, string>) =>
  api.post(`/api/v1/imports/${batchId}/commit`, {
    batch_id: batchId,
    column_mapping: columnMapping,
  });
