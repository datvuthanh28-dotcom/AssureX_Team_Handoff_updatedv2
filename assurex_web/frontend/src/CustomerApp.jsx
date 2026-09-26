import { useEffect, useState } from 'react'
import './CustomerApp.css'
import { api } from './api'
import {
  CustomerHome,
  CustomerSubmit,
  CustomerClaims,
} from './App'

const SESSION_KEY = 'assurex_customer_session'
const TOKEN_KEY = 'assurex_customer_token'
const ADMIN_PATH = `${import.meta.env.BASE_URL}admin`

const customerNavigation = [
  ['home', 'Home', 'home'],
  ['submit', 'Submit Claim', 'submit'],
  ['my-claims', 'My Claims', 'claims'],
  ['products', 'My Products', 'products'],
  ['warranties', 'Warranties', 'warranties'],
  ['notifications', 'Notifications', 'notifications'],
  ['profile', 'Profile', 'profile'],
]

function loadSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY)

    if (raw) {
      const parsed = JSON.parse(raw)

      const token = localStorage.getItem(TOKEN_KEY)
      if (parsed?.email && token) {
        return { ...parsed, token }
      }
    }
  } catch {
    // ignore malformed session
  }

  return null
}

function NavIcon({ name }) {
  const paths = {
    home: 'M3 11.5 12 4l9 7.5M5 10v9h5v-5h4v5h5v-9',
    submit: 'M12 5v14M5 12h14',
    claims:
      'M7 3h7l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Zm7 0v4h4M9 12h6M9 16h6M9 8h2',
    notifications:
      'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4',
    products:
      'M4 7h16v13H4zM7 4h10v3H7zM8 11h8M8 15h5',
    warranties:
      'M12 3 19 6v5c0 5-3 8-7 10-4-2-7-5-7-10V6zm-3 9 2 2 4-4',
    profile:
      'M20 21a8 8 0 0 0-16 0M12 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8',
  }

  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="nav-icon"
    >
      <path d={paths[name]} />
    </svg>
  )
}


function CustomerNotifications() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/api/notifications')
      .then(setItems)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [])

  async function markRead(item) {
    try {
      await api(`/api/notifications/${item.id}/read`, { method: 'POST' })
      setItems((current) => current.map((entry) =>
        entry.id === item.id ? { ...entry, is_read: true } : entry
      ))
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Customer Portal</p>
          <h1>Notifications</h1>
          <p className="page-description">Claim receipts and status updates for your account.</p>
        </div>
      </header>
      {error && <div className="alert error">{error}</div>}
      <section className="panel">
        {loading ? <div className="state-card">Loading notifications...</div> : items.length === 0 ? (
          <div className="empty-state"><h3>No notifications</h3><p>Claim updates will appear here.</p></div>
        ) : (
          <div className="notification-list">
            {items.map((item) => (
              <article className={`notification-item ${item.is_read ? 'read' : 'unread'}`} key={item.id}>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.message}</p>
                  <small>{formatNotificationDate(item.created_at)}</small>
                </div>
                {!item.is_read && <button className="text-button" onClick={() => markRead(item)}>Mark read</button>}
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  )
}


function formatNotificationDate(value) {
  return value ? new Date(value).toLocaleString() : ''
}


function CustomerProducts() {
  const [catalog, setCatalog] = useState([])
  const [products, setProducts] = useState([])
  const [productId, setProductId] = useState('')
  const [serialNumber, setSerialNumber] = useState('')
  const [purchaseDate, setPurchaseDate] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function fetchProducts() {
    return Promise.all([
        api('/api/products'),
        api('/api/products/registered'),
      ])
  }

  useEffect(() => {
    let active = true
    fetchProducts()
      .then(([available, registered]) => {
        if (!active) return
        setCatalog(available)
        setProducts(registered)
      })
      .catch((requestError) => {
        if (active) setError(requestError.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  async function loadProducts() {
    try {
      const [available, registered] = await fetchProducts()
      setCatalog(available)
      setProducts(registered)
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  async function registerProduct(event) {
    event.preventDefault()
    setError('')
    try {
      await api('/api/products/register', {
        method: 'POST',
        body: JSON.stringify({
          product_id: Number(productId),
          serial_number: serialNumber,
          purchase_date: purchaseDate,
        }),
      })
      setProductId('')
      setSerialNumber('')
      setPurchaseDate('')
      await loadProducts()
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  return (
    <>
      <header className="page-header"><div><p className="eyebrow">Customer Portal</p><h1>My Products</h1><p className="page-description">Products registered to your account.</p></div></header>
      <form className="panel" onSubmit={registerProduct}>
        <div className="panel-heading"><h2>Register product</h2></div>
        <div className="form-grid">
          <label className="form-field"><span>Product</span><select value={productId} onChange={(event) => setProductId(event.target.value)} required><option value="">Select product</option>{catalog.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.model}</option>)}</select></label>
          <label className="form-field"><span>Serial number</span><input value={serialNumber} onChange={(event) => setSerialNumber(event.target.value)} required /></label>
          <label className="form-field"><span>Purchase date</span><input type="date" value={purchaseDate} onChange={(event) => setPurchaseDate(event.target.value)} required /></label>
        </div>
        {error && <div className="alert error">{error}</div>}
        <div className="form-actions"><button className="button primary">Register product</button></div>
      </form>
      <section className="panel">
        {loading ? <div className="state-card">Loading products...</div> : products.length === 0 ? <div className="empty-state"><h3>No registered products</h3><p>Register a product to see its warranty information here.</p></div> : (
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Product</th><th>Brand / Model</th><th>Serial</th><th>Purchase date</th><th>Warranty</th></tr></thead><tbody>
            {products.map((product) => <tr key={product.id}><td>{product.name}</td><td>{product.brand} · {product.model}</td><td>{product.serial_number}</td><td>{product.purchase_date}</td><td>{product.warranty?.status || '—'}{product.warranty ? ` · until ${product.warranty.end_date}` : ''}</td></tr>)}
          </tbody></table></div>
        )}
      </section>
    </>
  )
}


function CustomerWarranties() {
  const [warranties, setWarranties] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/api/warranties')
      .then(setWarranties)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <header className="page-header"><div><p className="eyebrow">Customer Portal</p><h1>Warranties</h1><p className="page-description">Coverage registered to your products.</p></div></header>
      <section className="panel">
        {error && <div className="alert error">{error}</div>}
        {loading ? <div className="state-card">Loading warranties...</div> : warranties.length === 0 ? <div className="empty-state"><h3>No warranties found</h3><p>Register a product to create its warranty record.</p></div> : (
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Product</th><th>Serial</th><th>Coverage</th><th>End date</th><th>Status</th></tr></thead><tbody>
            {warranties.map((warranty) => <tr key={warranty.id}><td>{warranty.product}</td><td>{warranty.serial_number}</td><td>{warranty.start_date} – {warranty.end_date}</td><td>{warranty.end_date}</td><td>{warranty.is_active ? warranty.status : 'Inactive'}</td></tr>)}
          </tbody></table></div>
        )}
      </section>
    </>
  )
}

function CustomerLogin({ mode, setMode, onLogin, onBack }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()

    const normalizedEmail = email.trim().toLowerCase()

    if (!normalizedEmail || !normalizedEmail.includes('@')) {
      setError('Enter a valid email address.')
      return
    }

    if (password.length < 8) {
      setError('Use a password with at least 8 characters.')
      return
    }

    setBusy(true)
    setError('')

    try {
      const result = await api(
        mode === 'signup' ? '/api/auth/register' : '/api/auth/login',
        {
          method: 'POST',
          body: JSON.stringify({ email: normalizedEmail, password }),
        }
      )
      onLogin(result)
    } catch (requestError) {
      setError(requestError.message || 'Unable to complete sign in. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-brand">
          <div className="brand-mark">AX</div>
          <div>
            <h2>AssureX</h2>
            <p>Warranty Claim Engine</p>
          </div>
        </div>

        <p className="eyebrow">CUSTOMER ACCOUNT</p>
        <h1>{mode === 'signup' ? 'Create your account' : 'Welcome back'}</h1>
        <p className="login-subtitle">
          {mode === 'signup'
            ? 'Create an account to keep your warranty claims together.'
            : 'Sign in to see and manage your warranty claims.'}
        </p>

        <form onSubmit={submit} className="login-form">
          <label>
            <span>Email</span>
            <input
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value)
                setError('')
              }}
              autoComplete="email"
              autoFocus
            />
          </label>

          <label>
            <span>Password</span>
            <input
              type="password"
              placeholder="At least 8 characters"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value)
                setError('')
              }}
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
              minLength={8}
            />
          </label>

          {error && (
            <p className="login-error">{error}</p>
          )}

          <button type="submit" className="button primary large" disabled={busy}>
            {busy ? 'Please wait...' : mode === 'signup' ? 'Create account' : 'Log in'}
          </button>
        </form>

        <button
          type="button"
          className="auth-mode-button"
          onClick={() => {
            setMode(mode === 'signup' ? 'login' : 'signup')
            setError('')
          }}
        >
          {mode === 'signup'
            ? 'Already registered? Log in'
            : 'New to AssureX? Create an account'}
        </button>
        <button type="button" className="auth-back-button" onClick={onBack}>
          Back to customer portal
        </button>
      </div>
      <aside className="login-aside">
        <p>ASSUREX CUSTOMER CARE</p>
        <h2>Your warranty, clearly handled.</h2>
        <span>Submit a request, keep your claim details close, and see each review update in one place.</span>
      </aside>
    </div>
  )
}

function CustomerApp() {
  const [session, setSession] = useState(
    () => loadSession()
  )

  const [customerPage, setCustomerPage] =
    useState('home')

  const [authMode, setAuthMode] = useState(null)

  const [refreshKey, setRefreshKey] = useState(0)
  const [guestEmail, setGuestEmail] = useState('')

  useEffect(() => {
    document.body.classList.add('customer-light')

    return () => {
      document.body.classList.remove(
        'customer-light'
      )
    }
  }, [])

  useEffect(() => {
    if (!session?.token) return undefined

    let active = true
    api('/api/auth/me')
      .then((account) => {
        if (active) {
          setSession({ ...account, token: session.token })
        }
      })
      .catch(() => {
        if (!active) return
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(SESSION_KEY)
        setSession(null)
      })

    return () => {
      active = false
    }
  }, [session?.token])

  function handleLogin(result) {
    const { email, access_token: token } = result
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({ email })
    )

    setSession({ email, token })
    setGuestEmail(email)
    setAuthMode(null)
    setCustomerPage('home')
  }

  async function handleLogout() {
    try {
      await api('/api/auth/logout', { method: 'POST' })
    } catch {
      // Clear the local session even when the API is unavailable.
    }

    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(SESSION_KEY)
    setSession(null)
    setGuestEmail('')
    setAuthMode(null)
    setCustomerPage('home')
  }

  function refresh() {
    setRefreshKey((value) => value + 1)
  }

  function navigateCustomer(page) {
    if (!session && page !== 'home') {
      setAuthMode('login')
      return
    }
    setCustomerPage(page)
  }

  if (authMode) {
    return (
      <CustomerLogin
        mode={authMode}
        setMode={setAuthMode}
        onLogin={handleLogin}
        onBack={() => setAuthMode(null)}
      />
    )
  }

  const initial = session?.email
    .charAt(0)
    .toUpperCase()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">AX</div>

          <div>
            <h2>AssureX</h2>
            <p>Claim Engine</p>
          </div>
        </div>

        <div className="sidebar-section-label">
          Customer Portal
        </div>

        <nav className="nav-menu">
          {customerNavigation.map(
            ([key, label, icon]) => (
              <button
                key={key}
                className={`nav-item ${
                  customerPage === key
                    ? 'active'
                    : ''
                }`}
                onClick={() => navigateCustomer(key)}
              >
                <NavIcon name={icon} />
                {label}
              </button>
            )
          )}
        </nav>

        {session ? (
          <>
            <div className="account-card">
              <div className="account-avatar">{initial}</div>
              <div className="account-details">
                <span>Signed in as</span>
                <strong>{session.email}</strong>
              </div>
            </div>
            <button className="logout-button" onClick={handleLogout}>
              Log out
            </button>
          </>
        ) : (
          <div className="guest-actions">
            <p>Have an account?</p>
            <button className="button primary" onClick={() => setAuthMode('login')}>
              Log in
            </button>
            <button className="logout-button" onClick={() => setAuthMode('signup')}>
              Create account
            </button>
            <a className="customer-admin-link" href={ADMIN_PATH}>
              Staff access
            </a>
          </div>
        )}
      </aside>

      <main className="main-content">
        {customerPage === 'home' && (
          <CustomerHome
            email={session?.email || guestEmail}
            setEmail={setGuestEmail}
            hideIdentity
            onNavigate={navigateCustomer}
            refreshKey={refreshKey}
          />
        )}

        {customerPage === 'submit' && (
          <CustomerSubmit
            email={session?.email || guestEmail}
            setEmail={setGuestEmail}
            onSubmitted={() => {
              refresh()
              navigateCustomer('my-claims')
            }}
            onNavigate={navigateCustomer}
          />
        )}

        {customerPage === 'my-claims' && (
          <CustomerClaims
            email={session?.email || guestEmail}
            setEmail={setGuestEmail}
            hideIdentity
            refreshKey={refreshKey}
          />
        )}

        {customerPage === 'notifications' && <CustomerNotifications />}

        {customerPage === 'products' && <CustomerProducts />}

        {customerPage === 'warranties' && <CustomerWarranties />}

        {customerPage === 'profile' && (
          <section className="panel profile-page">
            <p className="eyebrow">Customer account</p>
            <h1>Profile</h1>
            <div className="detail-grid">
              <div><span>Email</span><strong>{session?.email || '—'}</strong></div>
              <div><span>Role</span><strong>CUSTOMER</strong></div>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default CustomerApp
