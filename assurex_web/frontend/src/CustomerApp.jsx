import React, { useEffect, useState } from 'react'
import './CustomerApp.css'
import { api } from './api'
import {
  CustomerHome,
  CustomerClaims,
} from './App'
import { CustomerWarrantyClaimForm } from './WarrantyClaimSystem'

const SESSION_KEY = 'assurex_customer_session'
const TOKEN_KEY = 'assurex_customer_token'
const ADMIN_PATH = `${import.meta.env.BASE_URL}admin`

function getCustomerRouteFromPath(pathname) {
  const cleaned = pathname.replace(/\/+$/, '') || '/'
  const base = import.meta.env.BASE_URL.replace(/\/+$/, '') || ''
  const relative = cleaned.startsWith(base)
    ? cleaned.slice(base.length) || '/'
    : cleaned
  const segments = relative.split('/').filter(Boolean)

  if (segments[0] === 'claims' && segments[1]) {
    return { page: 'claims', claimId: decodeURIComponent(segments[1]) }
  }

  const map = {
    home: 'home',
    'warranty-ticket': 'submit',
    submit: 'submit',
    'my-claims': 'my-claims',
    products: 'products',
    warranties: 'warranties',
    notifications: 'notifications',
    profile: 'profile',
  }

  return { page: map[segments[0]] || 'home', claimId: null }
}

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
      if (item.resource_id) {
        const nextPath = `${import.meta.env.BASE_URL}claims/${encodeURIComponent(item.resource_id)}`
        window.history.pushState({}, '', nextPath)
        window.dispatchEvent(new PopStateEvent('popstate'))
      }
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
        </div>
      </header>
      {error && <div className="alert error">{error}</div>}
      <section className="panel">
        {loading ? <div className="state-card">Loading notifications...</div> : items.length === 0 ? (
          <div className="empty-state"><h3>No notifications</h3></div>
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


function CustomerProducts({ onNavigate }) {
  const [catalog, setCatalog] = useState([])
  const [policies, setPolicies] = useState({})
  const [products, setProducts] = useState([])
  const [productCategory, setProductCategory] = useState('')
  const [productId, setProductId] = useState('')
  const [serialNumber, setSerialNumber] = useState('')
  const [purchaseDate, setPurchaseDate] = useState('')
  const [purchasePrice, setPurchasePrice] = useState('')
  const [retailer, setRetailer] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  async function fetchProducts() {
    return Promise.all([
      api('/api/products'),
      api('/api/products/registered'),
      api('/api/warranty-policies'),
    ])
  }

  useEffect(() => {
    let active = true
    fetchProducts()
      .then(([available, registered, policySummaries]) => {
        if (!active) return
        setCatalog(available)
        setProducts(registered)
        setPolicies(policySummaries || {})
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
      const [available, registered, policySummaries] = await fetchProducts()
      setCatalog(available)
      setProducts(registered)
      setPolicies(policySummaries || {})
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  async function registerProduct(event) {
    event.preventDefault()
    setError('')
    setSuccess('')
    setSubmitting(true)
    try {
      const result = await api('/api/products/register', {
        method: 'POST',
        body: JSON.stringify({
          product_id: Number(productId),
          serial_number: serialNumber.trim(),
          purchase_date: purchaseDate,
          purchase_price: purchasePrice ? parseFloat(purchasePrice) : null,
          retailer: retailer.trim() || null,
        }),
      })
      setSuccess(`Product registered successfully! Assigned Registration ID: ${result.registration_code || 'REG-' + result.id}`)
      setProductCategory('')
      setProductId('')
      setSerialNumber('')
      setPurchaseDate('')
      setPurchasePrice('')
      setRetailer('')
      await loadProducts()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  const categories = [...new Set(catalog.map((product) => product.category).filter(Boolean))].sort()
  const categoryProducts = catalog.filter((product) => product.category === productCategory)
  const selectedPolicy = policies[productCategory]

  function formatPolicyItem(value) {
    return String(value || '').replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
  }

  const filteredProducts = products.filter((p) => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return (
      (p.name && p.name.toLowerCase().includes(q)) ||
      (p.brand && p.brand.toLowerCase().includes(q)) ||
      (p.model && p.model.toLowerCase().includes(q)) ||
      (p.serial_number && p.serial_number.toLowerCase().includes(q)) ||
      (p.retailer && p.retailer.toLowerCase().includes(q)) ||
      (p.registration_code && p.registration_code.toLowerCase().includes(q))
    )
  })

  const totalRegistered = products.length
  const activeWarranties = products.filter(
    (p) => p.warranty && p.warranty.status === 'Active'
  ).length
  const totalValue = products.reduce(
    (acc, p) => acc + (Number(p.purchase_price) || 0),
    0
  )

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Customer Portal</p>
          <h1>My Products</h1>
        </div>
      </header>

      {/* Overview Stat Cards */}
      <section className="stats-grid">
        <div className="stat-card">
          <span>Registered Products</span>
          <strong>{totalRegistered}</strong>
        </div>
        <div className="stat-card">
          <span>Active Warranties</span>
          <strong>{activeWarranties}</strong>
        </div>
        <div className="stat-card">
          <span>Total Protected Value</span>
          <strong>${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
        </div>
      </section>

      {/* Product Registration Form */}
      <form className="panel" onSubmit={registerProduct}>
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Product Onboarding</p>
            <h2>Register a New Product</h2>
          </div>
        </div>

        <div className="form-grid">
          <label className="form-field full-width">
            <span>Product Category <span style={{ color: 'var(--ax-danger)' }}>*</span></span>
            <select
              value={productCategory}
              onChange={(event) => {
                setProductCategory(event.target.value)
                setProductId('')
              }}
              required
            >
              <option value="">Select a product category...</option>
              {categories.map((category) => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </label>

          {selectedPolicy && (
            <div className="form-field full-width" style={{ marginTop: '-4px' }}>
              <div className="policy-summary-card">
                <div className="policy-summary-heading">
                  <div>
                    <span className="eyebrow">Warranty Policy Summary</span>
                    <h3>{productCategory} · {selectedPolicy.warranty_months} months standard warranty</h3>
                  </div>
                  <span className="policy-version">Policy v{selectedPolicy.policy_version}</span>
                </div>
                <div className="policy-summary-grid">
                  <div>
                    <strong>Usually covered</strong>
                    <p>{selectedPolicy.covered_faults.map(formatPolicyItem).join(', ') || 'Eligible product faults under normal use.'}</p>
                  </div>
                  <div>
                    <strong>Usually excluded</strong>
                    <p>{selectedPolicy.excluded_causes.map(formatPolicyItem).join(', ') || 'Accidental or misuse-related damage.'}</p>
                  </div>
                </div>
                <p className="policy-summary-note">
                  Prepare: {selectedPolicy.required_evidence.map(formatPolicyItem).join(', ')}.
                  {selectedPolicy.installation_required ? ' Installation evidence is also required for this category.' : ''}
                </p>
              </div>
            </div>
          )}

          <label className="form-field full-width">
            <span>Product Model <span style={{ color: 'var(--ax-danger)' }}>*</span></span>
            <select
              value={productId}
              onChange={(event) => setProductId(event.target.value)}
              required
              disabled={!productCategory}
            >
              <option value="">
                {productCategory ? 'Select a product model...' : 'Select a category first...'}
              </option>
              {categoryProducts.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name} · {product.brand} ({product.model}) — {product.warranty_months} Months Standard Warranty
                </option>
              ))}
            </select>
          </label>

          <label className="form-field">
            <span>Serial Number <span style={{ color: 'var(--ax-danger)' }}>*</span></span>
            <input
              value={serialNumber}
              onChange={(event) => setSerialNumber(event.target.value)}
              placeholder="e.g. SN-98234-A78"
              required
            />
          </label>

          <label className="form-field">
            <span>Purchase Date <span style={{ color: 'var(--ax-danger)' }}>*</span></span>
            <input
              type="date"
              value={purchaseDate}
              onChange={(event) => setPurchaseDate(event.target.value)}
              required
            />
          </label>

          <label className="form-field">
            <span>Purchase Price ($ USD)</span>
            <input
              type="number"
              step="0.01"
              min="0"
              value={purchasePrice}
              onChange={(event) => setPurchasePrice(event.target.value)}
              placeholder="e.g. 899.00"
            />
          </label>

          <label className="form-field">
            <span>Retailer / Store Name</span>
            <input
              type="text"
              value={retailer}
              onChange={(event) => setRetailer(event.target.value)}
              placeholder="e.g. Best Buy, Amazon, Apple Store"
            />
          </label>
        </div>

        {error && <div className="alert error" style={{ marginTop: '16px' }}>{error}</div>}
        {success && <div className="alert success" style={{ marginTop: '16px' }}>{success}</div>}

        <div className="form-actions">
          <button className="button primary" disabled={submitting}>
            {submitting ? 'Registering Product...' : 'Register Product & Activate Warranty'}
          </button>
        </div>
      </form>

      {/* Registered Products Table */}
      <section className="panel">
        <div className="panel-heading between">
          <div>
            <p className="eyebrow">Catalog</p>
            <h2>Registered Equipment ({filteredProducts.length})</h2>
          </div>
          <div className="table-search-box">
            <input
              type="text"
              placeholder="Search by name, serial, retailer..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid var(--ax-border)',
                fontSize: '13px',
                minWidth: '240px',
              }}
            />
          </div>
        </div>

        {loading ? (
          <div className="state-card">Loading products...</div>
        ) : filteredProducts.length === 0 ? (
          <div className="empty-state">
            <h3>No products found</h3>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Reg ID / Product ID</th>
                  <th>Product & Model</th>
                  <th>Serial Number</th>
                  <th>Retailer & Date</th>
                  <th>Price</th>
                  <th>Warranty Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map((product) => {
                  const warranty = product.warranty
                  const isExpiring = warranty?.status === 'Approaching Expiry'
                  const isExpired = warranty?.status === 'Expired'
                  return (
                    <tr key={product.id}>
                      <td>
                        <span className="user-id-badge" style={{ fontSize: '12px' }}>
                          {product.registration_code || `REG-${String(product.id).padStart(5, '0')}`}
                        </span>
                        <div style={{ fontSize: '11px', color: 'var(--ax-text-faint)', marginTop: '2px' }}>
                          {product.product_code || `PRD-${String(product.product_id).padStart(4, '0')}`}
                        </div>
                      </td>
                      <td>
                        <strong>{product.name}</strong>
                        <div style={{ fontSize: '12px', color: 'var(--ax-text-soft)' }}>
                          {product.brand} · {product.model} ({product.category})
                        </div>
                      </td>
                      <td className="mono" style={{ fontWeight: 600 }}>
                        {product.serial_number}
                      </td>
                      <td>
                        <div>{product.retailer || 'Authorized Dealer'}</div>
                        <small style={{ color: 'var(--ax-text-faint)' }}>{product.purchase_date}</small>
                      </td>
                      <td>
                        {product.purchase_price != null
                          ? `$${Number(product.purchase_price).toFixed(2)}`
                          : '—'}
                      </td>
                      <td>
                        {warranty ? (
                          <div>
                            <span
                              className={`status-badge ${
                                isExpired
                                  ? 'status-rejected'
                                  : isExpiring
                                    ? 'status-review'
                                    : 'status-approved'
                              }`}
                            >
                              {warranty.status}
                            </span>
                            <div style={{ fontSize: '11px', color: 'var(--ax-text-faint)', marginTop: '3px' }}>
                              Exp: {warranty.end_date}
                              {warranty.remaining_days != null && (
                                <span> ({warranty.remaining_days > 0 ? `${warranty.remaining_days}d left` : 'Expired'})</span>
                              )}
                            </div>
                          </div>
                        ) : (
                          <span className="status-badge">No Warranty</span>
                        )}
                      </td>
                      <td>
                        <button
                          className="button secondary"
                          style={{ padding: '6px 10px', fontSize: '12px' }}
                          onClick={() => {
                            if (onNavigate) {
                              onNavigate('submit')
                            }
                          }}
                        >
                          Claim Warranty
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}


function CustomerWarranties({ onNavigate }) {
  const [warranties, setWarranties] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedId, setExpandedId] = useState(null)

  useEffect(() => {
    api('/api/warranties')
      .then(setWarranties)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [])

  const countActive = warranties.filter((w) => w.status === 'Active').length
  const countExpiring = warranties.filter((w) => w.status === 'Approaching Expiry').length
  const countExpired = warranties.filter((w) => w.status === 'Expired').length

  const filtered = warranties.filter((w) => {
    if (statusFilter === 'ACTIVE' && w.status !== 'Active') return false
    if (statusFilter === 'EXPIRING' && w.status !== 'Approaching Expiry') return false
    if (statusFilter === 'EXPIRED' && w.status !== 'Expired') return false

    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return (
      (w.product && w.product.toLowerCase().includes(q)) ||
      (w.serial_number && w.serial_number.toLowerCase().includes(q)) ||
      (w.brand && w.brand.toLowerCase().includes(q)) ||
      (w.model && w.model.toLowerCase().includes(q)) ||
      (w.warranty_code && w.warranty_code.toLowerCase().includes(q))
    )
  })

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Customer Portal</p>
          <h1>Warranties & Coverage</h1>
        </div>
      </header>

      {/* Stats row */}
      <section className="stats-grid">
        <div className="stat-card">
          <span>Total Warranties</span>
          <strong>{warranties.length}</strong>
        </div>
        <div className="stat-card">
          <span>Active Coverage</span>
          <strong style={{ color: 'var(--ax-success)' }}>{countActive}</strong>
        </div>
        <div className="stat-card">
          <span>Approaching Expiry</span>
          <strong style={{ color: 'var(--ax-warning)' }}>{countExpiring}</strong>
        </div>
        <div className="stat-card">
          <span>Expired Policies</span>
          <strong style={{ color: 'var(--ax-danger)' }}>{countExpired}</strong>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading between" style={{ flexWrap: 'wrap', gap: '12px' }}>
          {/* Status Tabs */}
          <div style={{ display: 'flex', gap: '6px' }}>
            {[
              ['ALL', `All (${warranties.length})`],
              ['ACTIVE', `Active (${countActive})`],
              ['EXPIRING', `Approaching Expiry (${countExpiring})`],
              ['EXPIRED', `Expired (${countExpired})`],
            ].map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={`button ${statusFilter === key ? 'primary' : 'secondary'}`}
                style={{ padding: '6px 12px', fontSize: '13px' }}
                onClick={() => setStatusFilter(key)}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Search */}
          <input
            type="text"
            placeholder="Search warranties..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: '6px',
              border: '1px solid var(--ax-border)',
              fontSize: '13px',
              minWidth: '220px',
            }}
          />
        </div>

        {error && <div className="alert error">{error}</div>}

        {loading ? (
          <div className="state-card">Loading warranties...</div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <h3>No warranties found</h3>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Warranty Code</th>
                  <th>Product / Model</th>
                  <th>Serial Number</th>
                  <th>Coverage Duration</th>
                  <th>Remaining Days</th>
                  <th>Status</th>
                  <th>Policy Details</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((warranty) => {
                  const isExpanded = expandedId === warranty.id
                  const isExpiring = warranty.status === 'Approaching Expiry'
                  const isExpired = warranty.status === 'Expired'

                  return (
                    <React.Fragment key={warranty.id}>
                      <tr>
                        <td>
                          <span className="user-id-badge" style={{ fontSize: '12px' }}>
                            {warranty.warranty_code || `WAR-${String(warranty.id).padStart(5, '0')}`}
                          </span>
                        </td>
                        <td>
                          <strong>{warranty.product}</strong>
                          <div style={{ fontSize: '12px', color: 'var(--ax-text-soft)' }}>
                            {warranty.brand} · {warranty.model}
                          </div>
                        </td>
                        <td className="mono" style={{ fontWeight: 600 }}>
                          {warranty.serial_number}
                        </td>
                        <td>
                          <div>{warranty.start_date} → {warranty.end_date}</div>
                          <small style={{ color: 'var(--ax-text-faint)' }}>
                            Provider: {warranty.warranty_provider || 'AssureX Official Care'}
                          </small>
                        </td>
                        <td>
                          {warranty.remaining_days != null ? (
                            <span
                              style={{
                                fontWeight: 700,
                                color: isExpired
                                  ? 'var(--ax-danger)'
                                  : isExpiring
                                    ? 'var(--ax-warning)'
                                    : 'var(--ax-success)',
                              }}
                            >
                              {warranty.remaining_days > 0
                                ? `${warranty.remaining_days} days left`
                                : `Expired (${Math.abs(warranty.remaining_days)}d ago)`}
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td>
                          <span
                            className={`status-badge ${
                              isExpired
                                ? 'status-rejected'
                                : isExpiring
                                  ? 'status-review'
                                  : 'status-approved'
                            }`}
                          >
                            {warranty.status}
                          </span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '6px' }}>
                            <button
                              className="button secondary"
                              style={{ padding: '5px 9px', fontSize: '12px' }}
                              onClick={() => setExpandedId(isExpanded ? null : warranty.id)}
                            >
                              {isExpanded ? 'Hide Policy ▲' : 'View Policy ▼'}
                            </button>
                            {!isExpired && (
                              <button
                                className="button primary"
                                style={{ padding: '5px 9px', fontSize: '12px' }}
                                onClick={() => {
                                  if (onNavigate) onNavigate('submit')
                                }}
                              >
                                File Claim
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr style={{ background: '#f8fafc' }}>
                          <td colSpan="7" style={{ padding: '16px 20px' }}>
                            <div
                              style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                                gap: '16px',
                                background: '#ffffff',
                                border: '1px solid var(--ax-border)',
                                borderRadius: '8px',
                                padding: '16px',
                              }}
                            >
                              <div>
                                <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--ax-text-faint)', fontWeight: 700 }}>
                                  Warranty Provider & Type
                                </span>
                                <p style={{ margin: '4px 0 0', fontWeight: 600 }}>
                                  {warranty.warranty_provider || 'AssureX Official Care'} · {warranty.warranty_type || 'Standard Coverage'}
                                </p>
                              </div>

                              <div>
                                <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--ax-text-faint)', fontWeight: 700 }}>
                                  Authorized Service Center & Contact
                                </span>
                                <p style={{ margin: '4px 0 0', fontSize: '13px' }}>
                                  {warranty.service_center_details || 'AssureX Central Center, 123 Tech Park Blvd (Hotline: 1800-ASSUREX)'}
                                </p>
                              </div>

                              <div style={{ gridColumn: '1 / -1' }}>
                                <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--ax-success)', fontWeight: 700 }}>
                                  ✓ Coverage Conditions
                                </span>
                                <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--ax-text-soft)' }}>
                                  {warranty.coverage_conditions || 'Covers manufacturing defects, internal component failures, and electrical faults under normal operating conditions.'}
                                </p>
                              </div>

                              <div style={{ gridColumn: '1 / -1' }}>
                                <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--ax-danger)', fontWeight: 700 }}>
                                  ✕ Exclusions & Limitations
                                </span>
                                <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--ax-text-soft)' }}>
                                  {warranty.exclusions || 'Damage caused by accidents, water/liquid intrusion, unauthorized disassembly, software alterations, or physical abuse.'}
                                </p>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
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

function CustomerProfile({ session, onUpdateSession }) {
  const [formData, setFormData] = useState({
    full_name: session?.full_name || '',
    phone_number: session?.phone_number || '',
    address: session?.address || '',
    city: session?.city || '',
  })
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileMessage, setProfileMessage] = useState({ type: '', text: '' })

  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [passwordMessage, setPasswordMessage] = useState({ type: '', text: '' })

  useEffect(() => {
    if (session) {
      setFormData({
        full_name: session.full_name || '',
        phone_number: session.phone_number || '',
        address: session.address || '',
        city: session.city || '',
      })
    }
  }, [session?.full_name, session?.phone_number, session?.address, session?.city])

  async function handleProfileSubmit(event) {
    event.preventDefault()
    setProfileSaving(true)
    setProfileMessage({ type: '', text: '' })

    try {
      const updated = await api('/api/auth/profile', {
        method: 'PUT',
        body: JSON.stringify(formData),
      })
      onUpdateSession(updated)
      setProfileMessage({
        type: 'success',
        text: 'Profile contact information updated successfully!',
      })
    } catch (err) {
      setProfileMessage({
        type: 'error',
        text: err.message || 'Failed to update profile.',
      })
    } finally {
      setProfileSaving(false)
    }
  }

  async function handlePasswordSubmit(event) {
    event.preventDefault()
    setPasswordMessage({ type: '', text: '' })

    if (passwordData.new_password.length < 8) {
      setPasswordMessage({
        type: 'error',
        text: 'New password must be at least 8 characters long.',
      })
      return
    }

    if (passwordData.new_password !== passwordData.confirm_password) {
      setPasswordMessage({
        type: 'error',
        text: 'New password and confirmation do not match.',
      })
      return
    }

    setPasswordSaving(true)
    try {
      await api('/api/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: passwordData.current_password,
          new_password: passwordData.new_password,
        }),
      })
      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: '',
      })
      setPasswordMessage({
        type: 'success',
        text: 'Password updated successfully!',
      })
    } catch (err) {
      setPasswordMessage({
        type: 'error',
        text: err.message || 'Failed to change password.',
      })
    } finally {
      setPasswordSaving(false)
    }
  }

  const userId = session?.user_id || (session?.id ? `USR-${String(session.id).padStart(5, '0')}` : '—')

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Account Management</p>
          <h1>My Profile</h1>
        </div>
      </header>

      {/* Account Overview Card */}
      <section className="panel profile-overview-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Account Details</p>
            <h2>User Identification</h2>
          </div>
          <span className="status-badge status-approved">
            Active Account
          </span>
        </div>
        <div className="detail-grid">
          <div>
            <span>Unique User ID</span>
            <strong className="user-id-badge">{userId}</strong>
          </div>
          <div>
            <span>Email Address</span>
            <strong>{session?.email || '—'}</strong>
          </div>
          <div>
            <span>Assigned Role</span>
            <strong>{session?.role || 'CUSTOMER'}</strong>
          </div>
          <div>
            <span>Member Since</span>
            <strong>{formatNotificationDate(session?.created_at) || 'Active'}</strong>
          </div>
        </div>
      </section>

      {/* Contact Information Form */}
      <section className="panel profile-form-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Contact Details</p>
            <h2>Personal & Contact Information</h2>
          </div>
        </div>

        <form onSubmit={handleProfileSubmit}>
          <div className="form-grid">
            <label className="form-field">
              <span>Full Name</span>
              <input
                type="text"
                placeholder="e.g. John Doe"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              />
            </label>

            <label className="form-field">
              <span>Phone Number</span>
              <input
                type="tel"
                placeholder="e.g. +84 912 345 678"
                value={formData.phone_number}
                onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
              />
            </label>

            <label className="form-field">
              <span>Street Address</span>
              <input
                type="text"
                placeholder="e.g. 123 Nguyen Trai Street"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              />
            </label>

            <label className="form-field">
              <span>City / Province</span>
              <input
                type="text"
                placeholder="e.g. Ho Chi Minh City"
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
              />
            </label>
          </div>

          {profileMessage.text && (
            <div className={`alert ${profileMessage.type}`} style={{ marginTop: '16px' }}>
              {profileMessage.text}
            </div>
          )}

          <div className="form-actions">
            <button type="submit" className="button primary" disabled={profileSaving}>
              {profileSaving ? 'Saving Changes...' : 'Save Profile Changes'}
            </button>
          </div>
        </form>
      </section>

      {/* Security & Password Change */}
      <section className="panel profile-password-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Security</p>
            <h2>Change Password</h2>
          </div>
        </div>

        <form onSubmit={handlePasswordSubmit}>
          <div className="form-grid">
            <label className="form-field full-width">
              <span>Current Password</span>
              <input
                type="password"
                placeholder="Enter current password"
                value={passwordData.current_password}
                onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
                required
              />
            </label>

            <label className="form-field">
              <span>New Password</span>
              <input
                type="password"
                placeholder="At least 8 characters"
                minLength={8}
                value={passwordData.new_password}
                onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                required
              />
            </label>

            <label className="form-field">
              <span>Confirm New Password</span>
              <input
                type="password"
                placeholder="Re-enter new password"
                minLength={8}
                value={passwordData.confirm_password}
                onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                required
              />
            </label>
          </div>

          {passwordMessage.text && (
            <div className={`alert ${passwordMessage.type}`} style={{ marginTop: '16px' }}>
              {passwordMessage.text}
            </div>
          )}

          <div className="form-actions">
            <button type="submit" className="button secondary" disabled={passwordSaving}>
              {passwordSaving ? 'Updating Password...' : 'Update Password'}
            </button>
          </div>
        </form>
      </section>
    </>
  )
}

function CustomerApp() {
  const [session, setSession] = useState(
    () => loadSession()
  )

  const initialRoute = getCustomerRouteFromPath(window.location.pathname)
  const [customerPage, setCustomerPage] =
    useState(initialRoute.page)
  const [selectedClaimId, setSelectedClaimId] = useState(initialRoute.claimId || '')

  const [authMode, setAuthMode] = useState(null)

  const [refreshKey, setRefreshKey] = useState(0)
  const [guestEmail, setGuestEmail] = useState('')
  const [notificationCount, setNotificationCount] = useState(0)

  useEffect(() => {
    if (!session?.token) {
      setNotificationCount(0)
      return undefined
    }

    let active = true
    api('/api/notifications')
      .then((items) => {
        if (!active) return
        setNotificationCount(items.filter((item) => !item.is_read).length)
      })
      .catch(() => {
        if (active) setNotificationCount(0)
      })

    return () => {
      active = false
    }
  }, [session?.token, refreshKey])

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

  function handleUpdateSession(updated) {
    setSession((current) => {
      const fresh = { ...current, ...updated }
      localStorage.setItem(SESSION_KEY, JSON.stringify(fresh))
      return fresh
    })
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

  useEffect(() => {
    const syncRoute = () => {
      const route = getCustomerRouteFromPath(window.location.pathname)
      setCustomerPage(route.page)
      setSelectedClaimId(route.claimId || '')
    }

    window.addEventListener('popstate', syncRoute)
    return () => window.removeEventListener('popstate', syncRoute)
  }, [])

  function navigateCustomer(page, claimId = null) {
    if (!session && page !== 'home') {
      setAuthMode('login')
      return
    }

    setCustomerPage(page)
    setSelectedClaimId(claimId || '')

    const basePath = import.meta.env.BASE_URL.replace(/\/+$/, '')
    const normalized = page === 'home' ? `${basePath}/` : page === 'notifications' ? `${basePath}/notifications` : page === 'submit' ? `${basePath}/submit` : page === 'products' ? `${basePath}/products` : page === 'warranties' ? `${basePath}/warranties` : page === 'profile' ? `${basePath}/profile` : page === 'my-claims' ? `${basePath}/my-claims` : `${basePath}/`

    const targetUrl = claimId ? `${basePath}/claims/${encodeURIComponent(claimId)}` : normalized
    window.history.pushState({}, '', targetUrl)
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

  const displayName = session?.full_name || session?.email || ''
  const initial = displayName.charAt(0).toUpperCase() || 'U'

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
            ([key, label, icon]) => {
              const finalLabel = key === 'notifications' && notificationCount > 0
                ? `${label} (${notificationCount})`
                : label

              return (
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
                  {finalLabel}
                </button>
              )
            }
          )}
        </nav>

        {session ? (
          <>
            <div className="account-card">
              <div className="account-avatar">{initial}</div>
              <div className="account-details">
                <span>Signed in as</span>
                <strong>{session.full_name || session.email}</strong>
                {session.full_name && (
                  <span style={{ fontSize: '11px', color: 'var(--ax-text-faint)', wordBreak: 'break-all' }}>
                    {session.email}
                  </span>
                )}
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

        {(customerPage === 'submit' || customerPage === 'warranty-ticket') && (
          <CustomerWarrantyClaimForm
            email={session?.email || ''}
            customerName={session?.full_name || ''}
            onCreated={() => {
              refresh()
            }}
            onCancel={() => navigateCustomer('home')}
          />
        )}

        {customerPage === 'my-claims' && (
          <CustomerClaims
            email={session?.email || guestEmail}
            setEmail={setGuestEmail}
            hideIdentity
            refreshKey={refreshKey}
            selectedClaimId={selectedClaimId}
            onSelectClaim={(claimId) => navigateCustomer('my-claims', claimId)}
            onOpenClaim={(claimId) => navigateCustomer('my-claims', claimId)}
          />
        )}

        {customerPage === 'claims' && (
          <CustomerClaims
            email={session?.email || guestEmail}
            setEmail={setGuestEmail}
            hideIdentity
            refreshKey={refreshKey}
            selectedClaimId={selectedClaimId}
            onSelectClaim={(claimId) => navigateCustomer('my-claims', claimId)}
            onOpenClaim={(claimId) => navigateCustomer('my-claims', claimId)}
          />
        )}

        {customerPage === 'notifications' && <CustomerNotifications />}

        {customerPage === 'products' && (
          <CustomerProducts onNavigate={navigateCustomer} />
        )}

        {customerPage === 'warranties' && (
          <CustomerWarranties onNavigate={navigateCustomer} />
        )}

        {customerPage === 'profile' && (
          <CustomerProfile
            session={session}
            onUpdateSession={handleUpdateSession}
          />
        )}
      </main>
    </div>
  )
}

export default CustomerApp
