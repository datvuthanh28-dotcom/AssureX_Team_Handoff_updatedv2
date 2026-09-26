import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import CustomerApp from './CustomerApp.jsx'
import { api } from './api.js'

const ADMIN_SESSION_KEY = 'assurex_admin_token'
const APP_BASE_PATH = import.meta.env.BASE_URL.replace(/\/$/, '')

function AdminLogin({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const session = await api('/api/auth/workspace/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      onLogin(session)
    } catch (requestError) {
      setError(requestError.message || 'Sign in failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="admin-auth-screen">
      <section className="admin-auth-panel">
        <div className="admin-auth-brand">
          <span className="brand-mark">AX</span>
          <div>
            <strong>AssureX</strong>
            <span>Warranty operations</span>
          </div>
        </div>
        <p className="eyebrow">STAFF WORKSPACE</p>
        <h1>Sign in to your workspace</h1>
        <p className="admin-auth-copy">
          Access the tools assigned to your role.
        </p>
        <form className="admin-auth-form" onSubmit={submit}>
          <label>
            Username
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => {
                setUsername(event.target.value)
                setError('')
              }}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value)
                setError('')
              }}
              required
            />
          </label>
          {error && <p className="admin-auth-error" role="alert">{error}</p>}
          <button className="button primary" type="submit" disabled={busy}>
            {busy ? 'Signing in...' : 'Continue to admin'}
          </button>
        </form>
        <a className="admin-auth-back" href={APP_BASE_PATH || '/'}>Return to customer portal</a>
      </section>
      <aside className="admin-auth-aside">
        <p>ASSUREX / CLAIM OPERATIONS</p>
        <h2>Every claim, reviewed with clarity.</h2>
        <span>One workspace for service teams to assess warranty requests and follow decisions.</span>
      </aside>
    </main>
  )
}

function RootComponent() {
  const currentPath = window.location.pathname.replace(/\/+$/, '') || '/'
  const path = currentPath.startsWith(APP_BASE_PATH)
    ? currentPath.slice(APP_BASE_PATH.length) || '/'
    : currentPath
  const isAdminRoute = path === '/admin' || path.endsWith('/admin')
  const [adminAuthenticated, setAdminAuthenticated] = useState(
    () => Boolean(localStorage.getItem(ADMIN_SESSION_KEY))
  )
  const [adminRole, setAdminRole] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [checkingAdmin, setCheckingAdmin] = useState(isAdminRoute && adminAuthenticated)

  useEffect(() => {
    if (!isAdminRoute || !adminAuthenticated) {
      return undefined
    }

    let active = true
    api('/api/auth/me')
      .then((account) => {
        if (!['ADMIN', 'REVIEWER', 'SERVICE_CENTER'].includes(account.role)) {
          throw new Error('Workspace access required.')
        }
        if (active) setAdminRole(account.role)
        if (active) setAdminEmail(account.email)
      })
      .catch(() => {
        localStorage.removeItem(ADMIN_SESSION_KEY)
        if (active) setAdminAuthenticated(false)
      })
      .finally(() => {
        if (active) setCheckingAdmin(false)
      })

    return () => {
      active = false
    }
  }, [isAdminRoute, adminAuthenticated])

  if (!isAdminRoute) return <CustomerApp />
  if (checkingAdmin) {
    return <main className="admin-auth-screen"><p>Checking access...</p></main>
  }
  if (!adminAuthenticated) {
    return (
      <AdminLogin
        onLogin={(session) => {
          localStorage.setItem(ADMIN_SESSION_KEY, session.access_token)
          setAdminRole(session.role)
          setAdminEmail(session.email)
          setAdminAuthenticated(true)
        }}
      />
    )
  }

  return (
    <App
    role={adminRole}
    email={adminEmail}
      onLogout={async () => {
        try {
          await api('/api/auth/logout', { method: 'POST' })
        } catch {
          // Clear local state even if the API is unavailable.
        }
        localStorage.removeItem(ADMIN_SESSION_KEY)
        setAdminRole('')
        setAdminEmail('')
        setAdminAuthenticated(false)
      }}
    />
  )
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RootComponent />
  </StrictMode>,
)
