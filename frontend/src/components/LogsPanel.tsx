import type { LogDescriptor } from '../types/api'
import { LogsTable } from './LogsTable'

type LogsPanelProps = {
  logs: LogDescriptor[]
  loading: boolean
  error: string | null
  onRefresh: () => void
  onDownload: (log: LogDescriptor) => void
}

export const LogsPanel = ({ logs, loading, error, onRefresh, onDownload }: LogsPanelProps) => (
  <section className="section">
    <div className="section-header">
      <div>
        <h2>????</h2>
        <p>???????????</p>
      </div>
      <button className="secondary-button" onClick={onRefresh} disabled={loading}>
        {loading ? '???...' : '??'}
      </button>
    </div>
    {error && <p className="error">{error}</p>}
    <LogsTable logs={logs} loading={loading} onDownload={onDownload} />
  </section>
)
