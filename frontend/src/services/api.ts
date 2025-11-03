import type {
  LogDescriptor,
  LoginPayload,
  LoginResponse,
  UpgradeResponse,
  UserProfile,
} from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080/api'

const AUTH_HEADER = 'Authorization'

const createAuthHeader = (token: string) => ({
  [AUTH_HEADER]: `Bearer ${token}`,
})

const extractError = async (response: Response) => {
  try {
    const data = await response.json()
    if (data && typeof data === 'object' && 'error' in data && typeof data.error === 'string') {
      return data.error
    }
  } catch {
    try {
      const text = await response.text()
      if (text) {
        return text
      }
    } catch {
      /* noop */
    }
  }
  return response.statusText || 'Request failed'
}

export const login = async (payload: LoginPayload): Promise<LoginResponse> => {
  const response = await fetch(`${API_BASE_URL}/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(await extractError(response))
  }

  return (await response.json()) as LoginResponse
}

export const getProfile = async (token: string, signal?: AbortSignal): Promise<UserProfile> => {
  const response = await fetch(`${API_BASE_URL}/me`, {
    method: 'GET',
    headers: createAuthHeader(token),
    signal,
  })

  if (!response.ok) {
    throw new Error(await extractError(response))
  }

  return (await response.json()) as UserProfile
}

export const listLogs = async (token: string, signal?: AbortSignal): Promise<LogDescriptor[]> => {
  const response = await fetch(`${API_BASE_URL}/logs`, {
    method: 'GET',
    headers: createAuthHeader(token),
    signal,
  })

  if (!response.ok) {
    throw new Error(await extractError(response))
  }

  return (await response.json()) as LogDescriptor[]
}

export const downloadLog = async (token: string, name: string): Promise<Blob> => {
  const response = await fetch(`${API_BASE_URL}/logs/${encodeURIComponent(name)}`, {
    method: 'GET',
    headers: createAuthHeader(token),
  })

  if (!response.ok) {
    throw new Error(await extractError(response))
  }

  return await response.blob()
}

export const uploadUpgrade = async (token: string, file: File): Promise<UpgradeResponse> => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/upgrade`, {
    method: 'POST',
    headers: createAuthHeader(token),
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await extractError(response))
  }

  return (await response.json()) as UpgradeResponse
}
