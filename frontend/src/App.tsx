import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type LogDescriptor = {
  name: string
  size: number
  modifiedAt: string
}

type LoginPayload = {
  username: string
  password: string
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080/api'

const formatBytes = (bytes: number) => {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / Math.pow(1024, i)
  return `${value.toFixed(value >= 10 || i === 0 ? 0 : 1)} ${units[i]}`
}

function App() {
  const [credentials, setCredentials] = useState<LoginPayload>({ username: '', password: '' })
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('authToken'))
  const [username, setUsername] = useState<string | null>(null)
  const [authError, setAuthError] = useState<string | null>(null)
  const [isAuthenticating, setIsAuthenticating] = useState(false)

  const [logs, setLogs] = useState<LogDescriptor[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [logsError, setLogsError] = useState<string | null>(null)

  const [upgradeFile, setUpgradeFile] = useState<File | null>(null)
  const [upgradeStatus, setUpgradeStatus] = useState<string | null>(null)
  const [upgradeError, setUpgradeError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  const isAuthenticated = useMemo(() => Boolean(token), [token])

  useEffect(() => {
    if (!token) {
      setUsername(null)
      return
    }

    const controller = new AbortController()
    const loadProfile = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/me`, {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${token}`,
          },
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error('???????????')
        }

        const data = (await response.json()) as { username: string }
        setUsername(data.username)
      } catch (error) {
        if ((error as Error).name === 'AbortError') return
        setToken(null)
        localStorage.removeItem('authToken')
      }
    }

    loadProfile()
    return () => controller.abort()
  }, [token])

  const loadLogs = useCallback(async () => {
    if (!token) return
    setLogsLoading(true)
    setLogsError(null)
    try {
      const response = await fetch(`${API_BASE_URL}/logs`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error('????????')
      }

      const data = (await response.json()) as LogDescriptor[]
      setLogs(data)
    } catch (error) {
      setLogs([])
      setLogsError((error as Error).message)
    } finally {
      setLogsLoading(false)
    }
  }, [token])

  useEffect(() => {
    if (token) {
      loadLogs()
    }
  }, [token, loadLogs])

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setAuthError(null)
    setIsAuthenticating(true)

    try {
      const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      })

      if (!response.ok) {
        throw new Error('????????')
      }

      const data = (await response.json()) as { token: string }
      setToken(data.token)
      localStorage.setItem('authToken', data.token)
      setCredentials({ username: '', password: '' })
    } catch (error) {
      setAuthError((error as Error).message)
    } finally {
      setIsAuthenticating(false)
    }
  }

  const handleDownload = async (log: LogDescriptor) => {
    if (!token) return
    try {
      const response = await fetch(`${API_BASE_URL}/logs/${encodeURIComponent(log.name)}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error('??????')
      }

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = log.name
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (error) {
      setLogsError((error as Error).message)
    }
  }

  const handleUpgradeSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setUpgradeStatus(null)
    setUpgradeError(null)

    if (!token || !upgradeFile) {
      setUpgradeError('???????')
      return
    }

    const formData = new FormData()
    formData.append('file', upgradeFile)

    setIsUploading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/upgrade`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      })

      if (!response.ok) {
        throw new Error('??????????')
      }

      const data = (await response.json()) as { message: string; filename: string }
      setUpgradeStatus(`${data.message}?${data.filename}`)
      setUpgradeFile(null)
      ;(event.target as HTMLFormElement).reset()
    } catch (error) {
      setUpgradeError((error as Error).message)
    } finally {
      setIsUploading(false)
    }
  }

  const handleLogout = () => {
    setToken(null)
    setUsername(null)
    localStorage.removeItem('authToken')
  }

  if (!isAuthenticated) {
    return (
      <div className="app">
        <main className="card">
          <h1 className="title">????</h1>
          <p className="subtitle">?????????????????</p>
          <form className="form" onSubmit={handleLogin}>
            <label className="form-group">
              <span>???</span>
              <input
                className="input"
                placeholder="admin"
                value={credentials.username}
                onChange={(event) =>
                  setCredentials((current) => ({ ...current, username: event.target.value }))
                }
                required
                autoFocus
              />
            </label>
            <label className="form-group">
              <span>??</span>
              <input
                className="input"
                type="password"
                placeholder="password123"
                value={credentials.password}
                onChange={(event) =>
                  setCredentials((current) => ({ ...current, password: event.target.value }))
                }
                required
              />
            </label>
            {authError && <p className="error">{authError}</p>}
            <button className="primary-button" type="submit" disabled={isAuthenticating}>
              {isAuthenticating ? '???...' : '??'}
            </button>
          </form>
        </main>
      </div>
    )
  }

  return (
    <div className="app">
      <main className="card">
        <header className="header">
          <div>
            <h1 className="title">?????</h1>
            <p className="subtitle">?????{username ?? '??'}</p>
          </div>
          <button className="secondary-button" onClick={handleLogout}>
            ????
          </button>
        </header>

        <section className="section">
          <div className="section-header">
            <div>
              <h2>????</h2>
              <p>???????????</p>
            </div>
            <button className="secondary-button" onClick={loadLogs} disabled={logsLoading}>
              {logsLoading ? '???...' : '??'}
            </button>
          </div>
          {logsError && <p className="error">{logsError}</p>}
          <div className="logs-table" role="table">
            <div className="logs-header" role="row">
              <span role="columnheader">???</span>
              <span role="columnheader">??</span>
              <span role="columnheader">????</span>
              <span role="columnheader" className="actions-column">
                ??
              </span>
            </div>
            {logs.length === 0 && !logsLoading ? (
              <div className="logs-row empty" role="row">
                <span role="cell">????</span>
              </div>
            ) : (
              logs.map((log) => (
                <div className="logs-row" role="row" key={log.name}>
                  <span role="cell" className="filename">
                    {log.name}
                  </span>
                  <span role="cell">{formatBytes(log.size)}</span>
                  <span role="cell">{new Date(log.modifiedAt).toLocaleString()}</span>
                  <span role="cell" className="actions-column">
                    <button className="primary-button" onClick={() => handleDownload(log)}>
                      ??
                    </button>
                  </span>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="section">
          <div className="section-header">
            <div>
              <h2>????</h2>
              <p>????????????????</p>
            </div>
          </div>
          <form className="form" onSubmit={handleUpgradeSubmit}>
            <label className="form-group">
              <span>??????</span>
              <input
                className="input"
                type="file"
                onChange={(event) => setUpgradeFile(event.target.files?.[0] ?? null)}
              />
            </label>
            {upgradeStatus && <p className="success">{upgradeStatus}</p>}
            {upgradeError && <p className="error">{upgradeError}</p>}
            <button className="primary-button" type="submit" disabled={isUploading}>
              {isUploading ? '???...' : '????'}
            </button>
          </form>
        </section>
      </main>
    </div>
  )
}

export default App
