import { useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'

import type { LoginPayload } from '../types/api'

type LoginFormProps = {
  loading: boolean
  error: string | null
  onSubmit: (credentials: LoginPayload) => Promise<boolean>
  onInputChange?: () => void
}

const TEXT = {
  title: '\u7CFB\u7EDF\u767B\u5F55',
  subtitle: '\u8BF7\u8F93\u5165\u8D26\u53F7\u5BC6\u7801\u4EE5\u8BBF\u95EE\u65E5\u5FD7\u548C\u5347\u7EA7\u529F\u80FD',
  username: '\u7528\u6237\u540D',
  password: '\u5BC6\u7801',
  submit: '\u767B\u5F55',
  submitting: '\u767B\u5F55\u4E2D...'
} as const

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
      <h1 className="title">{TEXT.title}</h1>
      <p className="subtitle">{TEXT.subtitle}</p>
      <form className="form" onSubmit={handleSubmit}>
        <label className="form-group">
          <span>{TEXT.username}</span>
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
          <span>{TEXT.password}</span>
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
          {loading ? TEXT.submitting : TEXT.submit}
        </button>
      </form>
    </main>
  )
}
