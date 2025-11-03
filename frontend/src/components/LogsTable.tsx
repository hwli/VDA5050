import type { LogDescriptor } from '../types/api'
import { formatBytes } from '../utils/format'

type LogsTableProps = {
  logs: LogDescriptor[]
  loading: boolean
  onDownload: (log: LogDescriptor) => void
}

export const LogsTable = ({ logs, loading, onDownload }: LogsTableProps) => (
  <div className="logs-table" role="table">
    <div className="logs-header" role="row">
      <span role="columnheader">???</span>
      <span role="columnheader">??</span>
      <span role="columnheader">????</span>
      <span role="columnheader" className="actions-column">
        ??
      </span>
    </div>
    {logs.length === 0 && !loading ? (
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
            <button className="primary-button" onClick={() => onDownload(log)}>
              ??
            </button>
          </span>
        </div>
      ))
    )}
  </div>
)
