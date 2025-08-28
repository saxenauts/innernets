export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

const BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_KEY = 'in_test_bearer';

function authHeader() {
  const raw = localStorage.getItem(TOKEN_KEY);
  if (!raw) return {} as Record<string, string>;
  try {
    const token = JSON.parse(raw).token as string;
    if (token) return { Authorization: `Bearer ${token}` };
  } catch {}
  return {} as Record<string, string>;
}

async function request<T>(method: HttpMethod, path: string, body?: any): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...authHeader(),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: any) => request<T>('POST', path, body),
  put: <T>(path: string, body?: any) => request<T>('PUT', path, body),
};

export function setDevToken(token: string) {
  localStorage.setItem(TOKEN_KEY, JSON.stringify({ token }));
}

export function clearDevToken() {
  localStorage.removeItem(TOKEN_KEY);
}

