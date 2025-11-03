import { useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'

type UpgradePanelProps = {
  loading: boolean
  status: string | null
  error: string | null
  onSubmit: (file: File) => Promise<boolean>
  onResetFeedback?: () => void
}

const TEXT = {
  title: '\u7CFB\u7EDF\u5347\u7EA7',
  subtitle: '\u4E0A\u4F20\u5347\u7EA7\u5305\uFF0C\u63D0\u4EA4\u540E\u5C06\u8FDB\u5165\u5347\u7EA7\u6D41\u7A0B',
  fileLabel: '\u9009\u62E9\u5347\u7EA7\u6587\u4EF6',
  submit: '\u5F00\u59CB\u5347\u7EA7',
  submitting: '\u4E0A\u4F20\u4E2D...'
} as const

export const UpgradePanel = ({ loading, status, error, onSubmit, onResetFeedback }: UpgradePanelProps) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [localError, setLocalError] = useState<string | null>(null)
  const formRef = useRef<HTMLFormElement | null>(null)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!selectedFile) {
      setLocalError('\u8BF7\u9009\u62E9\u5347\u7EA7\u6587\u4EF6')
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
          <h2>{TEXT.title}</h2>
          <p>{TEXT.subtitle}</p>
        </div>
      </div>
      <form className="form" onSubmit={handleSubmit} ref={formRef}>
        <label className="form-group">
          <span>{TEXT.fileLabel}</span>
          <input className="input" type="file" onChange={handleChange} />
        </label>
        {status && <p className="success">{status}</p>}
        {(error || localError) && <p className="error">{error ?? localError}</p>}
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? TEXT.submitting : TEXT.submit}
        </button>
      </form>
    </section>
  )
}
