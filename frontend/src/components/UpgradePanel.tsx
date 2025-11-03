import { useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'

type UpgradePanelProps = {
  loading: boolean
  status: string | null
  error: string | null
  onSubmit: (file: File) => Promise<boolean>
  onResetFeedback?: () => void
}

export const UpgradePanel = ({ loading, status, error, onSubmit, onResetFeedback }: UpgradePanelProps) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [localError, setLocalError] = useState<string | null>(null)
  const formRef = useRef<HTMLFormElement | null>(null)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!selectedFile) {
      setLocalError('???????')
      return
    }

    setLocalError(null)
    const success = await onSubmit(selectedFile)
    if (success) {
      setSelectedFile(null)
      formRef.current?.reset()
    }
  }

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    setLocalError(null)
    if (onResetFeedback) {
      onResetFeedback()
    }
  }

  return (
    <section className="section">
      <div className="section-header">
        <div>
          <h2>????</h2>
          <p>????????????????</p>
        </div>
      </div>
      <form className="form" onSubmit={handleSubmit} ref={formRef}>
        <label className="form-group">
          <span>??????</span>
          <input className="input" type="file" onChange={handleChange} />
        </label>
        {status && <p className="success">{status}</p>}
        {(error || localError) && <p className="error">{error ?? localError}</p>}
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? '???...' : '????'}
        </button>
      </form>
    </section>
  )
}
