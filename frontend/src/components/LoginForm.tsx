import { useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'

import type { LoginPayload } from '../types/api'

type LoginFormProps = {
  loading: boolean
  error: string | null
  onSubmit: (credentials: LoginPayload) => Promise<boolean>
  onInputChange?: () => void
}

export const LoginForm = ({ loading, error, onSubmit, onInputChange }: LoginFormProps) => {
  const [credentials, setCredentials] = useState<LoginPayload>({ username: '', password: '' })

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const success = await onSubmit(credentials)
    if (success) {
      setCredentials({ username: '', password: '' })
    }
  }

  const handleChange = (field: keyof LoginPayload) => (event: ChangeEvent<HTMLInputElement>) => {
    if (onInputChange) {
      onInputChange()
    }
    setCredentials((current) => ({ ...current, [field]: event.target.value }))
  }

  return (
    <main className="card">
      <h1 className="title">????</h1>
      <p className="subtitle">?????????????????</p>
      <form className="form" onSubmit={handleSubmit}>
        <label className="form-group">
          <span>???</span>
          <input
            className="input"
            placeholder="admin"
            value={credentials.username}
            onChange={handleChange('username')}
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
            onChange={handleChange('password')}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? '???...' : '??'}
        </button>
      </form>
    </main>
  )
}
