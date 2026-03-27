const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

// Structured API error for consistent error handling
export class ApiError extends Error {
  constructor(
    public status: number,
    public data: unknown
  ) {
    super(`Request failed with status ${status}`)
    this.name = 'ApiError'
  }
}

// Centralized API fetch wrapper with JWT auth injection
export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: HeadersInit = { ...options.headers }

  // Always request JSON from DRF
  ;(headers as Record<string, string>)['Accept'] = 'application/json'

  // Set Content-Type for non-FormData requests
  if (!(options.body instanceof FormData)) {
    ;(headers as Record<string, string>)['Content-Type'] = 'application/json'
  }

  const { getAccessToken } = await import('./auth')
  const token = getAccessToken()
  if (token) {
    ;(headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new ApiError(response.status, data)
  }

  // Handle 204 No Content (common for DELETE operations)
  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

// API helper methods
export const api = {
  get: <T>(endpoint: string) => apiFetch<T>(endpoint),
  post: <T>(endpoint: string, data: unknown) =>
    apiFetch<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  put: <T>(endpoint: string, data: unknown) =>
    apiFetch<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  patch: <T>(endpoint: string, data: unknown) =>
    apiFetch<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  delete: <T>(endpoint: string) =>
    apiFetch<T>(endpoint, { method: 'DELETE' }),
}

// Health check endpoint
export function fetchHealth() {
  return api.get<{ status: string; message: string; oauth_enabled: boolean }>('/health/')
}
