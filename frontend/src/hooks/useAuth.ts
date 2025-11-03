import { useCallback, useEffect, useMemo, useState } from 'react'

import { getProfile, login as loginRequest } from '../services/api'
import type { LoginPayload, UserProfile } from '../types/api'

const STORAGE_KEY = 'authToken'

export const useAuth = () => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY))
  const [user, setUser] = useState<UserProfile | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!token) {
      setUser(null)
      return
    }

    const controller = new AbortController()
    const loadProfile = async () => {
      try {
        const profile = await getProfile(token, controller.signal)
        setUser(profile)
      } catch {
        setToken(null)
        localStorage.removeItem(STORAGE_KEY)
        setUser(null)
      }
    }

    loadProfile()
    return () => controller.abort()
  }, [token])

  const login = useCallback(async (credentials: LoginPayload) => {
    setLoading(true)
    setError(null)

    try {
      const response = await loginRequest(credentials)
      localStorage.setItem(STORAGE_KEY, response.token)
      setToken(response.token)
      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : '????????'
      setError(message)
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setToken(null)
    setUser(null)
  }, [])

  const clearError = useCallback(() => setError(null), [])

  const isAuthenticated = useMemo(() => Boolean(token), [token])

  return {
    token,
    user,
    isAuthenticated,
    login,
    logout,
    loading,
    error,
    clearError,
  }
}
