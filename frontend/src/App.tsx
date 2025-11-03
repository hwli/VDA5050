import './App.css'

import { Dashboard } from './components/Dashboard'
import { LoginForm } from './components/LoginForm'
import { LogsPanel } from './components/LogsPanel'
import { UpgradePanel } from './components/UpgradePanel'
import { useAuth } from './hooks/useAuth'
import { useLogs } from './hooks/useLogs'
import { useUpgrade } from './hooks/useUpgrade'

const App = () => {
  const {
    token,
    user,
    isAuthenticated,
    login,
    logout,
    loading: authLoading,
    error: authError,
    clearError: clearAuthError,
  } = useAuth()

  const {
    items: logs,
    loading: logsLoading,
    error: logsError,
    refresh: refreshLogs,
    download: downloadLog,
    clearError: clearLogsError,
  } = useLogs(token)

  const {
    status: upgradeStatus,
    error: upgradeError,
    loading: upgradeLoading,
    upload: uploadUpgrade,
    clearStatus: clearUpgradeStatus,
  } = useUpgrade(token)

  if (!isAuthenticated) {
    return (
      <div className="app">
        <LoginForm
          loading={authLoading}
          error={authError}
          onSubmit={login}
          onInputChange={clearAuthError}
        />
      </div>
    )
  }

  return (
    <div className="app">
      <Dashboard username={user?.username} onLogout={logout}>
        <LogsPanel
          logs={logs}
          loading={logsLoading}
          error={logsError}
          onRefresh={() => {
            clearLogsError()
            void refreshLogs()
          }}
          onDownload={(log) => {
            clearLogsError()
            void downloadLog(log)
          }}
        />
        <UpgradePanel
          loading={upgradeLoading}
          status={upgradeStatus}
          error={upgradeError}
          onSubmit={uploadUpgrade}
          onResetFeedback={clearUpgradeStatus}
        />
      </Dashboard>
    </div>
  )
}

export default App
