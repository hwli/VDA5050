import type { ReactNode } from 'react'

type DashboardProps = {
  username?: string
  onLogout: () => void
  children: ReactNode
}

const TEXT = {
  title: '\u8FD0\u7EF4\u63A7\u5236\u53F0',
  welcome: '\u6B22\u8FCE\u56DE\u6765\uFF0C',
  fallbackUser: '\u7528\u6237',
  logout: '\u9000\u51FA\u767B\u5F55'
} as const

export const Dashboard = ({ username, onLogout, children }: DashboardProps) => (
  <main className="card">
    <header className="header">
      <div>
        <h1 className="title">{TEXT.title}</h1>
        <p className="subtitle">
          {TEXT.welcome}
          {username ?? TEXT.fallbackUser}
        </p>
      </div>
      <button className="secondary-button" onClick={onLogout}>
        {TEXT.logout}
      </button>
    </header>
    {children}
  </main>
)
