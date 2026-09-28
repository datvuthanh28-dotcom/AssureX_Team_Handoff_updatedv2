import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { api } from './api'
import { claimFieldGroups } from './claimFields'
import { ReviewerWarrantyDesk, WarrantyRetrainingDataset, CustomerWarrantyClaimForm } from './WarrantyClaimSystem'


const MODEL_METRICS = {
  pythonAccuracy: '99.11%',
  pythonF1: '99.11%',
  pythonAuc: '99.96%',
  pythonConfidence: '93.93%',
  gtmAccuracy: '86.22%',
  gtmF1: '86.10%',
  gtmAuc: '92.48%',
  gtmConfidence: '87.67%',
}


function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}


function formatNumber(value) {
  if (value === null || value === undefined) return '—'

  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2,
  }).format(value)
}


function downloadFile(filename, content, type) {
  const url = URL.createObjectURL(
    new Blob([content], { type })
  )
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}


function csvValue(value) {
  const text = String(value ?? '')
  return `"${text.replaceAll('"', '""')}"`
}


function StatusBadge({ value }) {
  const normalized = String(value || '')
    .toLowerCase()
    .replaceAll(' ', '-')

  return (
    <span className={`status-badge status-${normalized}`}>
      {value || 'Unknown'}
    </span>
  )
}


function LoadingState() {
  return (
    <div className="state-card">
      <div className="spinner" />
      <span>Loading data...</span>
    </div>
  )
}


function EmptyState({ title, description }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">◇</div>
      <h3>{title}</h3>
      {description ? <p>{description}</p> : null}
    </div>
  )
}


function PageHeader({
  eyebrow,
  title,
  action,
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
      </div>

      {action}
    </header>
  )
}


function StatCard({
  label,
  value,
  tone = 'default',
}) {
  return (
    <article className={`stat-card tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  )
}


function AdminDashboard({
  onNavigate,
  refreshKey,
  role,
}) {
  const [mlClaims, setMlClaims] = useState([])
  const [customerClaims, setCustomerClaims] = useState([])
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api('/api/claims').catch(() => []),
      api('/api/customer/claims').catch(() => []),
      api('/api/products').catch(() => []),
    ])
      .then(([ml, customer, prods]) => {
        setMlClaims(ml || [])
        setCustomerClaims(customer || [])
        setProducts(prods || [])
      })
      .finally(() => setLoading(false))
  }, [refreshKey])

  const totalClaims = customerClaims.length
  const review = customerClaims.filter(
    (claim) => ['Under Review', 'Manual Review'].includes(claim.status)
  ).length

  const approved = customerClaims.filter(
    (claim) => claim.status === 'Approved'
  ).length

  const rejected = customerClaims.filter(
    (claim) => claim.status === 'Rejected'
  ).length

  const needInfo = customerClaims.filter(
    (claim) => claim.status === 'Additional Information Required'
  ).length

  const closed = customerClaims.filter(
    (claim) => claim.status === 'Closed'
  ).length

  const approvalRate = totalClaims > 0
    ? ((approved / totalClaims) * 100).toFixed(1)
    : '0.0'

  const dualModelEvaluated = customerClaims.filter(
    (c) => c.decision && c.decision.model_consistency_status
  )

  const modelDisagreements = customerClaims.filter(
    (c) => c.decision?.model_consistency_status === 'Model Disagreement'
  ).length

  const modelMatches = customerClaims.filter(
    (c) => ['Strong Match', 'Acceptable Match'].includes(c.decision?.model_consistency_status)
  ).length

  const consistencyRate = dualModelEvaluated.length > 0
    ? ((modelMatches / dualModelEvaluated.length) * 100).toFixed(1)
    : '100.0'

  const pctApproved = totalClaims > 0 ? (approved / totalClaims) * 100 : 0
  const pctReview = totalClaims > 0 ? (review / totalClaims) * 100 : 0
  const pctNeedInfo = totalClaims > 0 ? (needInfo / totalClaims) * 100 : 0
  const pctRejected = totalClaims > 0 ? (rejected / totalClaims) * 100 : 0
  const pctClosed = totalClaims > 0 ? (closed / totalClaims) * 100 : 0

  return (
    <>
      <PageHeader
        eyebrow="Operations & Assurance Overview"
        title="Admin Dashboard"
        description="Monitor claim queues, dual-model ML classification performance, and product catalog."
        action={
          <div style={{ display: 'flex', gap: '8px' }}>
            {role !== 'ADMIN' && <button
              className="button secondary"
              onClick={() => onNavigate('customer-claims')}
            >
              Review Queue ({review})
            </button>}
            <button
              className="button primary"
              onClick={() => onNavigate('classify')}
            >
              + New Classification
            </button>
          </div>
        }
      />

      {loading ? (
        <LoadingState />
      ) : (
        <>
          <section className="stats-grid">
            <StatCard
              label="Customer Claims"
              value={totalClaims}
              hint="Total submitted"
            />

            <StatCard
              label="Under Review"
              value={review}
              hint="Requires reviewer action"
              tone={review > 0 ? 'warning' : 'neutral'}
            />

            <StatCard
              label="Approval Rate"
              value={`${approvalRate}%`}
              hint={`${approved} approved claims`}
              tone="success"
            />

            <StatCard
              label="Rejected Claims"
              value={rejected}
              hint="Policy or fraud rejections"
              tone={rejected > 0 ? 'danger' : 'neutral'}
            />

            <StatCard
              label="Dual-Model Agreement"
              value={`${consistencyRate}%`}
              hint={`${modelMatches} / ${dualModelEvaluated.length || totalClaims} verified`}
              tone={modelDisagreements > 0 ? 'warning' : 'success'}
            />

          </section>

          {totalClaims > 0 && (
            <div className="progress-stacked-container">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '12.5px' }}>
                <strong style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>📊</span> Claim Lifecycle Distribution
                </strong>
                <span style={{ opacity: 0.75 }}>{totalClaims} total claims evaluated</span>
              </div>
              <div className="progress-stacked-bar">
                <div className="progress-segment" style={{ width: `${pctApproved}%`, background: '#22c55e' }} title={`Approved: ${approved} (${pctApproved.toFixed(1)}%)`} />
                <div className="progress-segment" style={{ width: `${pctReview}%`, background: '#f59e0b' }} title={`Under Review: ${review} (${pctReview.toFixed(1)}%)`} />
                <div className="progress-segment" style={{ width: `${pctNeedInfo}%`, background: '#3b82f6' }} title={`Needs Info: ${needInfo} (${pctNeedInfo.toFixed(1)}%)`} />
                <div className="progress-segment" style={{ width: `${pctRejected}%`, background: '#ef4444' }} title={`Rejected: ${rejected} (${pctRejected.toFixed(1)}%)`} />
                <div className="progress-segment" style={{ width: `${pctClosed}%`, background: '#64748b' }} title={`Closed: ${closed} (${pctClosed.toFixed(1)}%)`} />
              </div>
              <div className="progress-legend">
                <div className="legend-item"><span className="legend-dot" style={{ background: '#22c55e' }} /> Approved ({approved})</div>
                <div className="legend-item"><span className="legend-dot" style={{ background: '#f59e0b' }} /> Under Review ({review})</div>
                {needInfo > 0 && <div className="legend-item"><span className="legend-dot" style={{ background: '#3b82f6' }} /> Needs Info ({needInfo})</div>}
                <div className="legend-item"><span className="legend-dot" style={{ background: '#ef4444' }} /> Rejected ({rejected})</div>
                {closed > 0 && <div className="legend-item"><span className="legend-dot" style={{ background: '#64748b' }} /> Closed ({closed})</div>}
              </div>
            </div>
          )}

          <section className="dashboard-grid">
            <article className="panel" style={role === 'ADMIN' ? { display: 'none' } : undefined}>
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Customer Queue</p>
                  <h2>Recent Claims</h2>
                </div>

                <button
                  className="text-button"
                  onClick={() => onNavigate('customer-claims')}
                >
                  View all →
                </button>
              </div>

              {customerClaims.length === 0 ? (
                <EmptyState
                  title="No customer claims yet"
                  description="Submitted customer claims will appear here."
                />
              ) : (
                <div className="compact-list">
                  {customerClaims
                    .slice(0, 6)
                    .map((claim) => (
                      <div
                        className="compact-row"
                        key={claim.id}
                        style={{ cursor: 'pointer' }}
                        onClick={() => onNavigate('customer-claims')}
                      >
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <strong className="mono" style={{ fontSize: '13px' }}>
                              {claim.claim_id}
                            </strong>
                            {claim.decision?.model_consistency_status === 'Model Disagreement' && (
                              <span className="days-left-badge expired" style={{ fontSize: '10px', padding: '1px 5px' }}>
                                Disagreement
                              </span>
                            )}
                          </div>
                          <span style={{ fontSize: '12px', display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {claim.customer_name} · {claim.product_name}
                          </span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <StatusBadge value={claim.status} />
                          <span style={{ fontSize: '11px', opacity: 0.6 }}>Review →</span>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </article>

            <article className="panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Dual-Model Architecture</p>
                  <h2>ML Engine Activity</h2>
                </div>

                <button
                  className="text-button"
                  onClick={() => onNavigate('model')}
                >
                  Model details →
                </button>
              </div>

              <div className="dual-model-grid" style={{ marginTop: '4px', marginBottom: '14px' }}>
                <div className="model-card python-model">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, color: '#3b82f6' }}>
                      PRIMARY MODEL
                    </span>
                    <span className="days-left-badge active" style={{ fontSize: '10px' }}>
                      Gradient Boosting
                    </span>
                  </div>
                  <h4 style={{ margin: '6px 0 2px', fontSize: '14px' }}>Python Classifier</h4>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginTop: '8px' }}>
                    <span>Accuracy: <strong>{MODEL_METRICS.pythonAccuracy}</strong></span>
                    <span>Macro F1: <strong>{MODEL_METRICS.pythonF1}</strong></span>
                    <span>AUC-ROC: <strong>{MODEL_METRICS.pythonAuc}</strong></span>
                  </div>
                </div>

                <div className="model-card google-model">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, color: '#ea4335' }}>
                      BENCHMARK MODEL
                    </span>
                    <span className="days-left-badge active" style={{ fontSize: '10px' }}>
                      Cloud GTM
                    </span>
                  </div>
                  <h4 style={{ margin: '6px 0 2px', fontSize: '14px' }}>Teachable Machine</h4>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginTop: '8px' }}>
                    <span>Accuracy: <strong>{MODEL_METRICS.gtmAccuracy}</strong></span>
                    <span>Macro F1: <strong>{MODEL_METRICS.gtmF1}</strong></span>
                    <span>AUC-ROC: <strong>{MODEL_METRICS.gtmAuc}</strong></span>
                  </div>
                </div>
              </div>

              <div className="model-summary">
                <div>
                  <span>Classifications Stored</span>
                  <strong>{mlClaims.length}</strong>
                </div>

                <div>
                  <span>Mean Confidence</span>
                  <strong>{MODEL_METRICS.pythonConfidence}</strong>
                </div>

                <div>
                  <span>Consistency Rate</span>
                  <strong>{consistencyRate}%</strong>
                </div>
              </div>

            </article>
          </section>
        </>
      )}
    </>
  )
}


function AdminCustomerClaims({
  refreshKey,
  onChanged,
  canReview,
  resolvedOnly = false,
}) {
  const [claims, setClaims] = useState([])
  const [selected, setSelected] = useState(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [reviewerComment, setReviewerComment] = useState('')
  const [reviewError, setReviewError] = useState('')
  const [actionSuccess, setActionSuccess] = useState('')

  function loadClaims() {
    setLoading(true)

    api('/api/customer/claims')
      .then((data) => {
        setClaims(data)

        if (selected) {
          const fresh = data.find(
            (claim) =>
              claim.claim_id === selected.claim_id
          )

          if (fresh) setSelected(fresh)
        }
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadClaims()
  }, [refreshKey])

  const counts = useMemo(() => {
    const map = {
      All: claims.length,
      'Under Review': 0,
      'Manual Review': 0,
      Approved: 0,
      Rejected: 0,
      'Additional Information Required': 0,
      Closed: 0,
    }
    claims.forEach((c) => {
      if (map[c.status] !== undefined) {
        map[c.status] += 1
      }
    })
    return map
  }, [claims])

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()

    return claims.filter((claim) => {
      const matchesSearch =
        !term ||
        [
          claim.claim_id,
          claim.customer_name,
          claim.email,
          claim.product_name,
          claim.serial_number,
          claim.fault_description,
        ].some((value) =>
          String(value || '')
            .toLowerCase()
            .includes(term)
        )

      const matchesStatus = resolvedOnly
        ? ['Approved', 'Rejected', 'Closed'].includes(claim.status)
        : statusFilter === 'All' || claim.status === statusFilter

      return matchesSearch && matchesStatus
    })
  }, [claims, search, statusFilter])

  function exportClaims() {
    const columns = [
      ['claim_id', 'Claim ID'],
      ['customer_name', 'Customer'],
      ['email', 'Email'],
      ['product_name', 'Product'],
      ['serial_number', 'Serial Number'],
      ['claim_amount', 'Amount'],
      ['status', 'Status'],
      ['created_at', 'Submitted'],
    ]
    const csv = [
      columns.map(([, label]) => csvValue(label)).join(','),
      ...filtered.map((claim) =>
        columns.map(([key]) => csvValue(claim[key])).join(',')
      ),
    ].join('\r\n')
    downloadFile('assurex-claims.csv', `\uFEFF${csv}`, 'text/csv;charset=utf-8')
  }

  async function updateStatus(status) {
    if (!selected) return
    if (status === 'Additional Information Required' && !reviewerComment.trim()) {
      setReviewError('Reviewer note is required when requesting more information.')
      return
    }

    setUpdating(true)
    setReviewError('')
    setActionSuccess('')

    try {
      const updated = await api(
        `/api/customer/claims/${selected.claim_id}/status`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            status,
            reviewer_comment: reviewerComment.trim() || null,
          }),
        }
      )

      setSelected(updated)
      setActionSuccess(`Claim ${updated.claim_id} updated to status "${status}".`)

      setClaims((current) =>
        current.map((claim) =>
          claim.claim_id === updated.claim_id
            ? updated
            : claim
        )
      )

      onChanged()
    } catch (error) {
      setReviewError(error.message)
    } finally {
      setUpdating(false)
    }
  }

  const rationalePresets = [
    'Meets standard warranty conditions; defect confirmed under standard operation.',
    'Excluded from warranty coverage due to physical or accidental impact damage.',
    'Excluded due to evidence of liquid intrusion, moisture or corrosion.',
    'Missing proof of purchase; original retailer invoice required.',
    'Serial number mismatch between product label and registration record.',
    'Forwarded to authorized service center for in-person hardware diagnostic testing.',
  ]

  return (
    <>
      <PageHeader
        eyebrow="Review Queue & Operations"
        title={resolvedOnly ? 'Resolved Claims' : 'Claim Queue'}
        description={resolvedOnly ? 'Review completed decisions and the audit trail used for retraining feedback.' : 'Review claims, attached evidence, policy validation and decision history.'}
        action={
          <button className="button secondary" onClick={exportClaims} disabled={filtered.length === 0}>
            Export CSV ({filtered.length})
          </button>
        }
      />

      <section className="panel" style={selected ? { display: 'none' } : undefined}>
        <div className="toolbar" style={{ flexWrap: 'wrap', gap: '12px' }}>
          <div className="search-box" style={{ flex: '1 1 280px' }}>
            <span>⌕</span>
            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search Claim ID, customer, serial, product..."
            />
          </div>

          <div className="filter-tabs">
            {['All', 'Under Review', 'Manual Review', 'Approved', 'Rejected', 'Additional Information Required', 'Closed'].map((tab) => (
              <button
                key={tab}
                type="button"
                className={`filter-tab ${statusFilter === tab ? 'active' : ''}`}
                onClick={() => setStatusFilter(tab)}
              >
                <span>{tab}</span>
                {counts[tab] !== undefined && (
                  <span className="filter-tab-count">{counts[tab]}</span>
                )}
              </button>
            ))}
          </div>

          <span className="results-count">
            {filtered.length} claim(s)
          </span>
        </div>

        {loading ? (
          <LoadingState />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No matching claims"
            description="Try changing the search or status filter tab."
          />
        ) : (
          <div className="table-wrapper claim-queue-table-wrapper">
            <table className="data-table claim-queue-table">
              <thead>
                <tr>
                  <th>Claim ID</th>
                  <th>Customer</th>
                  <th>Product</th>
                  <th>Status</th>
                  <th>Submitted</th>
                  <th>Detail</th>
                </tr>
              </thead>

              <tbody>
                {filtered.map((claim) => (
                  <tr
                    key={claim.id}
                    className={
                      selected?.id === claim.id
                        ? 'selected-row'
                        : ''
                    }
                    onClick={() => {
                      setSelected(claim)
                      setReviewerComment('')
                      setReviewError('')
                      setActionSuccess('')
                    }}
                  >
                    <td className="mono">
                      <strong>{claim.claim_id}</strong>
                      {claim.decision?.model_consistency_status === 'Model Disagreement' && (
                        <div style={{ marginTop: '2px' }}>
                          <span className="days-left-badge expired" style={{ fontSize: '10px', padding: '1px 5px' }}>
                            Model Disagreement
                          </span>
                        </div>
                      )}
                    </td>
                    <td>
                      <strong>
                        {claim.customer_name}
                      </strong>
                      <small>
                        {claim.email}
                      </small>
                    </td>
                    <td>
                      <div>{claim.product_name}</div>
                      <small className="mono" style={{ opacity: 0.7 }}>{claim.serial_number}</small>
                    </td>
                    <td>
                      <StatusBadge
                        value={claim.status}
                      />
                    </td>
                    <td>
                      {formatDate(
                        claim.created_at
                      )}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="button secondary claim-detail-button"
                        onClick={(event) => {
                          event.stopPropagation()
                          setSelected(claim)
                          setReviewerComment('')
                          setReviewError('')
                          setActionSuccess('')
                        }}
                      >
                        Detail
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected && (
        <section className="panel detail-panel claim-detail-page">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                Claim Detail
              </p>
              <h2>{selected.claim_id}</h2>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button
                className="button secondary"
                onClick={() => setSelected(null)}
              >
                Back to queue
              </button>
              <StatusBadge value={selected.status} />
              <button
                className="button secondary"
                onClick={() => downloadFile(
                  `${selected.claim_id}-report.json`,
                  JSON.stringify(selected, null, 2),
                  'application/json'
                )}
              >
                Download Claim Report
              </button>
            </div>
          </div>

          <div className="detail-grid claim-summary-grid">
            <div>
              <span>Claim ID</span>
              <strong className="mono">{selected.claim_id}</strong>
            </div>

            <div>
              <span>Customer</span>
              <strong>{selected.customer_name}</strong>
            </div>

            <div>
              <span>Email</span>
              <strong>{selected.email}</strong>
            </div>

            <div>
              <span>Product Category</span>
              <strong>{selected.product_category || selected.raw_input?.product_category || '—'}</strong>
            </div>

            <div>
              <span>Product</span>
              <strong>{selected.product_name}</strong>
            </div>

            <div>
              <span>Serial Number</span>
              <strong className="mono">{selected.serial_number}</strong>
            </div>

            <div>
              <span>Claim Date</span>
              <strong>{formatDate(selected.created_at)}</strong>
            </div>

            <div>
              <span>Purchase Date</span>
              <strong>{selected.purchase_date}</strong>
            </div>

            <div>
              <span>Claim Amount</span>
              <strong>{formatNumber(selected.claim_amount)}</strong>
            </div>

            <div>
              <span>Fault Type</span>
              <strong>{selected.fault_type || selected.raw_input?.fault_type || '—'}</strong>
            </div>

            <div>
              <span>Damage Type</span>
              <strong>{selected.damage_type || selected.raw_input?.damage_type || '—'}</strong>
            </div>

            <div>
              <span>Warranty Status</span>
              <strong>{selected.decision?.derived_data?.WarrantyStatus || selected.raw_input?.warranty_status || '—'}</strong>
            </div>

            <div>
              <span>Model Result</span>
              <strong>{selected.decision?.final_decision || selected.predicted_class || '—'}</strong>
            </div>

            <div>
              <span>Reviewer Status</span>
              <strong>{selected.status || 'Pending'}</strong>
            </div>

          </div>

          <div className="description-box">
            <span>Customer Reported Fault Description</span>
            <p>{selected.fault_description}</p>
          </div>

          {false && <>
          {/* Dual-Model Comparison Card */}
          {selected.decision && (
            <div className="claim-analysis" style={{ marginTop: '20px' }}>
              <div className="panel-heading" style={{ marginBottom: '8px' }}>
                <div>
                  <p className="eyebrow">AI + Rule Analysis</p>
                  <h3>Dual-Model Intelligence Evaluation</h3>
                </div>
              </div>

              <div className="dual-model-grid">
                <div className="model-card python-model">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em', color: '#3b82f6' }}>
                      PYTHON CLASSIFIER (PRIMARY)
                    </span>
                    <span className="days-left-badge active" style={{ fontSize: '10px' }}>
                      Primary ML
                    </span>
                  </div>
                  <h4 style={{ margin: '8px 0 4px', fontSize: '15px' }}>
                    {selected.decision.python_model_name || selected.decision.model_name || 'Gradient Boosting / Random Forest'}
                  </h4>
                  <div style={{ fontSize: '11.5px', color: 'var(--ax-text-faint, #64748b)', marginBottom: '10px' }}>
                    Version: {selected.decision.python_model_version || 'v1.0.0'}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px' }}>
                    <div>
                      <span style={{ fontSize: '11px', opacity: 0.75 }}>Model Prediction</span>
                      <div style={{ fontWeight: 700, fontSize: '15px' }}>{selected.decision.ml_prediction}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '11px', opacity: 0.75 }}>Confidence</span>
                      <div style={{ fontWeight: 700, fontSize: '15px', color: '#3b82f6' }}>
                        {(selected.decision.ml_confidence * 100).toFixed(2)}%
                      </div>
                    </div>
                  </div>
                </div>

                <div className="model-card google-model">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em', color: '#ea4335' }}>
                      GOOGLE TEACHABLE MACHINE (GTM)
                    </span>
                    <span
                      className={`days-left-badge ${selected.decision.google_inference_status === 'connected' ? 'active' : 'expiring'}`}
                      style={{ fontSize: '10px' }}
                    >
                      {selected.decision.google_inference_status === 'connected' ? 'Connected' : 'Standby / Benchmark'}
                    </span>
                  </div>
                  <h4 style={{ margin: '8px 0 4px', fontSize: '15px' }}>
                    {selected.decision.google_model_name || 'Google Cloud GTM Model'}
                  </h4>
                  <div style={{ fontSize: '11.5px', color: 'var(--ax-text-faint, #64748b)', marginBottom: '10px' }}>
                    Endpoint: {selected.decision.google_model_version || 'Public GTM URL'}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px' }}>
                    <div>
                      <span style={{ fontSize: '11px', opacity: 0.75 }}>GTM Prediction</span>
                      <div style={{ fontWeight: 700, fontSize: '15px' }}>
                        {selected.decision.google_prediction || 'Standby'}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '11px', opacity: 0.75 }}>Confidence</span>
                      <div style={{ fontWeight: 700, fontSize: '15px', color: '#ea4335' }}>
                        {selected.decision.google_confidence != null
                          ? `${(selected.decision.google_confidence * 100).toFixed(2)}%`
                          : '—'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="consistency-box">
                <div>
                  <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.7, fontWeight: 700 }}>
                    Dual-Model Consistency Status
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                    <span
                      className={`days-left-badge ${
                        selected.decision.model_consistency_status === 'Strong Match'
                          ? 'active'
                          : selected.decision.model_consistency_status === 'Acceptable Match'
                            ? 'active'
                            : selected.decision.model_consistency_status === 'Model Disagreement'
                              ? 'expired'
                              : 'expiring'
                      }`}
                      style={{ fontSize: '12.5px', padding: '3px 10px' }}
                    >
                      {selected.decision.model_consistency_status || 'Dual Evaluation Standby'}
                    </span>
                    {selected.decision.confidence_difference != null && (
                      <span style={{ fontSize: '12px', opacity: 0.7 }}>
                        (Difference: {(selected.decision.confidence_difference * 100).toFixed(2)}%)
                      </span>
                    )}
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.7, fontWeight: 700 }}>
                    Final Rule Engine Outcome
                  </span>
                  <div style={{ fontWeight: 700, fontSize: '15px', marginTop: '4px' }}>
                    {selected.decision.final_decision}
                  </div>
                </div>
              </div>

              {selected.decision.decision_reasons?.length > 0 && (
                <div style={{ marginTop: '14px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600 }}>Decision Reasons:</span>
                  <ul className="decision-reason-list" style={{ marginTop: '6px' }}>
                    {selected.decision.decision_reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}

              <details className="analysis-inputs" style={{ marginTop: '14px' }}>
                <summary>Warranty Policy Validation & Rule Inputs</summary>
                <div className="feature-grid">
                  {Object.entries({
                    ...selected.decision.derived_data,
                    ...selected.decision.model_features,
                  }).map(([name, value]) => (
                    <div key={name}>
                      <span>{name}</span>
                      <strong>{String(value ?? '—')}</strong>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          )}

          {/* Attached Evidence & Verified Documents Section */}
          <div style={{ marginTop: '24px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '16px' }}>
            <p className="eyebrow">Document Integrity & Evidence</p>
            <h3 style={{ margin: '4px 0 12px', fontSize: '16px' }}>Attached Files (SHA-256 Verified)</h3>

            <div className="evidence-upload-grid">
              {/* Receipt */}
              <div className={`evidence-upload-card ${selected.receipt_url ? 'has-file' : ''}`}>
                <h4><span>📄</span> Purchase Receipt</h4>
                <p>Retailer proof of purchase & date verification</p>
                {selected.receipt_url ? (
                  <>
                    {selected.document_hashes?.receipt && (
                      <span className="sha256-badge" title={selected.document_hashes.receipt}>
                        SHA-256: {selected.document_hashes.receipt.substring(0, 16)}...
                      </span>
                    )}
                    <a
                      href={selected.receipt_url}
                      target="_blank"
                      rel="noreferrer"
                      className="button secondary"
                      style={{ padding: '5px 10px', fontSize: '12px', marginTop: 'auto', textAlign: 'center' }}
                    >
                      View / Download Receipt ↗
                    </a>
                  </>
                ) : (
                  <span style={{ fontSize: '11.5px', color: '#94a3b8', fontStyle: 'italic', marginTop: 'auto' }}>
                    Not provided by customer
                  </span>
                )}
              </div>

              {/* Product Photo */}
              <div className={`evidence-upload-card ${selected.product_image_url ? 'has-file' : ''}`}>
                <h4><span>📷</span> Product Photo</h4>
                <p>Physical unit & serial barcode verification</p>
                {selected.product_image_url ? (
                  <>
                    {selected.document_hashes?.product_image && (
                      <span className="sha256-badge" title={selected.document_hashes.product_image}>
                        SHA-256: {selected.document_hashes.product_image.substring(0, 16)}...
                      </span>
                    )}
                    <a
                      href={selected.product_image_url}
                      target="_blank"
                      rel="noreferrer"
                      className="button secondary"
                      style={{ padding: '5px 10px', fontSize: '12px', marginTop: 'auto', textAlign: 'center' }}
                    >
                      View Product Image ↗
                    </a>
                  </>
                ) : (
                  <span style={{ fontSize: '11.5px', color: '#94a3b8', fontStyle: 'italic', marginTop: 'auto' }}>
                    Not provided by customer
                  </span>
                )}
              </div>

              {/* Fault / Damage Evidence */}
              <div className={`evidence-upload-card ${selected.evidence_photo_url ? 'has-file' : ''}`}>
                <h4><span>⚠️</span> Fault / Defect Evidence</h4>
                <p>Visual verification of defect or screen damage</p>
                {selected.evidence_photo_url ? (
                  <>
                    {selected.document_hashes?.fault_evidence && (
                      <span className="sha256-badge" title={selected.document_hashes.fault_evidence}>
                        SHA-256: {selected.document_hashes.fault_evidence.substring(0, 16)}...
                      </span>
                    )}
                    <a
                      href={selected.evidence_photo_url}
                      target="_blank"
                      rel="noreferrer"
                      className="button secondary"
                      style={{ padding: '5px 10px', fontSize: '12px', marginTop: 'auto', textAlign: 'center' }}
                    >
                      View Fault Evidence ↗
                    </a>
                  </>
                ) : (
                  <span style={{ fontSize: '11.5px', color: '#94a3b8', fontStyle: 'italic', marginTop: 'auto' }}>
                    Not provided by customer
                  </span>
                )}
              </div>

              {/* Repair Diagnostic Report */}
              <div className={`evidence-upload-card ${selected.repair_report_url ? 'has-file' : ''}`}>
                <h4><span>🔧</span> Service Diagnostic Report</h4>
                <p>Service center diagnostic inspection sheet</p>
                {selected.repair_report_url ? (
                  <>
                    {selected.document_hashes?.repair_report && (
                      <span className="sha256-badge" title={selected.document_hashes.repair_report}>
                        SHA-256: {selected.document_hashes.repair_report.substring(0, 16)}...
                      </span>
                    )}
                    <a
                      href={selected.repair_report_url}
                      target="_blank"
                      rel="noreferrer"
                      className="button secondary"
                      style={{ padding: '5px 10px', fontSize: '12px', marginTop: 'auto', textAlign: 'center' }}
                    >
                      View Diagnostic Report ↗
                    </a>
                  </>
                ) : (
                  <span style={{ fontSize: '11.5px', color: '#94a3b8', fontStyle: 'italic', marginTop: 'auto' }}>
                    No prior report attached
                  </span>
                )}
              </div>
            </div>
          </div>

          </>}

          {/* Prior Service & Repair History Panel */}
          {(selected.repair_center_name || selected.previous_repair_date || selected.replaced_parts || selected.repair_cost) && (
            <div style={{ marginTop: '24px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '16px' }}>
              <p className="eyebrow">Service Center Records</p>
              <h3 style={{ margin: '4px 0 12px', fontSize: '16px' }}>Prior Product Service History</h3>
              <div className="detail-grid">
                <div>
                  <span>Service Center</span>
                  <strong>{selected.repair_center_name || 'Authorized Service Provider'}</strong>
                </div>
                <div>
                  <span>Prior Repair Date</span>
                  <strong>{selected.previous_repair_date || 'Prior to claim'}</strong>
                </div>
                <div>
                  <span>Replaced Parts</span>
                  <strong>{selected.replaced_parts || 'Maintenance only'}</strong>
                </div>
                <div>
                  <span>Outcome</span>
                  <strong>{selected.repair_outcome || 'Fully Resolved'}</strong>
                </div>
                <div>
                  <span>Previous Cost</span>
                  <strong>{selected.repair_cost ? `$${selected.repair_cost}` : 'Covered by warranty'}</strong>
                </div>
              </div>
            </div>
          )}

          <div style={{ marginTop: '20px' }}>
            <ClaimTimeline claimId={selected.claim_id} status={selected.status} />
          </div>

          {/* Reviewer Action Controls */}
          {canReview && (
            <div className="decision-actions" style={{ marginTop: '24px' }}>
              <label className="review-note">
                <span style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Reviewer Decision, Override & Audit Note
                </span>
                <p style={{ margin: '0 0 6px', fontSize: '12px', opacity: 0.75 }}>
                  Click a preset rationale to quickly fill, or write a custom audit reason.
                </p>
                <div className="rationale-presets">
                  {rationalePresets.map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      className="rationale-preset-btn"
                      onClick={() => setReviewerComment(preset)}
                    >
                      + {preset.substring(0, 38)}...
                    </button>
                  ))}
                </div>
                <textarea
                  rows="3"
                  value={reviewerComment}
                  onChange={(event) => setReviewerComment(event.target.value)}
                  placeholder="Record official justification for approval, rejection, or information request..."
                />
              </label>

              {actionSuccess && <div className="alert success" style={{ marginBottom: '12px' }}>{actionSuccess}</div>}
              {reviewError && <div className="alert error" style={{ marginBottom: '12px' }}>{reviewError}</div>}

              <div className="reviewer-action-buttons">
                <button
                  className="button success"
                  disabled={updating}
                  onClick={() => updateStatus('Approved')}
                >
                  {updating ? 'Saving...' : 'Approve'}
                </button>

                <button
                  className="button danger"
                  disabled={updating}
                  onClick={() => updateStatus('Rejected')}
                >
                  {updating ? 'Saving...' : 'Reject'}
                </button>

                <button
                  className="button warning"
                  disabled={updating}
                  onClick={() => updateStatus('Under Review')}
                >
                  {updating ? 'Saving...' : 'Review'}
                </button>

                <button
                  className="button secondary"
                  disabled={updating || !reviewerComment.trim()}
                  title={!reviewerComment.trim() ? 'Please provide a reviewer note explaining what info is needed' : ''}
                  onClick={() => updateStatus('Additional Information Required')}
                >
                  {updating ? 'Saving...' : 'More info'}
                </button>
              </div>
            </div>
          )}
        </section>
      )}
    </>
  )
}


function MLClassification({ onCreated }) {
  const [claimId, setClaimId] = useState('')
  const [formData, setFormData] = useState({})
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function changeField(field, value) {
    setFormData((current) => ({
      ...current,
      [field.name]:
        field.type === 'number' && value !== ''
          ? Number(value)
          : value,
    }))
  }

  async function submit(event) {
    event.preventDefault()

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const data = await api(
        '/api/claims/predict',
        {
          method: 'POST',
          body: JSON.stringify({
            claim_id: claimId,
            input_data: formData,
          }),
        }
      )

      setResult(data)
      onCreated()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="ML classification"
        title="New Classification"
        description="Create a structured claim and run the production Gradient Boosting model."
      />

      <form
        className="claim-form"
        onSubmit={submit}
      >
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                Identification
              </p>
              <h2>Claim Information</h2>
            </div>
          </div>

          <div className="form-grid">
            <label className="form-field">
              <span>Claim ID</span>
              <input
                value={claimId}
                onChange={(event) =>
                  setClaimId(event.target.value)
                }
                placeholder="e.g. CLM01001"
                required
              />
            </label>
          </div>
        </section>

        {claimFieldGroups.map((group) => (
          <section
            className="panel"
            key={group.title}
          >
            <div className="panel-heading">
              <h3>{group.title}</h3>
            </div>

            <div className="form-grid">
              {group.fields.map((field) => (
                <label
                  className="form-field"
                  key={field.name}
                >
                  <span>{field.label}</span>

                  {field.type === 'select' ? (
                    <select
                      value={
                        formData[field.name] ?? ''
                      }
                      onChange={(event) =>
                        changeField(
                          field,
                          event.target.value
                        )
                      }
                      required
                    >
                      <option value="">
                        Select...
                      </option>

                      {field.options.map(
                        (option) => (
                          <option
                            key={option}
                            value={option}
                          >
                            {option}
                          </option>
                        )
                      )}
                    </select>
                  ) : (
                    <input
                      type="number"
                      min={field.min}
                      max={field.max}
                      step={field.step}
                      value={
                        formData[field.name] ?? ''
                      }
                      onChange={(event) =>
                        changeField(
                          field,
                          event.target.value
                        )
                      }
                      required
                    />
                  )}
                </label>
              ))}
            </div>
          </section>
        ))}

        {error && (
          <div className="alert error">
            {error}
          </div>
        )}

        {result && (
          <section className="result-card">
            <div>
              <p className="eyebrow">
                Classification Result
              </p>

              <h2>{result.predicted_class}</h2>

              <p>
                Confidence:{' '}
                <strong>
                  {(result.confidence * 100)
                    .toFixed(2)}
                  %
                </strong>
              </p>
            </div>

            <div className="probability-list">
              {Object.entries(
                result.probabilities
              ).map(([label, probability]) => (
                <div
                  className="probability-row"
                  key={label}
                >
                  <div>
                    <span>{label}</span>
                    <strong>
                      {(probability * 100)
                        .toFixed(2)}
                      %
                    </strong>
                  </div>

                  <div className="progress-track">
                    <div
                      className="progress-value"
                      style={{
                        width: `${probability * 100}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        <div className="form-actions">
          <button
            className="button primary large"
            disabled={loading}
          >
            {loading
              ? 'Classifying...'
              : 'Classify Claim'}
          </button>
        </div>
      </form>
    </>
  )
}


function MLHistory({ refreshKey }) {
  const [claims, setClaims] = useState([])
  const [selected, setSelected] = useState(null)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api('/api/claims')
      .then(setClaims)
      .finally(() => setLoading(false))
  }, [refreshKey])

  const filtered = claims.filter((claim) =>
    claim.claim_id
      .toLowerCase()
      .includes(search.toLowerCase())
  )

  async function openClaim(claimId) {
    const detail = await api(
      `/api/claims/${claimId}`
    )

    setSelected(detail)
  }

  return (
    <>
      <PageHeader
        eyebrow="ML audit trail"
        title="Classification History"
        description="Review stored production model predictions and their original feature values."
      />

      <section className="panel">
        <div className="toolbar">
          <div className="search-box">
            <span>⌕</span>
            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search Claim ID..."
            />
          </div>
        </div>

        {loading ? (
          <LoadingState />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No classifications found"
            description="Create a classification to see it here."
          />
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Claim ID</th>
                  <th>Prediction</th>
                  <th>Confidence</th>
                  <th>Model</th>
                  <th>Created</th>
                </tr>
              </thead>

              <tbody>
                {filtered.map((claim) => (
                  <tr
                    key={claim.id}
                    onClick={() =>
                      openClaim(claim.claim_id)
                    }
                  >
                    <td className="mono">
                      {claim.claim_id}
                    </td>
                    <td>
                      <StatusBadge
                        value={
                          claim.predicted_class
                        }
                      />
                    </td>
                    <td>
                      {(claim.confidence * 100)
                        .toFixed(2)}
                      %
                    </td>
                    <td>{claim.model_name}</td>
                    <td>
                      {formatDate(
                        claim.created_at
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected && (
        <section className="panel detail-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                Classification Detail
              </p>
              <h2>{selected.claim_id}</h2>
            </div>

            <StatusBadge
              value={selected.predicted_class}
            />
          </div>

          <div className="detail-grid">
            <div>
              <span>Prediction</span>
              <strong>
                {selected.predicted_class}
              </strong>
            </div>

            <div>
              <span>Confidence</span>
              <strong>
                {(selected.confidence * 100)
                  .toFixed(2)}
                %
              </strong>
            </div>

            <div>
              <span>Model</span>
              <strong>
                {selected.model_name}
              </strong>
            </div>

            <div>
              <span>Created</span>
              <strong>
                {formatDate(selected.created_at)}
              </strong>
            </div>
          </div>

          <div className="feature-grid">
            {Object.entries(
              selected.input_data || {}
            ).map(([key, value]) => (
              <div key={key}>
                <span>{key}</span>
                <strong>{String(value)}</strong>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  )
}


function parseCsvRows(csvText) {
  const rows = []
  const lines = csvText.trim().split(/\r?\n/)
  const headers = lines[0].split(',')

  for (let i = 1; i < lines.length; i += 1) {
    if (!lines[i].trim()) continue
    const values = lines[i].split(',')
    const row = {}
    headers.forEach((header, index) => {
      row[header.trim()] = (values[index] || '').trim()
    })
    rows.push(row)
  }

  return rows
}

function AdminAIML() {
  const [data, setData] = useState({
    rawCsv: null,
    audit: null,
    modelComparison: null,
    finalModel: null,
    gtm: null,
    googleValidation: null,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    Promise.all([
      api('/api/pipeline'),
      fetch(`${window.location.origin}/data/cleaned/assurex_v3_clean.csv`).then((response) => response.text()).catch(() => null),
    ])
      .then(([pipeline, rawCsv]) => {
        if (!active) return
        const valueFor = (rows, metric) => {
          const item = rows?.find((row) => row.Metric === metric)
          return item ? Number(item.Value) : null
        }
        const textMetrics = pipeline.reports?.text_test?.rows || []
        const imageMetrics = pipeline.reports?.image_test?.rows || []
        const selection = pipeline.selection || {}
        setData({
          rawCsv,
          audit: { ...pipeline.audit, selection: {
            feature_count: selection.selected_feature_count,
            selected_model: selection.selector_model,
            selection_basis: [selection.importance_method],
            validation_macro_f1: selection.final_validation_macro_f1,
            selected_features: selection.selected_features,
          } },
          modelComparison: pipeline.reports?.models?.rows || [],
          finalModel: { model: pipeline.active?.python_model?.name, test_metrics: {
            accuracy: valueFor(textMetrics, 'TestAccuracy'),
            macro_f1: valueFor(textMetrics, 'TestMacroF1'),
          } },
          gtm: { accuracy: valueFor(imageMetrics, 'Accuracy'), macro_f1: valueFor(imageMetrics, 'MacroF1'), correct: valueFor(imageMetrics, 'Correct'), incorrect: valueFor(imageMetrics, 'Incorrect'), status: pipeline.active?.google_model?.version || 'G2_V3' },
          googleValidation: null,
        })
      })
      .catch(() => {
        if (active) setError('Unable to load the repository ML evidence files.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [])

  const rawRows = data.rawCsv ? parseCsvRows(data.rawCsv) : []
  const parsedClassCounts = rawRows.reduce((accumulator, row) => {
    const label = row.ClaimClass || row.claimclass || 'Unknown'
    accumulator[label] = (accumulator[label] || 0) + 1
    return accumulator
  }, {})
  const classCounts = Object.keys(parsedClassCounts).length > 0 ? parsedClassCounts : (data.audit?.class_counts || {})

  const pythonMetrics = data.audit?.selection || {}
  const comparisonRows = data.modelComparison || []

  return (
    <>
      <PageHeader
        eyebrow="AI & ML evidence"
        title="AI & ML"
        description="Review the repository-backed data audit, preprocessing, model selection, and validation evidence only."
      />

      {loading ? (
        <LoadingState />
      ) : error ? (
        <div className="alert error">{error}</div>
      ) : (
        <>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">01 · Data Audit</p>
                <h2>Raw dataset and class balance</h2>
              </div>
            </div>

            <div className="stats-grid">
              <StatCard label="Rows" value={data.audit?.rows || rawRows.length || 'Not available'} hint="Clean training dataset" />
              <StatCard label="Columns" value={data.audit?.columns || (rawRows[0] ? Object.keys(rawRows[0]).length : 'Not available')} hint="Feature and metadata columns" />
              <StatCard label="Valid" value={classCounts['Valid Claim'] || 'Not available'} hint="Usable claim class" tone="success" />
              <StatCard label="Manual Review" value={classCounts['Manual Review'] || 'Not available'} hint="Human review class" tone="warning" />
              <StatCard label="Invalid" value={classCounts['Invalid Claim'] || 'Not available'} hint="Ineligible claim class" tone="danger" />
            </div>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">02 · Preprocessing</p>
                <h2>Feature engineering and selection evidence</h2>
              </div>
            </div>

            <div className="detail-grid">
              <div>
                <span>Model feature count</span>
                <strong>{pythonMetrics.feature_count || 'Not available'}</strong>
              </div>
              <div>
                <span>Selected model</span>
                <strong>{pythonMetrics.selected_model || 'Not available'}</strong>
              </div>
              <div>
                <span>Selection basis</span>
                <strong>{pythonMetrics.selection_basis?.join(', ') || 'Not available'}</strong>
              </div>
              <div>
                <span>Validation Macro F1</span>
                <strong>{pythonMetrics.validation_macro_f1 != null ? Number(pythonMetrics.validation_macro_f1).toFixed(6) : 'Not available'}</strong>
              </div>
            </div>

            <div className="feature-grid">
              {(pythonMetrics?.selected_features || []).map((feature) => (
                <div key={feature}><span>Feature</span><strong>{feature}</strong></div>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">03 · Python ML</p>
                <h2>Primary Python model evidence</h2>
              </div>
            </div>

            <div className="stats-grid">
              <StatCard label="Python Accuracy" value={data.finalModel?.test_metrics?.accuracy ? `${(data.finalModel.test_metrics.accuracy * 100).toFixed(2)}%` : 'Not available'} hint="Locked test metrics" />
              <StatCard label="Python Macro F1" value={data.finalModel?.test_metrics?.macro_f1 ? `${(data.finalModel.test_metrics.macro_f1 * 100).toFixed(2)}%` : 'Not available'} hint="Primary selection metric" />
              <StatCard label="Validation Macro F1" value={pythonMetrics.validation_macro_f1 != null ? Number(pythonMetrics.validation_macro_f1 * 100).toFixed(2) + '%' : 'Not available'} hint="Validation selection" />
              <StatCard label="Model" value={data.finalModel?.model || 'Not available'} hint="Final artifact name" />
            </div>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">04 · Google ML</p>
                <h2>Google GTM G2 V3 evidence</h2>
              </div>
            </div>

            <div className="stats-grid">
              <StatCard label="Accuracy" value={data.gtm?.accuracy != null ? `${(data.gtm.accuracy * 100).toFixed(2)}%` : 'Not available'} hint="Locked final test" />
              <StatCard label="Macro F1" value={data.gtm?.macro_f1 != null ? `${(data.gtm.macro_f1 * 100).toFixed(2)}%` : 'Not available'} hint="GTM final evaluation" />
              <StatCard label="Correct" value={data.gtm?.correct ?? 'Not available'} hint="Correct predictions" />
              <StatCard label="Incorrect" value={data.gtm?.incorrect ?? 'Not available'} hint="Incorrect predictions" />
            </div>

            <div className="detail-grid">
              <div>
                <span>Validation status</span>
                <strong>{data.googleValidation?.selection_eligible === false ? 'Not eligible for selection' : (data.googleValidation?.status || 'Not available')}</strong>
              </div>
              <div>
                <span>Validation F1</span>
                <strong>{data.googleValidation?.macro_f1 != null ? Number(data.googleValidation.macro_f1 * 100).toFixed(2) + '%' : 'Not available'}</strong>
              </div>
              <div>
                <span>Version</span>
                <strong>{data.googleValidation?.model_version || 'Not available'}</strong>
              </div>
              <div>
                <span>Inference status</span>
                <strong>{data.gtm?.status || 'Not available'}</strong>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">05 · Model Comparison</p>
                <h2>Selection ranking from model comparison artifact</h2>
              </div>
            </div>

            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Model</th>
                    <th>Validation Accuracy</th>
                    <th>Validation Macro F1</th>
                    <th>Selected features</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonRows.length > 0 ? comparisonRows.map((row) => (
                    <tr key={`${row.Model}-${row.Rank}`}>
                      <td>{row.Rank || comparisonRows.indexOf(row) + 1}</td>
                      <td>{row.Model || '—'}</td>
                      <td>{row.ValidationAccuracy != null ? Number(row.ValidationAccuracy * 100).toFixed(2) + '%' : '—'}</td>
                      <td>{row.ValidationMacroF1 != null ? Number(row.ValidationMacroF1 * 100).toFixed(2) + '%' : '—'}</td>
                      <td>{row.SelectedFeatureCount || '—'}</td>
                    </tr>
                  )) : <tr><td colSpan="5">Not available</td></tr>}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  )
}

function ModelInfo() {
  return (
    <>
      <PageHeader
        eyebrow="Model intelligence"
        title="Model Performance"
        description="Final locked-test comparison between the structured model and GTM G2 V3."
      />

      <section className="hero-card">
        <div>
          <p className="eyebrow">
            Final Selection
          </p>
          <h2>Gradient Boosting</h2>
          <p>
            Selected as the production primary model
            using Macro F1 as the pre-defined selection
            metric.
          </p>
        </div>

        <div className="metric-highlight">
          <span>Macro F1</span>
          <strong>
            {MODEL_METRICS.pythonF1}
          </strong>
          <small>Primary model</small>
        </div>
      </section>

      <section className="stats-grid">
        <StatCard
          label="Python Accuracy"
          value={MODEL_METRICS.pythonAccuracy}
          hint="223 / 225 correct"
          tone="success"
        />

        <StatCard
          label="Python Macro F1"
          value={MODEL_METRICS.pythonF1}
          hint="Primary selection metric"
        />

        <StatCard
          label="Mean Confidence"
          value={MODEL_METRICS.pythonConfidence}
          hint="Python final test"
        />

        <StatCard
          label="Test Errors"
          value="2"
          hint="Across 225 claims"
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">
              Final Comparison
            </p>
            <h2>Gradient Boosting vs Inception-v1</h2>
          </div>
        </div>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Gradient Boosting</th>
                <th>Inception-v1</th>
              </tr>
            </thead>

            <tbody>
              <tr>
                <td>Accuracy</td>
                <td>
                  {MODEL_METRICS.pythonAccuracy}
                </td>
                <td>
                  {MODEL_METRICS.gtmAccuracy}
                </td>
              </tr>

              <tr>
                <td>Macro F1</td>
                <td>
                  {MODEL_METRICS.pythonF1}
                </td>
                <td>{MODEL_METRICS.gtmF1}</td>
              </tr>

              <tr>
                <td>Precision</td>
                <td>99.13%</td>
                <td>87.52%</td>
              </tr>

              <tr>
                <td>Recall</td>
                <td>99.11%</td>
                <td>86.22%</td>
              </tr>

              <tr>
                <td>AUC-ROC</td>
                <td>{MODEL_METRICS.pythonAuc}</td>
                <td>{MODEL_METRICS.gtmAuc}</td>
              </tr>

              <tr>
                <td>Mean Confidence</td>
                <td>
                  {
                    MODEL_METRICS.pythonConfidence
                  }
                </td>
                <td>
                  {MODEL_METRICS.gtmConfidence}
                </td>
              </tr>

              <tr>
                <td>Total Errors</td>
                <td>2</td>
                <td>31</td>
              </tr>

              <tr>
                <td>Role</td>
                <td>Primary Model</td>
                <td>Secondary Model</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">
              GTM Feature Selection
            </p>
            <h2>G2 V3 Evaluation Summary</h2>
          </div>
        </div>

        <div className="split-info">
          <div>
            <span>Removed</span>
            <strong>
              Frozen model: G2_V3
            </strong>
          </div>

          <div>
            <span>Removal rolled back</span>
            <strong>
              Test set: 225 claims · 194 correct
            </strong>
          </div>
        </div>
      </section>
    </>
  )
}

function MLPipelinePage({ page, onNavigate }) {
  const steps = [
    ['ml-audit', '01', 'Audit', 'Raw data quality'],
    ['ml-preprocessing', '02', 'Preprocessing', 'Clean & split'],
    ['ml-text', '03', 'Tuning models', 'CV + tuning'],
    ['ml-image', '04', 'Image model', 'Google Net'],
    ['ml-compare', '05', 'Compare', 'Deploy winner'],
  ]
  const active = steps.find((s) => s[0] === page) || steps[0]
  const go = (key) => onNavigate(key)
  const metric = (label, value, hint, tone) => <StatCard label={label} value={value} hint={hint} tone={tone} />

  return <>
    <PageHeader eyebrow="Admin · ML Operations" title="ML Pipeline" description="Theo dõi toàn bộ vòng đời dữ liệu, huấn luyện, đánh giá và tái huấn luyện model cho hệ thống AssureX." />
    <div className="ml-stepper">
      {steps.map(([key, number, title, subtitle], index) => <button key={key} className={`ml-step ${page === key ? 'active' : ''}`} onClick={() => go(key)}><span>{number}</span><strong>{title}</strong><small>{subtitle}</small>{index < steps.length - 1 && <i>→</i>}</button>)}
    </div>
    <section className="panel ml-page-panel">
      <div className="panel-heading"><div><p className="eyebrow">{active[1]} · {active[3]}</p><h2>{active[2]}</h2></div><span className="pipeline-status">● Production pipeline synced</span></div>
      {page === 'ml-audit' && <>
        <p className="section-lead">Kiểm tra dataset ban đầu trước khi đưa vào xử lý: cấu trúc, chất lượng và mức độ cân bằng nhãn.</p>
        <div className="stats-grid">{metric('Rows', '1,500', 'Clean dataset records')}{metric('Columns', '64', 'Raw dataset fields')}{metric('Missing values', '900', 'Cells after cleaning', 'warning')}{metric('Duplicates removed', '45', 'From 1,545 raw rows', 'warning')}{metric('Data types', '9 / 55', 'Numeric / categorical')}</div>
        <div className="two-column"><div><h3>Data quality checklist</h3><div className="check-list"><div>✓ Schema & kiểu dữ liệu <b>64 columns</b></div><div>⚠ Missing value scan <b className="warn">900 cells</b></div><div>✓ Duplicate records <b>45 removed</b></div><div>✓ Class distribution <b>500 / class</b></div></div></div><div><h3>Class distribution</h3><div className="bar-chart"><div><span>Valid Claim</span><b style={{width:'33.33%'}}>33.33%</b></div><div><span>Manual Review</span><b style={{width:'33.33%'}}>33.33%</b></div><div><span>Invalid Claim</span><b style={{width:'33.33%'}}>33.33%</b></div></div></div></div>
      </>}
      {page === 'ml-preprocessing' && <>
        <p className="section-lead">Làm sạch, loại bỏ nhiễu/đa cộng tuyến, mã hóa và chuẩn hóa dữ liệu trước khi chia tập.</p>
        <div className="stats-grid">{metric('Input columns', '94', 'Engineered dataset')}{metric('Removed structural', '11', '94 → 83')}{metric('Selected out', '67', '81 → 14')}{metric('Final features', '14', 'v3 production model', 'success')}</div>
        <div className="two-column"><div><h3>Preprocessing flow</h3><div className="flow-list"><span>01 · Deduplicate & impute</span><span>02 · Drop noisy / leakage fields</span><span>03 · Correlation filter & VIF</span><span>04 · One-hot encode categories</span><span>05 · StandardScaler numeric values</span><span>06 · Train 70% · Val 15% · Test 15%</span></div></div><div><h3>Correlation matrix</h3><div className="correlation-grid">{[.92,.18,.34,.11,.76,.21,.09,.64,.27,.13,.18,.88,.16,.32,.12,.22].map((v,i)=><span key={i} style={{opacity:.25+v*.75,background:v>.8?'#ef6a5b':'#2f8f83'}} title={`r = ${v}`}>{v.toFixed(2)}</span>)}</div><small className="muted">Highlighted pairs vượt ngưỡng tương quan 0.85 được loại bỏ.</small></div></div>
      </>}
      {page === 'ml-text' && <>
        <p className="section-lead">Đánh giá 3 model trên dữ liệu text/structured với Stratified 5-fold CV, sau đó tuning hyperparameter và chốt model tốt nhất.</p>
        <div className="stats-grid">{metric('CV strategy', '5-fold', 'Stratified cross-validation')}{metric('Best model', 'Gradient Boosting', 'Selected by validation Macro F1', 'success')}{metric('Validation F1', '98.22%', 'Locked validation result')}{metric('Features retained', '14', 'Selected model features')}</div>
        <div className="table-wrapper"><table className="data-table"><thead><tr><th>Model</th><th>Validation Accuracy</th><th>Validation Macro F1</th><th>Selected features</th><th>Status</th></tr></thead><tbody><tr><td>Logistic Regression</td><td>96.00%</td><td>95.99%</td><td>14</td><td>Candidate</td></tr><tr><td>Random Forest</td><td>97.78%</td><td>97.77%</td><td>14</td><td>Candidate</td></tr><tr className="selected-row"><td><strong>Gradient Boosting</strong></td><td><strong>98.22%</strong></td><td><strong>98.22%</strong></td><td><strong>14</strong></td><td><span className="status-badge status-approved">Selected</span></td></tr></tbody></table></div>
        <div className="feature-importance"><h3>Feature importance · final dataset</h3>{[['FaultCovered',0.2916],['WarrantyRemainingDays',0.1721],['RequiredDocumentsComplete',0.1188],['MissingDocumentCount',0.0859],['ProductIdentityMatch',0.0509]].map(([x,value])=><div key={x}><span>{x}</span><b style={{width:`${value/0.2916*100}%`}}></b><em>{value.toFixed(4)}</em></div>)}</div>
      </>}
      {page === 'ml-image' && <>
        <p className="section-lead">Đánh giá hình ảnh bằng Inception-v1 với cùng quy trình split, 5-fold validation, tuning và feature review.</p>
        <div className="stats-grid">{metric('Test claims', '225', 'Locked G2 V3 test set')}{metric('Model', 'Inception-v1', 'GTM frozen artifact')}{metric('Macro F1', '86.10%', 'Final test set')}{metric('Test accuracy', '86.22%', '194 / 225 correct')}</div>
        <div className="two-column"><div><h3>Image pipeline</h3><div className="flow-list"><span>01 · Resize 224 × 224</span><span>02 · Normalize & augment</span><span>03 · Train / validation / test split</span><span>04 · Fine-tune Inception-v1</span><span>05 · Evaluate per-class metrics</span></div></div><div><h3>Per-class Recall — Inception-v1</h3><div className="image-class-grid"><div><strong>Valid Claim</strong><span>94.67%</span></div><div><strong>Manual Review</strong><span>66.67%</span></div><div><strong>Invalid Claim</strong><span>82.67%</span></div></div></div></div>
      </>}
      {page === 'ml-compare' && <>
        <p className="section-lead">So sánh model text và image trên cùng tiêu chí, chọn model production và đóng vòng phản hồi để retrain version mới.</p>
        <div className="compare-hero"><div><span>Production winner</span><h3>Gradient Boosting</h3><p>Được chọn làm model chính cho claim decision engine.</p></div><strong>99.11%<small>Macro F1</small></strong></div>
        <div className="table-wrapper"><table className="data-table"><thead><tr><th>Metric</th><th>Tuning · Gradient Boosting</th><th>Image · Inception-v1</th><th>Winner</th></tr></thead><tbody><tr><td>Accuracy</td><td>99.11%</td><td>86.22%</td><td>Tuning</td></tr><tr><td>F1-Score</td><td>99.11%</td><td>86.10%</td><td>Tuning</td></tr><tr><td>Precision</td><td>99.13%</td><td>87.52%</td><td>Tuning</td></tr><tr><td>Recall</td><td>99.11%</td><td>86.22%</td><td>Tuning</td></tr><tr><td>AUC-ROC</td><td>{MODEL_METRICS.pythonAuc}</td><td>{MODEL_METRICS.gtmAuc}</td><td>Tuning</td></tr><tr><td>Latency</td><td>Not reported</td><td>Not reported</td><td>—</td></tr></tbody></table></div>
        <div className="retrain-card"><div><h3>Feedback loop</h3><p>Customer claim → model prediction → reviewer decision → verified label → retrain model vNext.</p></div><button className="button primary">Start retraining review →</button></div>
      </>}
    </section>
  </>
}


function AdminUsers({ refreshKey }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    role: 'REVIEWER',
  })

  useEffect(() => {
    api('/api/auth/users')
      .then(setUsers)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [refreshKey])

  async function createUser(event) {
    event.preventDefault()
    setError('')
    try {
      const user = await api('/api/auth/users', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      setUsers((current) => [user, ...current])
      setForm({ username: '', email: '', password: '', role: 'REVIEWER' })
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  async function toggleUser(user) {
    try {
      const updated = await api(`/api/auth/users/${user.id}/active`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !user.is_active }),
      })
      setUsers((current) => current.map((item) =>
        item.id === user.id ? { ...item, ...updated } : item
      ))
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  return (
    <>
      <PageHeader eyebrow="Access control" title="Users" description="Manage workspace accounts and roles." />
      <form className="panel admin-user-form" onSubmit={createUser}>
        <div className="panel-heading"><h2>Create user</h2></div>
        <div className="form-grid">
          <label className="form-field"><span>Username</span><input value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} required minLength="3" /></label>
          <label className="form-field"><span>Email</span><input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required /></label>
          <label className="form-field"><span>Temporary password</span><input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required minLength="8" /></label>
          <label className="form-field"><span>Role</span><select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}><option value="CUSTOMER">CUSTOMER</option><option value="SERVICE_CENTER">SERVICE CENTER / STAFF</option><option value="REVIEWER">REVIEWER</option><option value="ADMIN">ADMIN</option></select></label>
        </div>
        {error && <div className="alert error">{error}</div>}
        <div className="form-actions"><button className="button primary">Create account</button></div>
      </form>
      <section className="panel">
        {loading ? <LoadingState /> : users.length === 0 ? <EmptyState title="No users" description="Accounts appear here." /> : (
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>User</th><th>Email</th><th>Role</th><th>Created</th><th>Status</th><th /></tr></thead><tbody>
            {users.map((user) => <tr key={user.id}><td>{user.username || '—'}</td><td>{user.email}</td><td>{user.role}</td><td>{formatDate(user.created_at)}</td><td>{user.is_active ? 'Active' : 'Inactive'}</td><td><button className="text-button" onClick={() => toggleUser(user)}>{user.is_active ? 'Deactivate' : 'Activate'}</button></td></tr>)}
          </tbody></table></div>
        )}
      </section>
    </>
  )
}


function AdminAuditLog({ refreshKey }) {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/api/audit')
      .then(setEntries)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [refreshKey])

  return (
    <>
      <PageHeader eyebrow="Accountability" title="Audit Logs" description="Recorded account, document, prediction and claim actions." />
      <section className="panel">
        {error && <div className="alert error">{error}</div>}
        {loading ? <LoadingState /> : entries.length === 0 ? <EmptyState title="No audit events" description="Recorded actions will appear here." /> : (
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Date</th><th>User</th><th>Role</th><th>Action</th><th>Resource</th><th>Result</th></tr></thead><tbody>
            {entries.map((entry) => <tr key={entry.id}><td>{formatDate(entry.date)}</td><td>{entry.user}</td><td>{entry.role}</td><td>{entry.action}</td><td>{entry.resource}{entry.resource_id ? ` · ${entry.resource_id}` : ''}</td><td>{entry.result}</td></tr>)}
          </tbody></table></div>
        )}
      </section>
    </>
  )
}


function WorkspaceNotifications({ refreshKey }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/api/notifications')
      .then(setItems)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [refreshKey])

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
      <PageHeader eyebrow="Workspace" title="Notifications" description="Claim review and account updates assigned to you." />
      <section className="panel">
        {error && <div className="alert error">{error}</div>}
        {loading ? <LoadingState /> : items.length === 0 ? <EmptyState title="No notifications" description="New assigned updates will appear here." /> : (
          <div className="compact-list">{items.map((item) => <div className="compact-row" key={item.id}><div><strong>{item.title}</strong><span>{item.message} · {formatDate(item.created_at)}</span></div>{!item.is_read && <button className="text-button" onClick={() => markRead(item)}>Mark read</button>}</div>)}</div>
        )}
      </section>
    </>
  )
}


function WorkspaceProfile({ email, role }) {
  return (
    <>
      <PageHeader eyebrow="Workspace account" title="Profile" description="Your account identity and assigned role." />
      <section className="panel detail-grid">
        <div><span>Username</span><strong>{email?.split('@')[0] || '—'}</strong></div>
        <div><span>Email</span><strong>{email || '—'}</strong></div>
        <div><span>Role</span><strong>{role || '—'}</strong></div>
      </section>
    </>
  )
}


function AdminProducts({ refreshKey }) {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('All')
  const [isAdding, setIsAdding] = useState(false)
  const [form, setForm] = useState({
    name: '',
    category: '',
    brand: '',
    model: '',
    warranty_months: '12',
  })

  useEffect(() => {
    setLoading(true)
    api('/api/products')
      .then(setProducts)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [refreshKey])

  const categories = useMemo(() => {
    const set = new Set(products.map((p) => p.category).filter(Boolean))
    return ['All', ...Array.from(set)]
  }, [products])

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return products.filter((p) => {
      const matchSearch =
        !term ||
        [p.product_code, p.name, p.brand, p.model, p.category].some((v) =>
          String(v || '').toLowerCase().includes(term)
        )
      const matchCat = categoryFilter === 'All' || p.category === categoryFilter
      return matchSearch && matchCat
    })
  }, [products, search, categoryFilter])

  const totalRegistered = useMemo(() => {
    return products.reduce((acc, p) => acc + (p.registered_customers || 0), 0)
  }, [products])

  const totalClaims = useMemo(() => {
    return products.reduce((acc, p) => acc + (p.active_claims || 0), 0)
  }, [products])

  const avgWarranty = useMemo(() => {
    if (products.length === 0) return 0
    const sum = products.reduce((acc, p) => acc + (p.warranty_months || 0), 0)
    return Math.round(sum / products.length)
  }, [products])

  async function createProduct(event) {
    event.preventDefault()
    setError('')
    setSuccess('')
    try {
      const product = await api('/api/products', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          warranty_months: Number(form.warranty_months),
        }),
      })
      setProducts((current) => [product, ...current])
      setSuccess(`Product "${product.name}" (${product.product_code}) added to catalog!`)
      setForm({ name: '', category: '', brand: '', model: '', warranty_months: '12' })
      setIsAdding(false)
      setTimeout(() => setSuccess(''), 4000)
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  function exportCatalog() {
    const columns = [
      ['product_code', 'Product Code'],
      ['name', 'Product Name'],
      ['category', 'Category'],
      ['brand', 'Brand'],
      ['model', 'Model'],
      ['warranty_months', 'Warranty Months'],
      ['registered_customers', 'Registered Customers'],
      ['active_claims', 'Active Claims'],
    ]
    const csv = [
      columns.map(([, label]) => csvValue(label)).join(','),
      ...filtered.map((prod) =>
        columns.map(([key]) => csvValue(prod[key])).join(',')
      ),
    ].join('\r\n')
    downloadFile('assurex-product-catalog.csv', `\uFEFF${csv}`, 'text/csv;charset=utf-8')
  }

  return (
    <>
      <PageHeader
        eyebrow="Catalog & Models"
        title="Products"
        description="Manage product lines, standard warranty terms, customer registration counts, and active claim volume."
        action={
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="button secondary"
              onClick={exportCatalog}
              disabled={filtered.length === 0}
            >
              Export Catalog CSV
            </button>
            <button
              className="button primary"
              onClick={() => setIsAdding((prev) => !prev)}
            >
              {isAdding ? 'Close Form' : '+ Add New Product'}
            </button>
          </div>
        }
      />

      <section className="stats-grid">
        <StatCard
          label="Catalog Models"
          value={products.length}
          hint="Active registered product lines"
        />
        <StatCard
          label="Registered Customer Units"
          value={totalRegistered}
          hint="Total customer products registered"
          tone="success"
        />
        <StatCard
          label="Active Claims in Queue"
          value={totalClaims}
          hint="Pending reviewer action across models"
          tone={totalClaims > 0 ? 'warning' : 'neutral'}
        />
        <StatCard
          label="Avg. Standard Warranty"
          value={`${avgWarranty} mo`}
          hint="Coverage duration standard"
        />
      </section>

      {success && <div className="alert success" style={{ marginBottom: '16px' }}>{success}</div>}
      {error && <div className="alert error" style={{ marginBottom: '16px' }}>{error}</div>}

      {isAdding && (
        <form className="panel" onSubmit={createProduct} style={{ marginBottom: '24px' }}>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Catalog Addition</p>
              <h2>Add Product Model</h2>
            </div>
            <button
              type="button"
              className="text-button"
              onClick={() => setIsAdding(false)}
            >
              Cancel
            </button>
          </div>

          <div className="form-grid">
            <label className="form-field">
              <span>Product Display Name</span>
              <input
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                placeholder="e.g. UltraBook Pro 15"
                required
              />
            </label>

            <label className="form-field">
              <span>Category</span>
              <input
                list="category-suggestions"
                value={form.category}
                onChange={(event) => setForm({ ...form, category: event.target.value })}
                placeholder="e.g. Laptop, Smartphone, Audio..."
                required
              />
              <datalist id="category-suggestions">
                <option value="Laptop" />
                <option value="Smartphone" />
                <option value="Tablet" />
                <option value="Smartwatch" />
                <option value="Audio" />
                <option value="Home Appliance" />
                <option value="Gaming Console" />
                <option value="Monitor" />
              </datalist>
            </label>

            <label className="form-field">
              <span>Brand</span>
              <input
                value={form.brand}
                onChange={(event) => setForm({ ...form, brand: event.target.value })}
                placeholder="e.g. AssureTech, Apex, Nova..."
                required
              />
            </label>

            <label className="form-field">
              <span>Model Number</span>
              <input
                value={form.model}
                onChange={(event) => setForm({ ...form, model: event.target.value })}
                placeholder="e.g. AT-UB15-2026"
                required
              />
            </label>

            <label className="form-field">
              <span>Standard Warranty (Months)</span>
              <input
                type="number"
                min="1"
                max="120"
                value={form.warranty_months}
                onChange={(event) => setForm({ ...form, warranty_months: event.target.value })}
                required
              />
            </label>
          </div>

          <div className="form-actions" style={{ marginTop: '16px' }}>
            <button className="button primary">Save Product Model</button>
          </div>
        </form>
      )}

      <section className="panel">
        <div className="toolbar" style={{ flexWrap: 'wrap', gap: '12px' }}>
          <div className="search-box" style={{ flex: '1 1 240px' }}>
            <span>⌕</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search product code, name, brand, model..."
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', opacity: 0.7 }}>Category:</span>
            <select
              className="filter-select"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              {categories.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          <span className="results-count">
            {filtered.length} product(s)
          </span>
        </div>

        {loading ? (
          <LoadingState />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No matching products"
            description="Add a product or adjust your search filter."
          />
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product Code</th>
                  <th>Product Name</th>
                  <th>Category</th>
                  <th>Brand</th>
                  <th>Model</th>
                  <th>Warranty</th>
                  <th>Registered Units</th>
                  <th>Active Claims</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((product) => (
                  <tr key={product.id}>
                    <td className="mono">
                      <strong>{product.product_code || `PRD-${product.id}`}</strong>
                    </td>
                    <td>
                      <strong>{product.name}</strong>
                    </td>
                    <td>
                      <span className="category-badge">{product.category}</span>
                    </td>
                    <td>{product.brand}</td>
                    <td className="mono">{product.model}</td>
                    <td>{product.warranty_months} months</td>
                    <td>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                        <span>👤</span> {product.registered_customers || 0}
                      </span>
                    </td>
                    <td>
                      {(product.active_claims || 0) > 0 ? (
                        <span className="days-left-badge expiring">
                          {product.active_claims} in review
                        </span>
                      ) : (
                        <span style={{ opacity: 0.6 }}>0</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}


function AdminWarranties({ refreshKey }) {
  const [warranties, setWarranties] = useState([])
  const [selectedWarranty, setSelectedWarranty] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [togglingId, setTogglingId] = useState(null)

  useEffect(() => {
    setLoading(true)
    api('/api/warranties')
      .then(setWarranties)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [refreshKey])

  const counts = useMemo(() => {
    const res = {
      All: warranties.length,
      Active: 0,
      'Approaching Expiry': 0,
      Expired: 0,
      Inactive: 0,
    }
    warranties.forEach((w) => {
      if (!w.is_active) {
        res.Inactive += 1
      } else if (w.status === 'Active') {
        res.Active += 1
      } else if (w.status === 'Approaching Expiry' || (w.remaining_days >= 0 && w.remaining_days <= 30)) {
        res['Approaching Expiry'] += 1
      } else if (w.status === 'Expired' || w.remaining_days < 0) {
        res.Expired += 1
      }
    })
    return res
  }, [warranties])

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return warranties.filter((w) => {
      const matchSearch =
        !term ||
        [
          w.warranty_code,
          w.customer_name,
          w.customer_email,
          w.product,
          w.product_code,
          w.brand,
          w.model,
          w.serial_number,
          w.retailer,
        ].some((v) => String(v || '').toLowerCase().includes(term))

      let matchStatus = true
      if (statusFilter === 'Active') {
        matchStatus = w.is_active && w.status === 'Active'
      } else if (statusFilter === 'Approaching Expiry') {
        matchStatus = w.is_active && (w.status === 'Approaching Expiry' || (w.remaining_days >= 0 && w.remaining_days <= 30))
      } else if (statusFilter === 'Expired') {
        matchStatus = w.status === 'Expired' || w.remaining_days < 0
      } else if (statusFilter === 'Inactive') {
        matchStatus = !w.is_active
      }

      return matchSearch && matchStatus
    })
  }, [warranties, search, statusFilter])

  async function toggleActive(warranty) {
    setError('')
    setTogglingId(warranty.id)
    try {
      const updated = await api(`/api/warranties/${warranty.id}/active`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !warranty.is_active }),
      })
      setWarranties((current) =>
        current.map((entry) =>
          entry.id === warranty.id ? { ...entry, ...updated } : entry
        )
      )
      if (selectedWarranty?.id === warranty.id) {
        setSelectedWarranty((prev) => ({ ...prev, ...updated }))
      }
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setTogglingId(null)
    }
  }

  function exportWarranties() {
    const columns = [
      ['warranty_code', 'Warranty Code'],
      ['customer_name', 'Customer'],
      ['customer_email', 'Email'],
      ['product', 'Product'],
      ['product_code', 'Product Code'],
      ['brand', 'Brand'],
      ['model', 'Model'],
      ['serial_number', 'Serial Number'],
      ['start_date', 'Start Date'],
      ['end_date', 'End Date'],
      ['remaining_days', 'Remaining Days'],
      ['status', 'Status'],
      ['warranty_provider', 'Provider'],
      ['is_active', 'Active'],
    ]
    const csv = [
      columns.map(([, label]) => csvValue(label)).join(','),
      ...filtered.map((w) =>
        columns.map(([key]) => csvValue(w[key])).join(',')
      ),
    ].join('\r\n')
    downloadFile('assurex-warranties.csv', `\uFEFF${csv}`, 'text/csv;charset=utf-8')
  }

  return (
    <>
      <PageHeader
        eyebrow="Policy & Coverage Records"
        title="Warranties"
        description="Monitor registered product warranties, remaining validity days, authorized service centers, and policy terms."
        action={
          <button
            className="button secondary"
            onClick={exportWarranties}
            disabled={filtered.length === 0}
          >
            Export Warranties CSV ({filtered.length})
          </button>
        }
      />

      <section className="stats-grid">
        <StatCard
          label="Total Policies"
          value={warranties.length}
          hint="All registered warranty policies"
        />
        <StatCard
          label="Active Coverage"
          value={counts.Active}
          hint="Under valid protection"
          tone="success"
        />
        <StatCard
          label="Expiring Soon (≤30d)"
          value={counts['Approaching Expiry']}
          hint="Renewal or checkup recommended"
          tone={counts['Approaching Expiry'] > 0 ? 'warning' : 'neutral'}
        />
        <StatCard
          label="Expired Warranties"
          value={counts.Expired}
          hint="Coverage duration elapsed"
          tone={counts.Expired > 0 ? 'danger' : 'neutral'}
        />
      </section>

      {error && <div className="alert error" style={{ marginBottom: '16px' }}>{error}</div>}

      <section className="panel">
        <div className="toolbar" style={{ flexWrap: 'wrap', gap: '12px' }}>
          <div className="search-box" style={{ flex: '1 1 260px' }}>
            <span>⌕</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search warranty code, customer, product, serial..."
            />
          </div>

          <div className="filter-tabs">
            {['All', 'Active', 'Approaching Expiry', 'Expired', 'Inactive'].map((tab) => (
              <button
                key={tab}
                type="button"
                className={`filter-tab ${statusFilter === tab ? 'active' : ''}`}
                onClick={() => setStatusFilter(tab)}
              >
                <span>{tab}</span>
                {counts[tab] !== undefined && (
                  <span className="filter-tab-count">{counts[tab]}</span>
                )}
              </button>
            ))}
          </div>

          <span className="results-count">
            {filtered.length} warranty record(s)
          </span>
        </div>

        {loading ? (
          <LoadingState />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No matching warranties"
            description="Try changing your search term or filter tab."
          />
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Warranty Code</th>
                  <th>Customer</th>
                  <th>Product</th>
                  <th>Serial Number</th>
                  <th>Coverage Window</th>
                  <th>Validity</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((warranty) => {
                  const rem = warranty.remaining_days ?? 0
                  return (
                    <tr
                      key={warranty.id}
                      className={selectedWarranty?.id === warranty.id ? 'selected-row' : ''}
                      onClick={() => setSelectedWarranty(warranty)}
                    >
                      <td className="mono">
                        <strong>{warranty.warranty_code || `WAR-${warranty.id}`}</strong>
                      </td>
                      <td>
                        <strong>{warranty.customer_name}</strong>
                        <small>{warranty.customer_email}</small>
                      </td>
                      <td>
                        <div>{warranty.product}</div>
                        <small style={{ opacity: 0.7 }}>{warranty.brand} · {warranty.model}</small>
                      </td>
                      <td className="mono">{warranty.serial_number}</td>
                      <td>
                        <span style={{ fontSize: '12px' }}>
                          {warranty.start_date} → {warranty.end_date}
                        </span>
                      </td>
                      <td>
                        {rem < 0 ? (
                          <span className="days-left-badge expired">
                            Expired ({Math.abs(rem)}d ago)
                          </span>
                        ) : rem <= 30 ? (
                          <span className="days-left-badge expiring">
                            ⚠️ {rem} days left
                          </span>
                        ) : (
                          <span className="days-left-badge active">
                            ✓ {rem} days left
                          </span>
                        )}
                      </td>
                      <td>
                        {!warranty.is_active ? (
                          <span className="days-left-badge expired">Deactivated</span>
                        ) : (
                          <StatusBadge value={warranty.status} />
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '6px' }} onClick={(e) => e.stopPropagation()}>
                          <button
                            className="button secondary"
                            style={{ padding: '3px 8px', fontSize: '11.5px' }}
                            onClick={() => setSelectedWarranty(warranty)}
                          >
                            Details
                          </button>
                          <button
                            className="text-button"
                            style={{
                              fontSize: '11.5px',
                              color: warranty.is_active ? 'var(--ax-danger, #ef4444)' : 'var(--ax-success, #22c55e)',
                            }}
                            disabled={togglingId === warranty.id}
                            onClick={() => toggleActive(warranty)}
                          >
                            {togglingId === warranty.id ? '...' : warranty.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Selected Warranty Policy Drawer */}
      {selectedWarranty && (
        <section className="panel detail-panel" style={{ marginTop: '24px' }}>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Warranty Policy Specifications</p>
              <h2>{selectedWarranty.warranty_code || `WAR-${selectedWarranty.id}`}</h2>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <StatusBadge value={selectedWarranty.is_active ? selectedWarranty.status : 'Inactive'} />
              <button
                className="button secondary"
                onClick={() => setSelectedWarranty(null)}
              >
                Close ✕
              </button>
            </div>
          </div>

          <div className="detail-grid">
            <div>
              <span>Customer</span>
              <strong>{selectedWarranty.customer_name}</strong>
            </div>

            <div>
              <span>Email</span>
              <strong>{selectedWarranty.customer_email}</strong>
            </div>

            <div>
              <span>Product & Code</span>
              <strong>{selectedWarranty.product} ({selectedWarranty.product_code || 'PRD'})</strong>
            </div>

            <div>
              <span>Serial Number</span>
              <strong className="mono">{selectedWarranty.serial_number}</strong>
            </div>

            <div>
              <span>Purchase Date & Retailer</span>
              <strong>{selectedWarranty.purchase_date} · {selectedWarranty.retailer || 'Authorized Dealer'}</strong>
            </div>

            <div>
              <span>Purchase Price</span>
              <strong>{selectedWarranty.purchase_price ? `$${selectedWarranty.purchase_price}` : '—'}</strong>
            </div>

            <div>
              <span>Effective Duration</span>
              <strong>{selectedWarranty.start_date} to {selectedWarranty.end_date}</strong>
            </div>

            <div>
              <span>Remaining Coverage</span>
              <strong>
                {selectedWarranty.remaining_days < 0
                  ? `Expired ${Math.abs(selectedWarranty.remaining_days)} days ago`
                  : `${selectedWarranty.remaining_days} days remaining`}
              </strong>
            </div>

            <div>
              <span>Warranty Provider</span>
              <strong>{selectedWarranty.warranty_provider || 'AssureX Official Care'}</strong>
            </div>

            <div>
              <span>Warranty Plan Type</span>
              <strong>{selectedWarranty.warranty_type || 'Standard Factory Warranty'}</strong>
            </div>
          </div>

          <div style={{ marginTop: '16px', background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
            <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.7, fontWeight: 700 }}>
              Authorized Service Center
            </span>
            <p style={{ margin: '6px 0 0', fontSize: '13px', lineHeight: 1.5 }}>
              {selectedWarranty.service_center_details || 'AssureX Central Authorized Center, 123 Tech Park Blvd (Hotline: 1800-ASSUREX)'}
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px', marginTop: '14px' }}>
            <div className="description-box" style={{ margin: 0 }}>
              <span>Coverage Conditions</span>
              <p>{selectedWarranty.coverage_conditions || 'Covers manufacturing defects, internal component failures, and electrical faults under normal operating conditions.'}</p>
            </div>

            <div className="description-box" style={{ margin: 0 }}>
              <span>Policy Exclusions</span>
              <p>{selectedWarranty.exclusions || 'Damage caused by accidents, liquid intrusion, unauthorized disassembly, or physical abuse.'}</p>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '12px' }}>
            <button
              className={`button ${selectedWarranty.is_active ? 'danger' : 'success'}`}
              disabled={togglingId === selectedWarranty.id}
              onClick={() => toggleActive(selectedWarranty)}
            >
              {selectedWarranty.is_active ? 'Deactivate Warranty Policy' : 'Activate Warranty Policy'}
            </button>

            <button
              className="button secondary"
              onClick={() => setSelectedWarranty(null)}
            >
              Done Viewing
            </button>
          </div>
        </section>
      )}
    </>
  )
}


function CustomerIdentity({
  email,
  onChange,
}) {
  return (
    <div className="customer-identity">
      <div>
        <span>Customer account</span>
        <strong>
          {email || 'Enter your email'}
        </strong>
      </div>

      <input
        type="email"
        value={email}
        onChange={(event) =>
          onChange(event.target.value)
        }
        placeholder="your@email.com"
      />
    </div>
  )
}


function CustomerHome({
  email,
  setEmail,
  onNavigate,
  refreshKey,
  hideIdentity,
}) {
  const [claims, setClaims] = useState([])
  const [loading, setLoading] = useState(Boolean(email))

  useEffect(() => {
    if (!email) {
      setClaims([])
      setLoading(false)
      return
    }

    setLoading(true)

    api(
      `/api/customer/claims?email=${encodeURIComponent(
        email
      )}`
    )
      .then(setClaims)
      .finally(() => setLoading(false))
  }, [email, refreshKey])

  const review = claims.filter(
    (claim) => ['Under Review', 'Manual Review'].includes(claim.status)
  ).length

  const approved = claims.filter(
    (claim) => claim.status === 'Approved'
  ).length

  const rejected = claims.filter(
    (claim) => claim.status === 'Rejected'
  ).length

  return (
    <>
      <PageHeader
        eyebrow="AssureX Customer Portal"
        title="Warranty Claims"
      />

      {!hideIdentity && (
        <CustomerIdentity
          email={email}
          onChange={setEmail}
        />
      )}

      <section className="customer-hero">
        <div>
          <p className="eyebrow">
            Customer Warranty Service
          </p>
          <h2>
            Everything about your claim in one place.
          </h2>
        </div>

        <button
          className="button primary large"
          onClick={() => onNavigate('submit')}
        >
          Submit Warranty Claim
        </button>
      </section>

      {loading ? (
        <LoadingState />
      ) : (
        <>
          <section className="stats-grid">
            <StatCard
              label="My Claims"
              value={claims.length}
              hint="Total submitted"
            />

            <StatCard
              label="Under Review"
              value={review}
              hint="Currently being reviewed"
              tone="warning"
            />

            <StatCard
              label="Approved"
              value={approved}
              hint="Approved warranty claims"
              tone="success"
            />

            <StatCard
              label="Rejected"
              value={rejected}
              hint="Rejected claims"
              tone="danger"
            />
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">
                  Recent Activity
                </p>
                <h2>My Recent Claims</h2>
              </div>

              <button
                className="text-button"
                onClick={() =>
                  onNavigate('my-claims')
                }
              >
                View all →
              </button>
            </div>

            {!email ? (
              <EmptyState
                title="Sign in to view your claims"
                description="Log in or create an account to track claims linked to your account."
              />
            ) : claims.length === 0 ? (
              <EmptyState
                title="No claims found"
                description="Submit your first warranty claim to get started."
              />
            ) : (
              <div className="compact-list">
                {claims.slice(0, 5).map((claim) => (
                  <button
                    type="button"
                    className="compact-row row-button"
                    key={claim.id}
                    onClick={() => onNavigate('my-claims', claim.claim_id)}
                  >
                    <div>
                      <strong>
                        {claim.claim_id}
                      </strong>
                      <span>
                        {claim.product_name}
                        {' · '}
                        {formatDate(
                          claim.created_at
                        )}
                      </span>
                    </div>

                    <StatusBadge
                      value={claim.status}
                    />
                  </button>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </>
  )
}


function CustomerSubmit({
  email,
  customerName = '',
  setEmail,
  onSubmitted,
  onNavigate,
}) {
  return (
    <CustomerWarrantyClaimForm
      onCreated={() => {
        if (onSubmitted) onSubmitted()
      }}
      onCancel={() => {
        if (onNavigate) onNavigate('home')
      }}
    />
  )
  const [form, setForm] = useState({
    customer_name: customerName || '',
    email: email || '',

    product_name: '',
    model_number: '',
    serial_number: '',
    purchase_date: '',
    warranty_duration_months: '',

    fault_date: '',
    damage_type: '',
    claim_amount: '',
    fault_description: '',

    receipt_available: '',
    product_image_available: '',
    fault_evidence_available: '',

    previous_repair: 'No',
    repair_count: '0',
    repair_report_available: '',
    repair_authorized: '',

    previous_repair_date: '',
    repair_center_name: '',
    replaced_parts: '',
    repair_outcome: 'Fully Resolved',
    repair_cost: '',
  })

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const [warrantyDocument, setWarrantyDocument] = useState(null)
  const [ocrOriginal, setOcrOriginal] = useState(null)
  const [ocrUploading, setOcrUploading] = useState(false)
  const [ocrError, setOcrError] = useState('')
  const [registeredProducts, setRegisteredProducts] = useState([])
  const [selectedProductId, setSelectedProductId] = useState('')

  // Evidence files state with SHA-256 integrity
  const [evidenceFiles, setEvidenceFiles] = useState({
    receipt: null,
    product_image: null,
    fault_evidence: null,
    repair_report: null,
  })
  const [uploadingDoc, setUploadingDoc] = useState('')
  const [uploadError, setUploadError] = useState('')
  const [draftMessage, setDraftMessage] = useState('')
  const [hasDraft, setHasDraft] = useState(false)

  const DRAFT_STORAGE_KEY = 'assurex_claim_draft'

  useEffect(() => {
    try {
      const raw = localStorage.getItem(DRAFT_STORAGE_KEY)
      if (raw) {
        setHasDraft(true)
      }
    } catch {
      // ignore
    }
  }, [])

  function saveDraft() {
    try {
      const draft = {
        form,
        evidenceFiles,
        warrantyDocument,
        ocrOriginal,
        selectedProductId,
        savedAt: new Date().toISOString(),
      }
      localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft))
      setHasDraft(true)
      setDraftMessage(`Draft saved successfully at ${new Date().toLocaleTimeString()}!`)
      setTimeout(() => setDraftMessage(''), 4000)
    } catch (e) {
      setError(`Failed to save draft: ${e.message}`)
    }
  }

  function resumeDraft() {
    try {
      const raw = localStorage.getItem(DRAFT_STORAGE_KEY)
      if (!raw) return
      const draft = JSON.parse(raw)
      if (draft.form) setForm(draft.form)
      if (draft.evidenceFiles) setEvidenceFiles(draft.evidenceFiles)
      if (draft.warrantyDocument) setWarrantyDocument(draft.warrantyDocument)
      if (draft.ocrOriginal) setOcrOriginal(draft.ocrOriginal)
      if (draft.selectedProductId) setSelectedProductId(draft.selectedProductId)
      setDraftMessage('Draft restored successfully!')
      setHasDraft(false)
      setTimeout(() => setDraftMessage(''), 4000)
    } catch (e) {
      setError(`Failed to resume draft: ${e.message}`)
    }
  }

  function discardDraft() {
    try {
      localStorage.removeItem(DRAFT_STORAGE_KEY)
      setHasDraft(false)
      setDraftMessage('Draft discarded.')
      setTimeout(() => setDraftMessage(''), 3000)
    } catch {
      // ignore
    }
  }

  async function handleFileUpload(event, docType) {
    const file = event.target.files?.[0]
    if (!file) return

    setUploadingDoc(docType)
    setUploadError('')

    try {
      const body = new FormData()
      body.append('file', file)
      body.append('document_type', docType)

      const data = await api('/api/customer/evidence/upload', {
        method: 'POST',
        body,
      })

      setEvidenceFiles((curr) => ({
        ...curr,
        [docType]: {
          filename: data.filename,
          file_url: data.file_url,
          sha256: data.sha256,
          file_size: data.file_size,
        },
      }))

      if (docType === 'receipt') setForm((f) => ({ ...f, receipt_available: 'Yes' }))
      if (docType === 'product_image') setForm((f) => ({ ...f, product_image_available: 'Yes' }))
      if (docType === 'fault_evidence') setForm((f) => ({ ...f, fault_evidence_available: 'Yes' }))
      if (docType === 'repair_report') setForm((f) => ({ ...f, repair_report_available: 'Yes' }))
    } catch (err) {
      setUploadError(`Failed to upload ${docType.replace('_', ' ')}: ${err.message}`)
    } finally {
      setUploadingDoc('')
    }
  }

  function removeEvidenceFile(docType) {
    setEvidenceFiles((curr) => ({
      ...curr,
      [docType]: null,
    }))
    if (docType === 'receipt') setForm((f) => ({ ...f, receipt_available: 'No' }))
    if (docType === 'product_image') setForm((f) => ({ ...f, product_image_available: 'No' }))
    if (docType === 'fault_evidence') setForm((f) => ({ ...f, fault_evidence_available: 'No' }))
    if (docType === 'repair_report') setForm((f) => ({ ...f, repair_report_available: 'No' }))
  }

  useEffect(() => {
    if (customerName && !form.customer_name) {
      setForm((current) => ({ ...current, customer_name: customerName }))
    }
  }, [customerName])

  useEffect(() => {
    if (!email) return
    let active = true
    api('/api/products/registered')
      .then((products) => {
        if (active) setRegisteredProducts(products)
      })
      .catch(() => {
        if (active) setRegisteredProducts([])
      })
    return () => {
      active = false
    }
  }, [email])

  const missingInformation = [
    ['Full name', form.customer_name],
    ['Email address', form.email],
    ['Product', form.product_name],
    ['Model number', form.model_number],
    ['Serial number', form.serial_number],
    ['Purchase date', form.purchase_date],
    ['Warranty duration', form.warranty_duration_months],
    ['Fault type', form.damage_type],
    ['Issue details', form.fault_description],
  ]
    .filter(([, value]) => !String(value || '').trim())
    .map(([label]) => label)

  const missingDocuments = [
    !evidenceFiles.receipt && form.receipt_available !== 'Yes' ? 'Receipt' : null,
    !warrantyDocument ? 'Warranty card' : null,
    !evidenceFiles.product_image && form.product_image_available !== 'Yes' ? 'Product image' : null,
    !ocrOriginal?.serial_number ? 'Serial evidence' : null,
    !evidenceFiles.fault_evidence && form.fault_evidence_available !== 'Yes' ? 'Fault evidence' : null,
    form.previous_repair === 'Yes' && !evidenceFiles.repair_report && form.repair_report_available !== 'Yes'
      ? 'Repair report'
      : null,
  ].filter(Boolean)

  function change(event) {
    const { name, value } = event.target

    setForm((current) => ({
      ...current,
      [name]: value,
    }))
  }

  function selectRegisteredProduct(event) {
    const productId = event.target.value
    setSelectedProductId(productId)
    const product = registeredProducts.find(
      (item) => String(item.id) === productId
    )
    if (!product) return
    setForm((current) => ({
      ...current,
      product_name: product.name,
      model_number: product.model,
      serial_number: product.serial_number,
      purchase_date: product.purchase_date,
      warranty_duration_months: String(product.warranty_months),
    }))
  }

  async function uploadWarranty(event) {
    const file =
      event.target.files?.[0]

    if (!file) return

    setOcrUploading(true)
    setOcrError('')

    try {
      const body = new FormData()

      body.append(
        'file',
        file
      )

      const data = await api(
        '/api/customer/warranty/extract',
        {
          method: 'POST',
          body,
        }
      )

      const extracted =
        data.extracted_data || {}

      setOcrOriginal(extracted)

      setWarrantyDocument({
        document_id:
          data.document_id,

        filename:
          data.filename,

        ocr_confidence:
          data.ocr_confidence,

        sha256: data.sha256,
        file_url: data.file_url,
      })

      setForm((current) => ({
        ...current,

        customer_name:
          extracted.customer_name ||
          current.customer_name,

        email:
          extracted.email ||
          current.email,

        product_name:
          extracted.product_name ||
          current.product_name,

        model_number:
          extracted.model_number ||
          current.model_number,

        serial_number:
          extracted.serial_number ||
          current.serial_number,

        purchase_date:
          extracted.purchase_date ||
          current.purchase_date,

        warranty_duration_months:
          extracted.warranty_duration_months
            ? String(
                extracted
                  .warranty_duration_months
              )
            : current
                .warranty_duration_months,
      }))
    } catch (err) {
      setOcrError(err.message)
    } finally {
      setOcrUploading(false)
    }
  }

  function normalizeCompare(value) {
    return String(
      value ?? ''
    )
      .trim()
      .toLowerCase()
  }

  function changedFromWarranty(field) {
    if (!ocrOriginal) {
      return false
    }

    const original =
      ocrOriginal[field]

    if (
      original === null ||
      original === undefined ||
      original === ''
    ) {
      return false
    }

    return (
      normalizeCompare(original) !==
      normalizeCompare(form[field])
    )
  }

  async function submit(event) {
    event.preventDefault()

    setSubmitting(true)
    setError('')
    setResult(null)

    try {
      const previousRepair = form.previous_repair

      const document_hashes = {}
      if (evidenceFiles.receipt?.sha256) document_hashes.receipt = evidenceFiles.receipt.sha256
      if (evidenceFiles.product_image?.sha256) document_hashes.product_image = evidenceFiles.product_image.sha256
      if (evidenceFiles.fault_evidence?.sha256) document_hashes.fault_evidence = evidenceFiles.fault_evidence.sha256
      if (evidenceFiles.repair_report?.sha256) document_hashes.repair_report = evidenceFiles.repair_report.sha256
      if (warrantyDocument?.sha256) document_hashes.warranty_card = warrantyDocument.sha256

      const payload = {
        customer_name: form.customer_name,
        email: form.email,
        product_name: form.product_name,
        model_number: form.model_number,
        serial_number: form.serial_number,
        purchase_date: form.purchase_date,
        fault_date: form.fault_date || null,
        damage_type: form.damage_type,
        claim_amount: form.claim_amount ? Number(form.claim_amount) : null,
        fault_description: form.fault_description,
        warranty_duration_months: form.warranty_duration_months
          ? Number(form.warranty_duration_months)
          : null,
        extended_warranty: 'No',
        receipt_available: form.receipt_available || (evidenceFiles.receipt ? 'Yes' : 'No'),
        warranty_card_available: warrantyDocument ? 'Yes' : 'No',
        product_image_available: form.product_image_available || (evidenceFiles.product_image ? 'Yes' : 'No'),
        serial_evidence_available: ocrOriginal?.serial_number ? 'Yes' : 'No',
        fault_evidence_available: form.fault_evidence_available || (evidenceFiles.fault_evidence ? 'Yes' : 'No'),
        evidence_serial_number: ocrOriginal?.serial_number || null,
        evidence_model_number: ocrOriginal?.model_number || null,
        previous_repair: previousRepair,
        repair_count: previousRepair === 'Yes' ? Number(form.repair_count || 0) : 0,
        repair_report_available: previousRepair === 'Yes'
          ? (form.repair_report_available || (evidenceFiles.repair_report ? 'Yes' : 'No'))
          : 'Not Applicable',
        repair_authorized: previousRepair === 'Yes' ? form.repair_authorized : 'Not Applicable',
        ocr_confidence: warrantyDocument?.ocr_confidence ?? null,
        document_duplicate_indicator: 'No',
        warranty_document_id: warrantyDocument?.document_id || null,
        warranty_ocr_data: ocrOriginal,
        warranty_ocr_confidence: warrantyDocument?.ocr_confidence ?? null,
        receipt_url: evidenceFiles.receipt?.file_url || null,
        product_image_url: evidenceFiles.product_image?.file_url || null,
        evidence_photo_url: evidenceFiles.fault_evidence?.file_url || null,
        repair_report_url: evidenceFiles.repair_report?.file_url || null,
        document_hashes: document_hashes,
        previous_repair_date: previousRepair === 'Yes' ? (form.previous_repair_date || null) : null,
        repair_center_name: previousRepair === 'Yes' ? (form.repair_center_name || null) : null,
        replaced_parts: previousRepair === 'Yes' ? (form.replaced_parts || null) : null,
        repair_outcome: previousRepair === 'Yes' ? (form.repair_outcome || null) : null,
        repair_cost: previousRepair === 'Yes' && form.repair_cost ? Number(form.repair_cost) : null,
      }

      const data = await api(
        '/api/customer/claims',
        {
          method: 'POST',
          body: JSON.stringify(payload),
        }
      )

      try {
        localStorage.removeItem(DRAFT_STORAGE_KEY)
      } catch {
        // ignore
      }

      setResult(data)
      setEmail(form.email)
      onSubmitted()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  function decisionMessage() {
    if (!result) return ''

    if (result.status === 'Approved') {
      return (
        'Your claim passed the automated ' +
        'warranty assessment and has been approved.'
      )
    }

    if (result.status === 'Rejected') {
      return (
        'The automated assessment identified ' +
        'one or more conditions that make this ' +
        'claim ineligible.'
      )
    }

    return (
      'Your claim requires additional review. ' +
      'It has been sent to the warranty team.'
    )
  }

  if (result) {
    const decision = result.decision

    return (
      <>
        <PageHeader
          eyebrow="Claim submitted"
          title="Submission Complete"
          description="Your warranty claim has been evaluated and recorded."
        />

        <section className="success-card decision-success-card">
          <div
            className={`decision-mark ${
              result.status === 'Approved'
                ? 'approved'
                : result.status === 'Rejected'
                  ? 'rejected'
                  : 'review'
            }`}
          >
            {result.status === 'Approved'
              ? '✓'
              : result.status === 'Rejected'
                ? '×'
                : '…'}
          </div>

          <p className="eyebrow">
            Claim ID
          </p>

          <h2>{result.claim_id}</h2>

          <StatusBadge
            value={result.status}
          />

          <p className="decision-message">
            {decisionMessage()}
          </p>

          {decision && (
            <div className="decision-summary-grid">
              <div>
                <span>
                  AI Classification
                </span>

                <strong>
                  {decision.final_decision}
                </strong>
              </div>

              <div>
                <span>Confidence</span>

                <strong>
                  {(
                    decision.ml_confidence *
                    100
                  ).toFixed(2)}
                  %
                </strong>
              </div>

              <div>
                <span>Processing</span>

                <strong>
                  {
                    decision
                      .requires_admin_review
                      ? 'Manual Review'
                      : 'Automatic'
                  }
                </strong>
              </div>
              <div>
                <span>Google inference</span>
                <strong>
                  {decision.google_inference_status === 'not_connected'
                    ? 'Not connected'
                    : decision.google_prediction || 'Not run'}
                </strong>
              </div>
            </div>
          )}

          {decision
            ?.decision_reasons
            ?.length > 0 && (
            <div className="decision-reasons">
              <span>
                Assessment notes
              </span>

              <ul>
                {
                  decision
                    .decision_reasons
                    .map((reason) => (
                      <li key={reason}>
                        {reason}
                      </li>
                    ))
                }
              </ul>
            </div>
          )}

          <div className="success-actions">
            <button
              className="button primary"
              onClick={() =>
                onNavigate('my-claims')
              }
            >
              View My Claims
            </button>

            <button
              className="button secondary"
              onClick={() =>
                onNavigate('home')
              }
            >
              Customer Home
            </button>
          </div>
        </section>
      </>
    )
  }

  const yesNoOptions = [
    'Yes',
    'No',
  ]

  return (
    <>
      <PageHeader
        eyebrow="AssureX Customer Portal"
        title="Submit a Warranty Claim"
        description="Upload your warranty card and provide only the information needed to assess your claim."
      />

      {hasDraft && (
        <div className="draft-banner">
          <div>
            <strong>Unfinished Claim Draft Found</strong>
            <p style={{ margin: '2px 0 0', fontSize: '13px' }}>
              You have an unsaved claim draft from your previous session. Would you like to resume?
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              type="button"
              className="button primary"
              style={{ padding: '6px 12px', fontSize: '13px' }}
              onClick={resumeDraft}
            >
              Resume Draft
            </button>
            <button
              type="button"
              className="button secondary"
              style={{ padding: '6px 12px', fontSize: '13px' }}
              onClick={discardDraft}
            >
              Discard
            </button>
          </div>
        </div>
      )}

      {draftMessage && (
        <div className="alert success" style={{ marginBottom: '16px' }}>
          {draftMessage}
        </div>
      )}

      <form
        className="claim-form"
        onSubmit={submit}
      >
        <section className="panel warranty-upload-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                Start here
              </p>

              <h2>
                Upload Warranty Card
              </h2>

              <p className="section-helper">
                Upload a clear photo. AssureX
                will read the warranty details
                and fill the form automatically.
              </p>
            </div>
          </div>

          <label className="warranty-upload-box">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={uploadWarranty}
              disabled={ocrUploading}
            />

            <strong>
              {ocrUploading
                ? 'Reading warranty card...'
                : 'Choose Warranty Card'}
            </strong>

            <span>
              JPG, PNG or WEBP · Max 8 MB
            </span>
          </label>

          {ocrError && (
            <div className="alert error">
              {ocrError}
            </div>
          )}

          {warrantyDocument && (
            <>
              <div className="ocr-success">
                <div>
                  <strong>
                    ✓ Warranty card processed
                  </strong>

                  <span>
                    {
                      warrantyDocument
                        .filename
                    }
                  </span>
                </div>

                <div>
                  OCR confidence:{' '}
                  {(
                    warrantyDocument
                      .ocr_confidence *
                    100
                  ).toFixed(1)}
                  %
                </div>
              </div>

              {ocrOriginal && (
                <details
                  className="evidence-verification"
                  style={{
                    marginTop: '16px',
                  }}
                >
                  <summary
                    style={{
                      cursor: 'pointer',
                      fontWeight: 700,
                    }}
                  >
                    View extracted warranty
                    information
                  </summary>

                  <div
                    className="detail-grid"
                    style={{
                      marginTop: '16px',
                    }}
                  >
                    <div>
                      <span>
                        Warranty Number
                      </span>
                      <strong>
                        {
                          ocrOriginal
                            .warranty_number ||
                          '—'
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Customer
                      </span>
                      <strong>
                        {
                          ocrOriginal
                            .customer_name ||
                          '—'
                        }
                      </strong>
                    </div>

                    <div>
                      <span>Phone</span>
                      <strong>
                        {
                          ocrOriginal
                            .phone_number ||
                          '—'
                        }
                      </strong>
                    </div>

                    <div>
                      <span>Email</span>
                      <strong>
                        {
                          ocrOriginal
                            .email ||
                          '—'
                        }
                      </strong>
                    </div>

                    <div>
                      <span>Product</span>
                      <strong>
                        {
                          ocrOriginal
                            .product_name ||
                          '—'
                        }
                      </strong>
                    </div>

                    <div>
                      <span>Model</span>
                      <strong>
                        {
                          ocrOriginal
                            .model_number ||
                          '—'
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Serial Number
                      </span>
                      <strong>
                        {
                          ocrOriginal
                            .serial_number ||
                          '—'
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Purchase Date
                      </span>
                      <strong>
                        {
                          ocrOriginal
                            .purchase_date ||
                          '—'
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Warranty Duration
                      </span>
                      <strong>
                        {
                          ocrOriginal
                            .warranty_duration_months
                            ? `${
                                ocrOriginal
                                  .warranty_duration_months
                              } months`
                            : '—'
                        }
                      </strong>
                    </div>

                    <div>
                      <span>Dealer</span>
                      <strong>
                        {
                          ocrOriginal
                            .dealer_name ||
                          '—'
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Dealer Address
                      </span>
                      <strong>
                        {
                          ocrOriginal
                            .dealer_address ||
                          '—'
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Warranty Status
                      </span>
                      <strong>
                        {
                          ocrOriginal
                            .warranty_status ||
                          '—'
                        }
                      </strong>
                    </div>
                  </div>
                </details>
              )}
            </>
          )}
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                Step 1
              </p>

              <h2>
                Contact & Warranty
              </h2>

              <p className="section-helper">
                Review the information extracted
                from your warranty card and
                correct it only if necessary.
              </p>
            </div>
          </div>

          <div className="form-grid">
            <label className="form-field full-width">
              <span>Select Product</span>
              <select value={selectedProductId} onChange={selectRegisteredProduct}>
                <option value="">Enter product details manually</option>
                {registeredProducts.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name} · {product.model} · {product.serial_number}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field">
              <span>Full Name</span>

              <input
                name="customer_name"
                value={
                  form.customer_name
                }
                onChange={change}
                placeholder="Your full name"
                required
              />
            </label>

            <label className="form-field">
              <span>Email Address</span>

              <input
                type="email"
                name="email"
                value={form.email}
                onChange={change}
                placeholder="you@example.com"
                required
              />
            </label>

            <label className="form-field">
              <span>Product Name</span>

              <input
                name="product_name"
                value={
                  form.product_name
                }
                onChange={change}
                placeholder="Product name"
                required
              />
            </label>

            <label className="form-field">
              <span>Model Number</span>

              <input
                name="model_number"
                value={
                  form.model_number
                }
                onChange={change}
                placeholder="Model number"
                required
              />

              {changedFromWarranty(
                'model_number'
              ) && (
                <span className="ocr-mismatch">
                  ⚠ Different from the
                  warranty card
                </span>
              )}
            </label>

            <label className="form-field">
              <span>Serial Number</span>

              <input
                name="serial_number"
                value={
                  form.serial_number
                }
                onChange={change}
                placeholder="Serial number"
                required
              />

              {changedFromWarranty(
                'serial_number'
              ) && (
                <span className="ocr-mismatch">
                  ⚠ Different from the
                  warranty card
                </span>
              )}
            </label>

            <label className="form-field">
              <span>Purchase Date</span>

              <input
                type="date"
                name="purchase_date"
                value={
                  form.purchase_date
                }
                onChange={change}
                required
              />

              {changedFromWarranty(
                'purchase_date'
              ) && (
                <span className="ocr-mismatch">
                  ⚠ Different from the
                  warranty card
                </span>
              )}
            </label>

            <label className="form-field">
              <span>
                Warranty Duration
              </span>

              <input
                type="number"
                min="1"
                max="120"
                name="warranty_duration_months"
                value={
                  form
                    .warranty_duration_months
                }
                onChange={change}
                required
              />

              {changedFromWarranty(
                'warranty_duration_months'
              ) && (
                <span className="ocr-mismatch">
                  ⚠ Different from the
                  warranty card
                </span>
              )}
            </label>
          </div>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                Step 2
              </p>

              <h2>
                What Happened?
              </h2>

              <p className="section-helper">
                Tell us about the fault or
                problem with the product.
              </p>
            </div>
          </div>

          <div className="form-grid">
            <label className="form-field">
              <span>
                When did you first notice the issue?
                <small> Optional</small>
              </span>

              <input
                type="date"
                name="fault_date"
                value={form.fault_date}
                onChange={change}
              />
            </label>

            <label className="form-field">
              <span>
                Damage / Fault Type
              </span>

              <select
                name="damage_type"
                value={
                  form.damage_type
                }
                onChange={change}
                required
              >
                <option value="">
                  Select fault type...
                </option>

                <optgroup label="Product Fault">
                  <option>
                    Manufacturing Defect
                  </option>

                  <option>
                    Electrical Failure
                  </option>

                  <option>
                    Internal Component Failure
                  </option>
                </optgroup>

                <optgroup label="Other Damage">
                  <option>
                    Accidental Damage
                  </option>

                  <option>
                    Water Damage
                  </option>

                  <option>
                    Physical Damage
                  </option>

                  <option>
                    Normal Wear
                  </option>

                  <option>
                    Misuse
                  </option>
                </optgroup>

                <option>
                  Other / Uncertain
                </option>
              </select>
            </label>

            <label className="form-field">
              <span>
                Estimated Repair / Claim Amount
                <small> Optional</small>
              </span>

              <input
                type="number"
                min="0.01"
                step="0.01"
                name="claim_amount"
                value={
                  form.claim_amount
                }
                onChange={change}
                placeholder="Enter an estimate if known"
              />
            </label>
          </div>

          <label className="form-field full-width">
            <span>
              Issue Details
            </span>

            <textarea
              name="fault_description"
              value={
                form.fault_description
              }
              onChange={change}
              rows="5"
              placeholder="Describe the symptoms, how often the issue occurs, any error messages, changes in product behavior, and any troubleshooting you have already tried..."
              required
            />
          </label>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Step 3</p>
              <h2>Supporting Evidence & Documents</h2>
              <p className="section-helper">
                Upload receipts, photos, or fault videos. Files are securely validated and cryptographically hashed with SHA-256 for integrity verification.
              </p>
            </div>
          </div>

          {uploadError && <div className="alert error" style={{ marginBottom: '14px' }}>{uploadError}</div>}

          <div className="evidence-upload-grid">
            {/* Purchase Receipt */}
            <div className={`evidence-upload-card ${evidenceFiles.receipt ? 'has-file' : ''}`}>
              <h4>
                <span>📄</span> Purchase Receipt
                {evidenceFiles.receipt && <span style={{ color: 'var(--ax-success)', fontSize: '12px' }}>✓ Verified</span>}
              </h4>
              <p>Proof of purchase from retailer or store (PDF, JPG, PNG · Max 25 MB).</p>
              {evidenceFiles.receipt ? (
                <div>
                  <div style={{ fontWeight: 600, fontSize: '13px', wordBreak: 'break-all' }}>
                    {evidenceFiles.receipt.filename}
                  </div>
                  <div style={{ marginTop: '6px' }}>
                    <span className="sha256-badge" title={evidenceFiles.receipt.sha256}>
                      SHA-256: {evidenceFiles.receipt.sha256.substring(0, 16)}...
                    </span>
                  </div>
                  <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
                    <a
                      href={evidenceFiles.receipt.file_url}
                      target="_blank"
                      rel="noreferrer"
                      className="button secondary"
                      style={{ padding: '4px 10px', fontSize: '12px' }}
                    >
                      View Receipt ↗
                    </a>
                    <button
                      type="button"
                      className="text-button"
                      style={{ color: 'var(--ax-danger)', fontSize: '12px' }}
                      onClick={() => removeEvidenceFile('receipt')}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ) : (
                <label className="button secondary" style={{ cursor: 'pointer', textAlign: 'center', marginTop: 'auto' }}>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,application/pdf"
                    style={{ display: 'none' }}
                    onChange={(e) => handleFileUpload(e, 'receipt')}
                    disabled={uploadingDoc === 'receipt'}
                  />
                  {uploadingDoc === 'receipt' ? 'Uploading & Hashing...' : 'Upload Receipt'}
                </label>
              )}
            </div>

            {/* Product Photo */}
            <div className={`evidence-upload-card ${evidenceFiles.product_image ? 'has-file' : ''}`}>
              <h4>
                <span>📷</span> Product Photo
                {evidenceFiles.product_image && <span style={{ color: 'var(--ax-success)', fontSize: '12px' }}>✓ Verified</span>}
              </h4>
              <p>Clear photo of your product showing the model and overall condition.</p>
              {evidenceFiles.product_image ? (
                <div>
                  <div style={{ fontWeight: 600, fontSize: '13px', wordBreak: 'break-all' }}>
                    {evidenceFiles.product_image.filename}
                  </div>
                  <div style={{ marginTop: '6px' }}>
                    <span className="sha256-badge" title={evidenceFiles.product_image.sha256}>
                      SHA-256: {evidenceFiles.product_image.sha256.substring(0, 16)}...
                    </span>
                  </div>
                  <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
                    <a
                      href={evidenceFiles.product_image.file_url}
                      target="_blank"
                      rel="noreferrer"
                      className="button secondary"
                      style={{ padding: '4px 10px', fontSize: '12px' }}
                    >
                      View Photo ↗
                    </a>
                    <button
                      type="button"
                      className="text-button"
                      style={{ color: 'var(--ax-danger)', fontSize: '12px' }}
                      onClick={() => removeEvidenceFile('product_image')}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ) : (
                <label className="button secondary" style={{ cursor: 'pointer', textAlign: 'center', marginTop: 'auto' }}>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    style={{ display: 'none' }}
                    onChange={(e) => handleFileUpload(e, 'product_image')}
                    disabled={uploadingDoc === 'product_image'}
                  />
                  {uploadingDoc === 'product_image' ? 'Uploading & Hashing...' : 'Upload Product Photo'}
                </label>
              )}
            </div>

            {/* Fault Evidence (Damage Photo / Fault Video) */}
            <div className={`evidence-upload-card ${evidenceFiles.fault_evidence ? 'has-file' : ''}`}>
              <h4>
                <span>⚠️</span> Fault / Damage Evidence
                {evidenceFiles.fault_evidence && <span style={{ color: 'var(--ax-success)', fontSize: '12px' }}>✓ Verified</span>}
              </h4>
              <p>Close-up photo of the defect, cracked part, or short video of malfunction (MP4/JPG/PNG).</p>
              {evidenceFiles.fault_evidence ? (
                <div>
                  <div style={{ fontWeight: 600, fontSize: '13px', wordBreak: 'break-all' }}>
                    {evidenceFiles.fault_evidence.filename}
                  </div>
                  <div style={{ marginTop: '6px' }}>
                    <span className="sha256-badge" title={evidenceFiles.fault_evidence.sha256}>
                      SHA-256: {evidenceFiles.fault_evidence.sha256.substring(0, 16)}...
                    </span>
                  </div>
                  <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
                    <a
                      href={evidenceFiles.fault_evidence.file_url}
                      target="_blank"
                      rel="noreferrer"
                      className="button secondary"
                      style={{ padding: '4px 10px', fontSize: '12px' }}
                    >
                      View Evidence ↗
                    </a>
                    <button
                      type="button"
                      className="text-button"
                      style={{ color: 'var(--ax-danger)', fontSize: '12px' }}
                      onClick={() => removeEvidenceFile('fault_evidence')}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ) : (
                <label className="button secondary" style={{ cursor: 'pointer', textAlign: 'center', marginTop: 'auto' }}>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp,video/mp4"
                    style={{ display: 'none' }}
                    onChange={(e) => handleFileUpload(e, 'fault_evidence')}
                    disabled={uploadingDoc === 'fault_evidence'}
                  />
                  {uploadingDoc === 'fault_evidence' ? 'Uploading & Hashing...' : 'Upload Fault Photo / Video'}
                </label>
              )}
            </div>
          </div>
        </section>

        {/* Step 4: Repair History */}
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Step 4</p>
              <h2>Repair & Maintenance History</h2>
              <p className="section-helper">
                Record any previous servicing to help our engineering team assess recurring faults accurately.
              </p>
            </div>
          </div>

          <div className="form-grid">
            <label className="form-field full-width">
              <span>Has this product been repaired or serviced before?</span>
              <select
                name="previous_repair"
                value={form.previous_repair}
                onChange={change}
                required
              >
                <option value="No">No — this is the first issue</option>
                <option value="Yes">Yes — product has previous repair history</option>
              </select>
            </label>

            {form.previous_repair === 'Yes' && (
              <>
                <label className="form-field">
                  <span>Number of Previous Repairs</span>
                  <input
                    type="number"
                    min="1"
                    name="repair_count"
                    value={form.repair_count}
                    onChange={change}
                    required
                  />
                </label>

                <label className="form-field">
                  <span>Previous Repair Date</span>
                  <input
                    type="date"
                    name="previous_repair_date"
                    value={form.previous_repair_date}
                    onChange={change}
                  />
                </label>

                <label className="form-field">
                  <span>Service Center Name</span>
                  <input
                    type="text"
                    name="repair_center_name"
                    placeholder="e.g. AssureX Authorized Service Center"
                    value={form.repair_center_name}
                    onChange={change}
                  />
                </label>

                <label className="form-field">
                  <span>Replaced Parts (if known)</span>
                  <input
                    type="text"
                    name="replaced_parts"
                    placeholder="e.g. Motherboard, battery, display cable"
                    value={form.replaced_parts}
                    onChange={change}
                  />
                </label>

                <label className="form-field">
                  <span>Prior Repair Outcome</span>
                  <select
                    name="repair_outcome"
                    value={form.repair_outcome}
                    onChange={change}
                  >
                    <option value="Fully Resolved">Fully Resolved</option>
                    <option value="Partially Resolved">Partially Resolved</option>
                    <option value="Recurring Fault">Recurring Fault</option>
                    <option value="Unresolved">Unresolved</option>
                  </select>
                </label>

                <label className="form-field">
                  <span>Prior Repair Cost ($ USD)</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    name="repair_cost"
                    placeholder="0.00"
                    value={form.repair_cost}
                    onChange={change}
                  />
                </label>

                <label className="form-field">
                  <span>Repaired by Authorized Center?</span>
                  <select
                    name="repair_authorized"
                    value={form.repair_authorized}
                    onChange={change}
                    required
                  >
                    <option value="">Select authorization status...</option>
                    <option value="Yes">Yes — Authorized Official Center</option>
                    <option value="No">No — Independent Third-Party Repair</option>
                    <option value="Unknown">Not sure</option>
                  </select>
                </label>

                {/* Repair Report Upload */}
                <div className="form-field full-width">
                  <span>Upload Previous Diagnostic / Repair Report</span>
                  <div className={`evidence-upload-card ${evidenceFiles.repair_report ? 'has-file' : ''}`} style={{ marginTop: '6px' }}>
                    {evidenceFiles.repair_report ? (
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <strong>{evidenceFiles.repair_report.filename}</strong>
                          <span className="sha256-badge" style={{ marginLeft: '10px' }}>
                            SHA-256: {evidenceFiles.repair_report.sha256.substring(0, 16)}...
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <a
                            href={evidenceFiles.repair_report.file_url}
                            target="_blank"
                            rel="noreferrer"
                            className="button secondary"
                            style={{ padding: '4px 8px', fontSize: '12px' }}
                          >
                            View Report ↗
                          </a>
                          <button
                            type="button"
                            className="text-button"
                            style={{ color: 'var(--ax-danger)', fontSize: '12px' }}
                            onClick={() => removeEvidenceFile('repair_report')}
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    ) : (
                      <label className="button secondary" style={{ cursor: 'pointer', textAlign: 'center', width: 'fit-content' }}>
                        <input
                          type="file"
                          accept="image/jpeg,image/png,application/pdf"
                          style={{ display: 'none' }}
                          onChange={(e) => handleFileUpload(e, 'repair_report')}
                          disabled={uploadingDoc === 'repair_report'}
                        />
                        {uploadingDoc === 'repair_report' ? 'Uploading & Hashing...' : 'Upload Repair Report (PDF / Image)'}
                      </label>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </section>

        <section className="readiness-check" aria-live="polite">
          <div>
            <p className="eyebrow">Claim Readiness Check</p>
            <h2>
              {missingInformation.length === 0
                ? 'Required information is complete'
                : `${missingInformation.length} required item(s) missing`}
            </h2>
          </div>
          {missingInformation.length > 0 && (
            <p>Complete: {missingInformation.join(', ')}</p>
          )}
          <p>
            {missingDocuments.length === 0
              ? 'All listed evidence is marked available.'
              : `Evidence to add or confirm: ${missingDocuments.join(', ')}`}
          </p>
          <small>
            Missing evidence may require manual review; you can still submit without an optional document.
          </small>
        </section>

        <section className="assessment-notice">
          <div>
            <strong>
              Automated Claim Assessment
            </strong>

            <p>
              AssureX will verify the
              document data, derive the ML
              features automatically and
              evaluate the claim.
            </p>
          </div>

          <div className="assessment-flow">
            <span>
              Valid → Approved
            </span>

            <span>
              Invalid → Rejected
            </span>

            <span>
              Uncertain → Manual Review
            </span>
          </div>
        </section>

        {error && (
          <div className="alert error">
            {error}
          </div>
        )}

        <div className="form-actions between">
          <button
            type="button"
            className="button secondary"
            onClick={() =>
              onNavigate('home')
            }
          >
            Cancel
          </button>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              type="button"
              className="button secondary"
              onClick={saveDraft}
            >
              Save Draft
            </button>

            <button
              type="submit"
              className="button primary large"
              disabled={submitting || missingInformation.length > 0}
            >
              {submitting
                ? 'Evaluating Claim...'
                : 'Submit Claim'}
            </button>
          </div>
        </div>
      </form>
    </>
  )
}


function ClaimTimeline({ claimId, status }) {
  const [events, setEvents] = useState([])

  useEffect(() => {
    if (!claimId) return
    api(`/api/customer/claims/${encodeURIComponent(claimId)}/history`)
      .then(setEvents)
      .catch(() => setEvents([]))
  }, [claimId])

  return (
    <section className="claim-timeline">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Claim Timeline</p>
          <h3>{status}</h3>
        </div>
      </div>
      {events.length === 0 ? (
        <p className="timeline-empty">No audit events recorded yet.</p>
      ) : (
        <ol className="timeline-events">
          {events.map((event, index) => (
            <li key={`${event.action}-${event.date}-${index}`}>
              <span className="timeline-marker" />
              <div>
                <strong>{event.action.replaceAll('_', ' ')}</strong>
                <p>{event.details?.status || event.details?.final_decision || event.result}</p>
                <small>{formatDate(event.date)} · {event.user} ({event.role})</small>
                {event.details?.reviewer_comment && (
                  <p>{event.details.reviewer_comment}</p>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}


function CustomerClaims({
  email,
  setEmail,
  refreshKey,
  hideIdentity,
}) {
  const [claims, setClaims] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(Boolean(email))

  useEffect(() => {
    if (!email) {
      setClaims([])
      setSelected(null)
      setLoading(false)
      return
    }

    setLoading(true)

    api(
      `/api/customer/claims?email=${encodeURIComponent(
        email
      )}`
    )
      .then(setClaims)
      .finally(() => setLoading(false))
  }, [email, refreshKey])

  return (
    <>
      <PageHeader
        eyebrow="Customer Portal"
        title="My Claims"
      />

      {!hideIdentity && (
        <CustomerIdentity
          email={email}
          onChange={setEmail}
        />
      )}

      <section className="panel">
        {loading ? (
          <LoadingState />
        ) : !email ? (
          <EmptyState
            title="Enter your email"
          />
        ) : claims.length === 0 ? (
          <EmptyState
            title="No claims found"
          />
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Claim ID</th>
                  <th>Product</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Submitted</th>
                </tr>
              </thead>

              <tbody>
                {claims.map((claim) => (
                  <tr
                    key={claim.id}
                    className={
                      selected?.id === claim.id
                        ? 'selected-row'
                        : ''
                    }
                    onClick={() =>
                      setSelected(claim)
                    }
                  >
                    <td className="mono">
                      {claim.claim_id}
                    </td>
                    <td>{claim.product_name}</td>
                    <td>
                      {formatNumber(
                        claim.claim_amount
                      )}
                    </td>
                    <td>
                      <StatusBadge
                        value={claim.status}
                      />
                    </td>
                    <td>
                      {formatDate(
                        claim.created_at
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected && (
        <section className="panel detail-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                Claim Status
              </p>
              <h2>{selected.claim_id}</h2>
            </div>

            <StatusBadge value={selected.status} />
          </div>

          <ClaimTimeline claimId={selected.claim_id} status={selected.status} />

          {selected.decision && (
            <div className="claim-analysis">
              <p className="eyebrow">AI + Rule Analysis & Dual-Model Verification</p>

              {/* Dual-Model Comparison Cards */}
              <div className="dual-model-grid">
                <div className="model-card python-model">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em', color: 'var(--ax-primary)' }}>
                      PYTHON CLASSIFIER (LOCAL ML)
                    </span>
                    <span className="status-badge status-approved" style={{ fontSize: '11px' }}>
                      Primary Model
                    </span>
                  </div>
                  <h3 style={{ margin: '8px 0 4px', fontSize: '16px' }}>
                    {selected.decision.python_model_name || 'Random Forest Classifier'}
                  </h3>
                  <div style={{ fontSize: '12px', color: 'var(--ax-text-faint)', marginBottom: '10px' }}>
                    Version: {selected.decision.python_model_version || 'v1.0.0'}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', borderTop: '1px solid var(--ax-border)', paddingTop: '10px' }}>
                    <div>
                      <span style={{ fontSize: '11px', color: 'var(--ax-text-soft)' }}>Prediction</span>
                      <div style={{ fontWeight: 700, fontSize: '15px' }}>{selected.decision.ml_prediction}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '11px', color: 'var(--ax-text-soft)' }}>Confidence</span>
                      <div style={{ fontWeight: 700, fontSize: '15px', color: 'var(--ax-primary)' }}>
                        {(selected.decision.ml_confidence * 100).toFixed(2)}%
                      </div>
                    </div>
                  </div>
                </div>

                <div className="model-card google-model">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em', color: '#ea4335' }}>
                      GOOGLE TEACHABLE MACHINE (GTM)
                    </span>
                    <span
                      className={`status-badge ${selected.decision.google_inference_status === 'connected' ? 'status-approved' : 'status-review'}`}
                      style={{ fontSize: '11px' }}
                    >
                      {selected.decision.google_inference_status === 'connected' ? 'Connected' : 'Standby / Offline'}
                    </span>
                  </div>
                  <h3 style={{ margin: '8px 0 4px', fontSize: '16px' }}>
                    {selected.decision.google_model_name || 'Google Cloud GTM Model'}
                  </h3>
                  <div style={{ fontSize: '12px', color: 'var(--ax-text-faint)', marginBottom: '10px' }}>
                    Endpoint: {selected.decision.google_model_version || 'Public GTM URL'}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', borderTop: '1px solid var(--ax-border)', paddingTop: '10px' }}>
                    <div>
                      <span style={{ fontSize: '11px', color: 'var(--ax-text-soft)' }}>GTM Prediction</span>
                      <div style={{ fontWeight: 700, fontSize: '15px' }}>
                        {selected.decision.google_prediction || 'Standby'}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '11px', color: 'var(--ax-text-soft)' }}>Confidence</span>
                      <div style={{ fontWeight: 700, fontSize: '15px', color: '#ea4335' }}>
                        {selected.decision.google_confidence != null
                          ? `${(selected.decision.google_confidence * 100).toFixed(2)}%`
                          : '—'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Consistency & Agreement Bar */}
              <div className="consistency-box">
                <div>
                  <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--ax-text-faint)', fontWeight: 700 }}>
                    Dual-Model Consistency Status
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                    <span
                      className={`status-badge ${
                        selected.decision.model_consistency_status === 'Strong Match'
                          ? 'status-approved'
                          : selected.decision.model_consistency_status === 'Acceptable Match'
                            ? 'status-approved'
                            : selected.decision.model_consistency_status === 'Model Disagreement'
                              ? 'status-rejected'
                              : 'status-review'
                      }`}
                      style={{ fontSize: '13px', padding: '4px 10px' }}
                    >
                      {selected.decision.model_consistency_status || 'Dual Evaluation Standby'}
                    </span>
                    {selected.decision.confidence_difference != null && (
                      <span style={{ fontSize: '13px', color: 'var(--ax-text-soft)' }}>
                        (Confidence Difference: {(selected.decision.confidence_difference * 100).toFixed(2)}%)
                      </span>
                    )}
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--ax-text-faint)', fontWeight: 700 }}>
                    Final Decision Engine Result
                  </span>
                  <div style={{ fontWeight: 700, fontSize: '15px', marginTop: '4px' }}>
                    {selected.decision.final_decision}
                  </div>
                </div>
              </div>

              {selected.decision.decision_reasons?.length > 0 && (
                <div style={{ marginTop: '14px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600 }}>Decision Reasons:</span>
                  <ul className="decision-reason-list" style={{ marginTop: '6px' }}>
                    {selected.decision.decision_reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}

              <details className="analysis-inputs" style={{ marginTop: '14px' }}>
                <summary>Rule inputs and derived warranty values</summary>
                <div className="feature-grid">
                  {Object.entries({
                    ...selected.decision.derived_data,
                    ...selected.decision.model_features,
                  }).map(([name, value]) => (
                    <div key={name}>
                      <span>{name}</span>
                      <strong>{String(value ?? '—')}</strong>
                    </div>
                  ))}
                </div>
              </details>

              {selected.decision.reviewer_decision && (
                <p className="reviewer-summary" style={{ marginTop: '12px' }}>
                  Reviewer Override: <strong>{selected.decision.reviewer_decision}</strong>
                  {selected.decision.reviewer_comment && ` · "${selected.decision.reviewer_comment}"`}
                </p>
              )}
            </div>
          )}

          {/* Attached Evidence & Documents Section */}
          <div className="claim-documents-panel" style={{ marginTop: '20px', borderTop: '1px solid var(--ax-border)', paddingTop: '16px' }}>
            <p className="eyebrow">Evidence & Attached Documents</p>
            <h3 style={{ margin: '4px 0 12px', fontSize: '16px' }}>Uploaded Verification Evidence</h3>

            <div className="evidence-upload-grid">
              {/* Receipt */}
              {selected.receipt_url ? (
                <div className="evidence-upload-card has-file">
                  <h4><span>📄</span> Purchase Receipt</h4>
                  <p>Retailer proof of purchase</p>
                  {selected.document_hashes?.receipt && (
                    <span className="sha256-badge" title={selected.document_hashes.receipt}>
                      SHA-256: {selected.document_hashes.receipt.substring(0, 16)}...
                    </span>
                  )}
                  <a
                    href={selected.receipt_url}
                    target="_blank"
                    rel="noreferrer"
                    className="button secondary"
                    style={{ padding: '5px 10px', fontSize: '12px', marginTop: '6px', textAlign: 'center' }}
                  >
                    View / Download Receipt ↗
                  </a>
                </div>
              ) : null}

              {/* Product Photo */}
              {selected.product_image_url ? (
                <div className="evidence-upload-card has-file">
                  <h4><span>📷</span> Product Photo</h4>
                  <p>Product & Serial label evidence</p>
                  {selected.document_hashes?.product_image && (
                    <span className="sha256-badge" title={selected.document_hashes.product_image}>
                      SHA-256: {selected.document_hashes.product_image.substring(0, 16)}...
                    </span>
                  )}
                  <a
                    href={selected.product_image_url}
                    target="_blank"
                    rel="noreferrer"
                    className="button secondary"
                    style={{ padding: '5px 10px', fontSize: '12px', marginTop: '6px', textAlign: 'center' }}
                  >
                    View Product Image ↗
                  </a>
                </div>
              ) : null}

              {/* Damage / Fault Photo */}
              {selected.evidence_photo_url ? (
                <div className="evidence-upload-card has-file">
                  <h4><span>⚠️</span> Fault / Damage Evidence</h4>
                  <p>Visual verification of defect</p>
                  {selected.document_hashes?.fault_evidence && (
                    <span className="sha256-badge" title={selected.document_hashes.fault_evidence}>
                      SHA-256: {selected.document_hashes.fault_evidence.substring(0, 16)}...
                    </span>
                  )}
                  <a
                    href={selected.evidence_photo_url}
                    target="_blank"
                    rel="noreferrer"
                    className="button secondary"
                    style={{ padding: '5px 10px', fontSize: '12px', marginTop: '6px', textAlign: 'center' }}
                  >
                    View Fault Evidence ↗
                  </a>
                </div>
              ) : null}

              {/* Repair Diagnostic Report */}
              {selected.repair_report_url ? (
                <div className="evidence-upload-card has-file">
                  <h4><span>🔧</span> Repair Diagnostic Report</h4>
                  <p>Prior service documentation</p>
                  {selected.document_hashes?.repair_report && (
                    <span className="sha256-badge" title={selected.document_hashes.repair_report}>
                      SHA-256: {selected.document_hashes.repair_report.substring(0, 16)}...
                    </span>
                  )}
                  <a
                    href={selected.repair_report_url}
                    target="_blank"
                    rel="noreferrer"
                    className="button secondary"
                    style={{ padding: '5px 10px', fontSize: '12px', marginTop: '6px', textAlign: 'center' }}
                  >
                    View Diagnostic Report ↗
                  </a>
                </div>
              ) : null}

              {!selected.receipt_url && !selected.product_image_url && !selected.evidence_photo_url && !selected.repair_report_url && (
                <p style={{ color: 'var(--ax-text-faint)', fontSize: '13px', gridColumn: '1 / -1' }}>
                  No extra documents attached to this claim submission.
                </p>
              )}
            </div>
          </div>

          {/* Prior Repair History Section */}
          {(selected.repair_center_name || selected.previous_repair_date || selected.replaced_parts || selected.raw_input?.previous_repair === 'Yes') && (
            <div style={{ marginTop: '20px', borderTop: '1px solid var(--ax-border)', paddingTop: '16px' }}>
              <p className="eyebrow">Service History</p>
              <h3 style={{ margin: '4px 0 12px', fontSize: '16px' }}>Prior Product Repair Details</h3>
              <div className="detail-grid">
                <div>
                  <span>Service Center</span>
                  <strong>{selected.repair_center_name || 'Authorized Service Provider'}</strong>
                </div>
                <div>
                  <span>Repair Date</span>
                  <strong>{selected.previous_repair_date || 'Prior to claim'}</strong>
                </div>
                <div>
                  <span>Replaced Parts</span>
                  <strong>{selected.replaced_parts || 'Standard maintenance'}</strong>
                </div>
                <div>
                  <span>Repair Outcome</span>
                  <strong>{selected.repair_outcome || 'Resolved'}</strong>
                </div>
                <div>
                  <span>Prior Repair Cost</span>
                  <strong>{selected.repair_cost ? `$${Number(selected.repair_cost).toFixed(2)}` : 'Covered'}</strong>
                </div>
              </div>
            </div>
          )}

          <div className="detail-grid" style={{ marginTop: '20px', borderTop: '1px solid var(--ax-border)', paddingTop: '16px' }}>
            <div>
              <span>Product</span>
              <strong>
                {selected.product_name}
              </strong>
            </div>

            <div>
              <span>Serial Number</span>
              <strong>
                {selected.serial_number}
              </strong>
            </div>

            <div>
              <span>Purchase Date</span>
              <strong>
                {selected.purchase_date}
              </strong>
            </div>

            <div>
              <span>Claim Amount</span>
              <strong>
                {formatNumber(
                  selected.claim_amount
                )}
              </strong>
            </div>
          </div>

          <div className="description-box">
            <span>Your Description</span>
            <p>{selected.fault_description}</p>
          </div>
        </section>
      )}
    </>
  )
}


function ReviewerAppeals({ onChanged }) {
  const [appeals, setAppeals] = useState([])
  const [comments, setComments] = useState({})
  const [status, setStatus] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  function loadAppeals() {
    setLoading(true)
    api('/api/appeals')
      .then(setAppeals)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadAppeals() }, [])

  async function resolveAppeal(appeal) {
    const decision = status[appeal.id] || 'Rejected'
    const comment = (comments[appeal.id] || '').trim()
    if (comment.length < 5) {
      setError('Please add a reviewer explanation before resolving the appeal.')
      return
    }
    setError('')
    try {
      await api(`/api/appeals/${appeal.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: decision, reviewer_comment: comment }),
      })
      setAppeals((current) => current.map((item) => item.id === appeal.id ? { ...item, status: decision, reviewer_comment: comment } : item))
      onChanged()
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  const pending = appeals.filter((appeal) => appeal.status === 'Pending')
  return <>
    <PageHeader eyebrow="Reviewer workspace" title="Appeals" description="Resolve rejected claim appeals while preserving the original decision and complete audit history." />
    {error && <div className="alert error">{error}</div>}
    {loading ? <LoadingState /> : pending.length === 0 ? <EmptyState title="No pending appeals" description="New customer appeals will appear here." /> : <div className="panel-grid">
      {pending.map((appeal) => <section className="panel" key={appeal.id}>
        <div className="panel-heading"><div><p className="eyebrow">Appeal #{appeal.id}</p><h2>{appeal.claim_id}</h2></div><StatusBadge value={appeal.status} /></div>
        <div className="description-box"><span>Customer appeal reason</span><p>{appeal.reason}</p></div>
        <div className="detail-grid"><div><span>Submitted</span><strong>{formatDate(appeal.created_at)}</strong></div><div><span>Original claim</span><strong>{appeal.claim_id}</strong></div></div>
        <label className="review-note" style={{ display: 'block', marginTop: '14px' }}><span>Reviewer response</span><textarea rows="3" value={comments[appeal.id] || ''} onChange={(event) => setComments((current) => ({ ...current, [appeal.id]: event.target.value }))} placeholder="Explain why the original decision is upheld or changed..." /></label>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '10px', flexWrap: 'wrap' }}><select value={status[appeal.id] || 'Rejected'} onChange={(event) => setStatus((current) => ({ ...current, [appeal.id]: event.target.value }))}><option value="Rejected">Uphold rejection</option><option value="Approved">Approve after appeal</option></select><button className="button primary" onClick={() => resolveAppeal(appeal)}>Resolve appeal</button></div>
      </section>)}
    </div>}
    {appeals.some((appeal) => appeal.status !== 'Pending') && <section className="panel" style={{ marginTop: '16px' }}><div className="panel-heading"><div><p className="eyebrow">History</p><h2>Resolved appeals</h2></div></div><div className="compact-list">{appeals.filter((appeal) => appeal.status !== 'Pending').map((appeal) => <div className="compact-row" key={appeal.id}><strong>{appeal.claim_id}</strong><StatusBadge value={appeal.status} /><span>{appeal.reviewer_comment || 'Resolved'}</span></div>)}</div></section>}
  </>
}

function ReviewerWorkspace({ onLogout, email }) {
  const [page, setPage] = useState('warranty-desk')
  const [refreshKey, setRefreshKey] = useState(0)
  const nav = [['overview', 'Review overview'], ['queue', 'Claim queue'], ['resolved', 'Resolved claims'], ['appeals', 'Appeals'], ['profile', 'My profile']]
  return <div className="app-shell reviewer-shell">
    <aside className="sidebar reviewer-sidebar"><div className="brand"><div className="brand-mark">AX</div><div><h2>AssureX</h2><p>Reviewer Desk</p></div></div><div className="sidebar-section-label">My workspace</div><nav className="nav-menu">{nav.map(([key,label]) => <button key={key} className={`nav-item ${page===key?'active':''}`} onClick={()=>setPage(key)}>{label}</button>)}</nav><div className="reviewer-rail-note"><strong>Reviewer mode</strong><span>Decision queue & customer appeals</span></div><button className="admin-logout-button" onClick={onLogout}>Log out</button></aside>
    <main className="main-content">{page==='overview' && <><PageHeader eyebrow="Reviewer workspace" title="Review overview" description="Prioritize claim decisions, appeals and verified feedback for future retraining." action={<button className="button primary" onClick={()=>setPage('queue')}>Open claim queue →</button>} /><div className="stats-grid"><StatCard label="Pending review" value="12" hint="Claims waiting for decision" tone="warning"/><StatCard label="High confidence" value="8" hint="Model confidence above 85%" tone="success"/><StatCard label="Appeals" value="3" hint="Need your response" tone="danger"/><StatCard label="Reviewed today" value="24" hint="Across all categories"/></div><section className="reviewer-focus"><div><p className="eyebrow">Next best action</p><h2>Prioritize pending reviews and appeals</h2><p>Review claim evidence, apply policy validation and record a final decision.</p></div><button className="button secondary" onClick={()=>setPage('appeals')}>View appeals</button></section><section className="panel"><div className="panel-heading"><div><p className="eyebrow">Today</p><h2>Review workload</h2></div></div><div className="review-progress"><span style={{width:'68%'}}></span></div><p className="muted">68% of today’s assigned claims have been resolved.</p></section></>}{page==='queue' && <AdminCustomerClaims refreshKey={refreshKey} onChanged={()=>setRefreshKey(x=>x+1)} canReview />}{page==='resolved' && <AdminCustomerClaims refreshKey={refreshKey} onChanged={()=>setRefreshKey(x=>x+1)} canReview={false} resolvedOnly />}{page==='appeals' && <ReviewerAppeals onChanged={()=>setRefreshKey(x=>x+1)} />}{page==='profile' && <WorkspaceProfile email={email} role="REVIEWER"/>}</main>
  </div>
}

function AdminMLConsole() {
  const [retrainRequested, setRetrainRequested] = useState(false)
  const [version, setVersion] = useState(() => { const saved = localStorage.getItem('assurex_model_version'); return saved?.startsWith('G') ? saved : 'G2_V3' })
  const datasetFields = ['RepairAuthorized','SerialNumberMatch','ProductModelConsistent','DuplicateClaimIndicator','ContradictionIndicator','OCRConfidence','ClaimReportingDelayDays','WarrantyRemainingDays','ClaimReportingWithinPeriod','FaultCovered','RequiredDocumentsComplete','MissingDocumentCount','ProductIdentityMatch','OCRQualityBand']
  const topFeatures = [['FaultCovered', 0.2916], ['WarrantyRemainingDays', 0.1721], ['RequiredDocumentsComplete', 0.1188], ['MissingDocumentCount', 0.0859], ['ProductIdentityMatch', 0.0509]]
  function requestRetrain() { const match = version.match(/^G(\d+)_V(\d+)$/); const next = match ? `G${match[1]}_V${Number(match[2]) + 1}` : 'G2_V4'; localStorage.setItem('assurex_model_version', next); setVersion(next); setRetrainRequested(true) }
  return <><PageHeader eyebrow="Admin · Model control center" title="Model Intelligence" action={<button className="button primary" onClick={requestRetrain}>Retrain Model →</button>} />{retrainRequested && <div className="alert success">New model version {version} queued for evaluation.</div>}<section className="panel"><div className="panel-heading"><div><p className="eyebrow">Evaluation Metrics</p><h2>Model comparison</h2></div><span className="pipeline-status">Production · {version}</span></div><div className="table-wrapper"><table className="data-table metrics-table"><thead><tr><th>Metric</th><th>Tuning · Gradient Boosting</th><th>Inception-v1</th><th>Winner</th></tr></thead><tbody>{[['Accuracy','99.11%','86.22%','Tuning'],['F1-Score','99.11%','86.10%','Tuning'],['Precision','99.13%','87.52%','Tuning'],['Recall','99.11%','86.22%','Tuning'],['AUC-ROC',MODEL_METRICS.pythonAuc,MODEL_METRICS.gtmAuc,'Tuning'],['Latency','Not reported','Not reported','—']].map(([metric,tabular,image,winner])=><tr key={metric}><td><strong>{metric}</strong></td><td>{tabular}</td><td>{image}</td><td><span className="status-badge status-approved">{winner}</span></td></tr>)}</tbody></table></div></section><div className="two-column"><section className="panel"><div className="panel-heading"><div><h2>Top 5 feature importance</h2></div></div><div className="feature-importance">{topFeatures.map(([name,value])=><div key={name}><span>{name}</span><b style={{width:`${value/0.2916*100}%`}}></b><em>{value.toFixed(4)}</em></div>)}</div></section><section className="panel"><div className="panel-heading"><div><h2>Confusion Matrix</h2></div></div><table className="mini-matrix"><thead><tr><th>Actual \ Pred.</th><th>Valid</th><th>Invalid</th><th>Review</th></tr></thead><tbody><tr><th>Valid</th><td>75</td><td>0</td><td>0</td></tr><tr><th>Invalid</th><td>0</td><td>75</td><td>0</td></tr><tr><th>Review</th><td>2</td><td>0</td><td>73</td></tr></tbody></table></section></div><section className="panel"><div className="panel-heading"><div><h2>Selected dataset features</h2></div><span className="schema-badge">14 / 81 selected</span></div><div className="dataset-field-grid">{datasetFields.map((field,index)=><div key={field} className="used-field"><span>{String(index+1).padStart(2,'0')}</span><strong>{field}</strong></div>)}</div></section><section className="panel retrain-panel"><div><h2>Retrain & versioning</h2><p className="section-lead">1,500 initial samples · 38 new approved samples · current {version}.</p></div><div className="retrain-stats"><strong>38<small>new labels</small></strong><strong>{version}<small>active version</small></strong><button className="button primary" onClick={requestRetrain}>Create next version</button></div></section></>
}

function AdminReports({ refreshKey }) {
  const [claims, setClaims] = useState([])
  const [status, setStatus] = useState('All')
  const [query, setQuery] = useState('')
  useEffect(() => { api('/api/customer/claims').then(setClaims).catch(() => setClaims([])) }, [refreshKey])
  const filtered = claims.filter((claim) => (status === 'All' || claim.status === status) && (!query || `${claim.claim_id} ${claim.product_name} ${claim.serial_number}`.toLowerCase().includes(query.toLowerCase())))
  const count = (value) => claims.filter((claim) => claim.status === value).length
  function exportCsv() {
    const columns = ['claim_id', 'status', 'customer_name', 'product_name', 'serial_number', 'claim_amount', 'created_at']
    const csv = [columns.join(','), ...filtered.map((claim) => columns.map((column) => csvValue(claim[column])).join(','))].join('\n')
    downloadFile('assurex-claims-report.csv', csv, 'text/csv;charset=utf-8')
  }
  return <><PageHeader eyebrow="Admin · Analytics & Reporting" title="Claims Reports" action={<button className="button primary" onClick={exportCsv}>Download CSV ↓</button>} /><div className="stats-grid"><StatCard label="Total claims" value={claims.length} hint="All submitted claims"/><StatCard label="Approved" value={count('Approved')} hint="Final positive decisions" tone="success"/><StatCard label="Manual review" value={count('Manual Review') + count('Under Review')} hint="Needs human action" tone="warning"/><StatCard label="Rejected" value={count('Rejected')} hint="Final negative decisions" tone="danger"/></div><section className="panel"><div className="panel-heading"><div><p className="eyebrow">Operational report</p><h2>Claim records</h2></div><div className="report-filters"><input placeholder="Search claim, product, serial..." value={query} onChange={(event) => setQuery(event.target.value)} /><select value={status} onChange={(event) => setStatus(event.target.value)}><option>All</option><option>Approved</option><option>Rejected</option><option>Under Review</option><option>Manual Review</option><option>Closed</option></select></div></div><div className="table-wrapper"><table className="data-table"><thead><tr><th>Claim ID</th><th>Product</th><th>Status</th><th>Amount</th><th>Model consistency</th><th>Created</th></tr></thead><tbody>{filtered.map((claim) => <tr key={claim.id || claim.claim_id}><td className="mono">{claim.claim_id}</td><td>{claim.product_name || '—'}<small className="table-subline">{claim.serial_number || 'No serial'}</small></td><td><StatusBadge value={claim.status}/></td><td>{formatNumber(claim.claim_amount)}</td><td>{claim.decision?.model_consistency_status || '—'}</td><td>{formatDate(claim.created_at)}</td></tr>)}{filtered.length === 0 && <tr><td colSpan="6">No claims match the selected filters.</td></tr>}</tbody></table></div></section></>
}

function AdminSettings() {
  const [saved, setSaved] = useState(false)
  const [settings, setSettings] = useState(() => {
    try { return JSON.parse(localStorage.getItem('assurex_admin_settings')) || { expiryDays: 30, minConfidence: 60, acceptableDifference: 15, reportingDays: 30, requiredReceipt: true, requiredProductPhoto: true } } catch { return { expiryDays: 30, minConfidence: 60, acceptableDifference: 15, reportingDays: 30, requiredReceipt: true, requiredProductPhoto: true } }
  })
  function update(name, value) { setSaved(false); setSettings((current) => ({ ...current, [name]: value })) }
  function save() { localStorage.setItem('assurex_admin_settings', JSON.stringify(settings)); setSaved(true) }
  return <><PageHeader eyebrow="Admin · System configuration" title="Rules & Alerts" action={<button className="button primary" onClick={save}>Save configuration</button>} />{saved && <div className="alert success">Configuration saved successfully.</div>}<div className="settings-grid"><section className="panel"><p className="eyebrow">Warranty expiry alerts</p><h2>Notification rules</h2><label className="setting-row"><span>Alert before expiry (days)</span><input type="number" min="1" max="365" value={settings.expiryDays} onChange={(event)=>update('expiryDays', Number(event.target.value))}/></label><label className="setting-row checkbox-row"><input type="checkbox" checked={settings.requiredReceipt} onChange={(event)=>update('requiredReceipt', event.target.checked)}/><span>Require purchase receipt for submission</span></label><label className="setting-row checkbox-row"><input type="checkbox" checked={settings.requiredProductPhoto} onChange={(event)=>update('requiredProductPhoto', event.target.checked)}/><span>Require product photo for submission</span></label></section><section className="panel"><p className="eyebrow">Decision engine</p><h2>Model and business thresholds</h2><label className="setting-row"><span>Minimum model confidence (%)</span><input type="number" min="0" max="100" value={settings.minConfidence} onChange={(event)=>update('minConfidence', Number(event.target.value))}/></label><label className="setting-row"><span>Acceptable model difference (%)</span><input type="number" min="0" max="100" value={settings.acceptableDifference} onChange={(event)=>update('acceptableDifference', Number(event.target.value))}/></label><label className="setting-row"><span>Claim reporting deadline (days)</span><input type="number" min="1" max="365" value={settings.reportingDays} onChange={(event)=>update('reportingDays', Number(event.target.value))}/></label></section></div><section className="panel"><p className="eyebrow">Active policy preview</p><h2>Applied rules</h2><div className="settings-summary"><span>Expiry alerts <strong>{settings.expiryDays} days before</strong></span><span>Manual review below <strong>{settings.minConfidence}% confidence</strong></span><span>Model match tolerance <strong>{settings.acceptableDifference}%</strong></span><span>Reporting period <strong>{settings.reportingDays} days</strong></span></div></section></>
}

function App({ onLogout, role, email }) {
  if (role === 'REVIEWER') return <ReviewerWorkspace onLogout={onLogout} email={email} />
  const [backendStatus, setBackendStatus] =
    useState('checking')

  const [adminPage, setAdminPage] =
    useState(() => {
      const match = window.location.pathname.match(/\/(?:admin|reviewer)(?:\/(.+))?$/)
      if (!match) return 'ai-ml'
      const suffix = match[1]
      if (!suffix) return 'ai-ml'
      const pageMap = {
        'warranty-desk': 'warranty-desk',
        'retraining': 'retraining',
        'customer-claims': 'customer-claims',
        'products': 'products',
        'notifications': 'notifications',
        'profile': 'profile',
        'classify': 'classify',
        'history': 'history',
        'model': 'model',
        'users': 'users',
        'audit': 'audit',
        'ai-ml': 'ai-ml',
        'ml-audit': 'ml-audit', 'ml-preprocessing': 'ml-preprocessing', 'ml-text': 'ml-text', 'ml-image': 'ml-image', 'ml-compare': 'ml-compare',
        'settings': 'settings',
      }
      return pageMap[suffix] || 'ai-ml'
    })

  const [refreshKey, setRefreshKey] =
    useState(0)
  const [notificationCount, setNotificationCount] = useState(0)

  useEffect(() => {
    document.body.classList.add('admin-light')
    return () => document.body.classList.remove('admin-light')
  }, [])

  useEffect(() => {
    api('/health')
      .then(() => setBackendStatus('online'))
      .catch(() =>
        setBackendStatus('offline')
      )
  }, [])

  useEffect(() => {
    let active = true
    api('/api/notifications')
      .then((items) => {
        if (!active) return
        const unread = items.filter((item) => !item.is_read).length
        setNotificationCount(unread)
      })
      .catch(() => {
        if (active) setNotificationCount(0)
      })
    return () => { active = false }
  }, [refreshKey, role, email])

  useEffect(() => {
    const syncPage = () => {
        const nextPage = (() => {
        const match = window.location.pathname.match(/\/(?:admin|reviewer)(?:\/(.+))?$/)
        if (!match) return 'ai-ml'
        const suffix = match[1]
        if (!suffix) return 'ai-ml'
        const map = {
          'warranty-desk': 'warranty-desk',
          'retraining': 'retraining',
          'customer-claims': 'customer-claims',
          'products': 'products',
          'notifications': 'notifications',
          'profile': 'profile',
          'classify': 'classify',
          'history': 'history',
          'model': 'model',
          'users': 'users',
          'audit': 'audit',
          'ai-ml': 'ai-ml',
          'ml-audit': 'ml-audit', 'ml-preprocessing': 'ml-preprocessing', 'ml-text': 'ml-text', 'ml-image': 'ml-image', 'ml-compare': 'ml-compare',
          'settings': 'settings',
        }
        return map[suffix] || 'ai-ml'
      })()
      setAdminPage(nextPage)
    }
    window.addEventListener('popstate', syncPage)
    return () => window.removeEventListener('popstate', syncPage)
  }, [])

  function navigateAdminPage(nextPage) {
    setAdminPage(nextPage)
    const workspace = role === 'REVIEWER' ? 'reviewer' : 'admin'
    const nextPath = nextPage === 'dashboard'
      ? `${import.meta.env.BASE_URL}${workspace}`
      : `${import.meta.env.BASE_URL}${workspace}/${nextPage}`
    window.history.pushState({}, '', nextPath)
  }

  function refresh() {
    setRefreshKey((value) => value + 1)
  }

  const allAdminNavigation = [
    ['customer-claims', 'Customer Claims'],
    ['classify', 'New Classification'],
    ['history', 'ML History'],
    ['model', 'Model Intelligence'],
    ['ai-ml', 'AI & ML'],
    ['ml-audit', 'ML · Audit'], ['ml-preprocessing', 'ML · Preprocessing'], ['ml-text', 'ML · Tuning models'], ['ml-image', 'ML · Image model'], ['ml-compare', 'ML · Compare'],
    ['settings', 'Rules & Alerts'],
    ...(role === 'ADMIN' ? [['users', 'Users'], ['audit', 'Audit Logs']] : []),
  ]

  const adminNavigation = role === 'SERVICE_CENTER'
    ? allAdminNavigation.filter(([key]) => ['profile', 'classify', 'history', 'model'].includes(key))
    : allAdminNavigation.filter(([key]) => ['profile', 'model', 'ai-ml', 'ml-audit', 'ml-preprocessing', 'ml-text', 'ml-image', 'ml-compare', 'settings', 'users', 'audit'].includes(key))

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            AX
          </div>

          <div>
            <h2>AssureX</h2>
            <p>Claim Engine</p>
          </div>
        </div>

        <div className="sidebar-section-label">
          Administration
        </div>

        <nav className="nav-menu">
          {adminNavigation.map(([key, label]) => (
              <button
                key={key}
                className={`nav-item ${
                  adminPage === key ? 'active' : ''
                }`}
                onClick={() => navigateAdminPage(key)}
              >
                {label}
              </button>
          ))}
        </nav>

        <div className="backend-status">
          <span
            className={`status-dot ${backendStatus}`}
          />
          API {backendStatus}
        </div>
        <a className="admin-customer-link" href={import.meta.env.BASE_URL}>
          Customer Portal
        </a>
        <button className="admin-logout-button" onClick={onLogout}>
          Log out
        </button>
      </aside>

      <main className="main-content">
        {adminPage === 'customer-claims' && role !== 'ADMIN' && (
          <AdminCustomerClaims
            refreshKey={refreshKey}
            onChanged={refresh}
            canReview={role === 'ADMIN' || role === 'REVIEWER'}
          />
        )}

        {adminPage === 'products' && (
          <AdminProducts refreshKey={refreshKey} />
        )}

        {adminPage === 'notifications' && (
          <WorkspaceNotifications refreshKey={refreshKey} />
        )}

        {adminPage === 'profile' && (
          <WorkspaceProfile email={email} role={role} />
        )}

        {adminPage === 'classify' && (
          <MLClassification onCreated={refresh} />
        )}

        {adminPage === 'history' && (
          <MLHistory refreshKey={refreshKey} />
        )}

        {adminPage === 'model' && (
          <ModelInfo />
        )}

        {adminPage === 'ai-ml' && (
          <AdminMLConsole />
        )}

        {['ml-audit', 'ml-preprocessing', 'ml-text', 'ml-image', 'ml-compare'].includes(adminPage) && (
          <MLPipelinePage page={adminPage} onNavigate={navigateAdminPage} />
        )}

        {adminPage === 'settings' && role === 'ADMIN' && (
          <AdminSettings />
        )}

        {adminPage === 'users' && role === 'ADMIN' && (
          <AdminUsers refreshKey={refreshKey} />
        )}

        {adminPage === 'audit' && role === 'ADMIN' && (
          <AdminAuditLog refreshKey={refreshKey} />
        )}
      </main>
    </div>
  )
}


export default App

export {
  PageHeader,
  StatCard,
  StatusBadge,
  LoadingState,
  EmptyState,
  formatDate,
  formatNumber,
  CustomerIdentity,
  CustomerHome,
  CustomerSubmit,
  CustomerClaims,
  ClaimTimeline,
}
