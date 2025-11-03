import type { LogDescriptor } from '../types/api'
import { formatBytes } from '../utils/format'

type LogsTableProps = {
  logs: LogDescriptor[]
  loading: boolean
  onDownload: (log: LogDescriptor) => void
}

const TEXT = {
  name: '\u6587\u4EF6\u540D',
  size: '\u5927\u5C0F',
  updatedAt: '\u66F4\u65B0\u65F6\u95F4',
  action: '\u64CD\u4F5C',
  empty: '\u6682\u65E0\u65E5\u5FD7',
  download: '\u4E0B\u8F7D'
} as const

export const LogsTable = ({ logs, loading, onDownload }: LogsTableProps) => (
  <div className="logs-table" role="table">
    <div className="logs-header" role="row">
      <span role="columnheader">{TEXT.name}</span>
      <span role="columnheader">{TEXT.size}</span>
      <span role="columnheader">{TEXT.updatedAt}</span>
      <span role="columnheader" className="actions-column">
        {TEXT.action}
      </span>
    </div>
    {logs.length === 0 && !loading ? (
      <div className="logs-row empty" role="row">
        <span role="cell">{TEXT.empty}</span>
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
              {TEXT.download}
            </button>
          </span>
        </div>
      ))
    )}
  </div>
)
