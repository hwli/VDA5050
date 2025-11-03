import type { ReactNode } from 'react'

type DashboardProps = {
  username?: string
  onLogout: () => void
  children: ReactNode
}

export const Dashboard = ({ username, onLogout, children }: DashboardProps) => (
  <main className="card">
    <header className="header">
      <div>
        <h1 className="title">?????</h1>
        <p className="subtitle">?????{username ?? '??'}</p>
      </div>
      <button className="secondary-button" onClick={onLogout}>
        ????
      </button>
    </header>
    {children}
  </main>
)
