import { useCallback, useEffect, useState } from 'react'

import { downloadLog, listLogs } from '../services/api'
import type { LogDescriptor } from '../types/api'

const triggerBrowserDownload = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export const useLogs = (token: string | null) => {
  const [items, setItems] = useState<LogDescriptor[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!token) {
      setItems([])
      return
    }

    setLoading(true)
    setError(null)
    try {
      const logs = await listLogs(token)
      setItems(logs)
    } catch (err) {
      setItems([])
      const message = err instanceof Error ? err.message : '????????'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    if (!token) {
      setItems([])
      return
    }
    refresh()
  }, [token, refresh])

  const download = useCallback(
    async (log: LogDescriptor) => {
      if (!token) {
        return
      }
      try {
        const blob = await downloadLog(token, log.name)
        triggerBrowserDownload(blob, log.name)
      } catch (err) {
        const message = err instanceof Error ? err.message : '??????'
        setError(message)
      }
    },
    [token],
  )

  const clearError = useCallback(() => setError(null), [])

  return {
    items,
    loading,
    error,
    refresh,
    download,
    clearError,
  }
}
