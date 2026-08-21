/* eslint-disable @typescript-eslint/no-explicit-any */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  // Try to retrieve token from localStorage if running in browser
  let token = '';
  if (typeof window !== 'undefined') {
    token = localStorage.getItem('access_token') || '';
  }

  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errData;
    try {
      errData = await response.json();
    } catch {
      errData = await response.text();
    }
    if (response.status === 401 && typeof window !== 'undefined' && !window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    const message = errData?.error?.message || errData?.message || 'An error occurred';
    throw new ApiError(response.status, message, errData);
  }

  // Handle 204 No Content
  if (response.status === 204) return null;

  if (options.headers && (options.headers as any)['Accept'] === 'text/event-stream') {
    return response;
  }

  return response.json();
}

export const api = {
  get: (endpoint: string, options?: RequestInit) => fetchWithAuth(endpoint, { ...options, method: 'GET' }),
  post: (endpoint: string, data?: any, options?: RequestInit) => fetchWithAuth(endpoint, {
    ...options,
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  }),
  put: (endpoint: string, data?: any, options?: RequestInit) => fetchWithAuth(endpoint, {
    ...options,
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  }),
  delete: (endpoint: string, options?: RequestInit) => fetchWithAuth(endpoint, { ...options, method: 'DELETE' }),
  patch: (endpoint: string, data?: any, options?: RequestInit) => fetchWithAuth(endpoint, {
    ...options,
    method: 'PATCH',
    body: data ? JSON.stringify(data) : undefined,
  }),
};

// Typed endpoints
export const auth = {
  login: (data: any) => api.post('/auth/login', data),
  register: (data: any) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
};

export const workspaces = {
  list: () => api.get('/workspaces'),
  getMembers: (workspaceId: string) => api.get(`/workspaces/${workspaceId}/members`),
  updateMemberRole: (workspaceId: string, userId: string, role: string) => api.patch(`/workspaces/${workspaceId}/members/${userId}`, { role }),
  removeMember: (workspaceId: string, userId: string) => api.delete(`/workspaces/${workspaceId}/members/${userId}`),
  updateSettings: (workspaceId: string, data: any) => api.put(`/workspaces/${workspaceId}/settings`, data),
};

export const chat = {
  completions: (data: any) => api.post('/chat', data),
};

export const documents = {
  list: (workspaceId: string) => api.get(`/workspaces/${workspaceId}/documents`),
  upload: (workspaceId: string, data: FormData) => fetchWithAuth(`/workspaces/${workspaceId}/documents/upload`, { method: 'POST', body: data }),
};

export const conversations = {
  list: (workspaceId: string) => api.get(`/workspaces/${workspaceId}/conversations`),
  get: (conversationId: string) => api.get(`/conversations/${conversationId}`),
  create: (workspaceId: string, data: any) => api.post(`/workspaces/${workspaceId}/conversations`, data),
  getMessages: (conversationId: string) => api.get(`/conversations/${conversationId}/messages`),
  sendMessage: (conversationId: string, data: any) => api.post(`/conversations/${conversationId}/messages`, data, { headers: { 'Accept': 'text/event-stream' } }),
};

export const agents = {
  list: () => api.get('/agents'),
};

export const settings = {
  get: () => api.get('/settings'),
  update: (data: any) => api.put('/settings', data),
};

export const analytics = {
  overview: (workspaceId: string) => api.get(`/workspaces/${workspaceId}/analytics/overview`),
  activity: (workspaceId: string) => api.get(`/workspaces/${workspaceId}/analytics/activity`),
};

export const apiKeys = {
  list: (workspaceId: string) => api.get(`/workspaces/${workspaceId}/api-keys`),
  create: (workspaceId: string, data: any) => api.post(`/workspaces/${workspaceId}/api-keys`, data),
  revoke: (workspaceId: string, keyId: string) => api.delete(`/workspaces/${workspaceId}/api-keys/${keyId}`),
};

export const audit = {
  list: (workspaceId: string) => api.get(`/workspaces/${workspaceId}/audit-logs`),
};

export const system = {
  health: () => fetch(`${API_BASE_URL}/health`).then(res => res.json()),
};
