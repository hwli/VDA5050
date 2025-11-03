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
        setError('\u4F1A\u8BDD\u5DF2\u5931\u6548\uFF0C\u8BF7\u91CD\u65B0\u767B\u5F55')
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
        const message = err instanceof Error ? err.message : '\u5347\u7EA7\u5931\u8D25\uFF0C\u8BF7\u7A0D\u540E\u91CD\u8BD5'
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
