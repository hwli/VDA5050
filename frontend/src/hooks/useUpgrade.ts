import { useCallback, useEffect, useState } from 'react'

import { uploadUpgrade } from '../services/api'

export const useUpgrade = (token: string | null) => {
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!token) {
      setStatus(null)
      setError(null)
      setLoading(false)
    }
  }, [token])

  const upload = useCallback(
    async (file: File) => {
      if (!token) {
        setError('???????????')
        return false
      }

      setLoading(true)
      setStatus(null)
      setError(null)

      try {
        const response = await uploadUpgrade(token, file)
        setStatus(`${response.message}?${response.filename}`)
        return true
      } catch (err) {
        const message = err instanceof Error ? err.message : '??????????'
        setError(message)
        return false
      } finally {
        setLoading(false)
      }
    },
    [token],
  )

  const clearStatus = useCallback(() => {
    setStatus(null)
    setError(null)
  }, [])

  return {
    status,
    error,
    loading,
    upload,
    clearStatus,
  }
}
