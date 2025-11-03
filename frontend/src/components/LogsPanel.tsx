import type { LogDescriptor } from '../types/api'
import { LogsTable } from './LogsTable'

type LogsPanelProps = {
  logs: LogDescriptor[]
  loading: boolean
  error: string | null
  onRefresh: () => void
  onDownload: (log: LogDescriptor) => void
}

const TEXT = {
  title: '\u65E5\u5FD7\u5217\u8868',
  subtitle: '\u67E5\u770B\u5E76\u4E0B\u8F7D\u7CFB\u7EDF\u8FD0\u884C\u65E5\u5FD7',
  refresh: '\u5237\u65B0',
  refreshing: '\u5237\u65B0\u4E2D...'
} as const

export const LogsPanel = ({ logs, loading, error, onRefresh, onDownload }: LogsPanelProps) => (
  <section className="section">
    <div className="section-header">
      <div>
        <h2>{TEXT.title}</h2>
        <p>{TEXT.subtitle}</p>
      </div>
      <button className="secondary-button" onClick={onRefresh} disabled={loading}>
        {loading ? TEXT.refreshing : TEXT.refresh}
      </button>
    </div>
    {error && <p className="error">{error}</p>}
    <LogsTable logs={logs} loading={loading} onDownload={onDownload} />
  </section>
)
