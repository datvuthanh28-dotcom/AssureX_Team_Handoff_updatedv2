import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { api } from './api'
import { claimFieldGroups } from './claimFields'


const MODEL_METRICS = {
  pythonAccuracy: '95.56%',
  pythonF1: '95.59%',
  pythonConfidence: '93.20%',
  gtmAccuracy: '81.33%',
  gtmF1: '81.29%',
  gtmConfidence: '87.74%',
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
      <p>{description}</p>
    </div>
  )
}


function PageHeader({
  eyebrow,
  title,
  description,
  action,
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {description && (
          <p className="page-description">
            {description}
          </p>
        )}
      </div>

      {action}
    </header>
  )
}


function StatCard({
  label,
  value,
  hint,
  tone = 'default',
}) {
  return (
    <article className={`stat-card tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </article>
  )
}


function AdminDashboard({
  onNavigate,
  refreshKey,
}) {
  const [mlClaims, setMlClaims] = useState([])
  const [customerClaims, setCustomerClaims] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api('/api/claims'),
      api('/api/customer/claims'),
    ])
      .then(([ml, customer]) => {
        setMlClaims(ml)
        setCustomerClaims(customer)
      })
      .finally(() => setLoading(false))
  }, [refreshKey])

  const review = customerClaims.filter(
    (claim) => ['Under Review', 'Manual Review'].includes(claim.status)
  ).length

  const approved = customerClaims.filter(
    (claim) => claim.status === 'Approved'
  ).length

  const rejected = customerClaims.filter(
    (claim) => claim.status === 'Rejected'
  ).length

  return (
    <>
      <PageHeader
        eyebrow="Operations overview"
        title="Admin Dashboard"
        description="Monitor incoming warranty claims, ML classifications and model performance."
        action={
          <button
            className="button primary"
            onClick={() => onNavigate('classify')}
          >
            + New Classification
          </button>
        }
      />

      <section className="hero-card">
        <div>
          <p className="eyebrow">
            Primary ML Model
          </p>

          <h2>Python Gradient Boosting</h2>

          <p>
            Final production classification model selected
            using Macro F1 on the locked 225-claim test set.
          </p>

          <div className="hero-actions">
            <button
              className="button secondary"
              onClick={() => onNavigate('model')}
            >
              View Model Intelligence
            </button>
          </div>
        </div>

        <div className="metric-highlight">
          <span>Test Accuracy</span>
          <strong>
            {MODEL_METRICS.pythonAccuracy}
          </strong>
          <small>SRS requirement passed</small>
        </div>
      </section>

      {loading ? (
        <LoadingState />
      ) : (
        <>
          <section className="stats-grid">
            <StatCard
              label="Customer Claims"
              value={customerClaims.length}
              hint="Total submitted"
            />

            <StatCard
              label="Under Review"
              value={review}
              hint="Requires staff attention"
              tone="warning"
            />

            <StatCard
              label="Approved"
              value={approved}
              hint="Approved customer claims"
              tone="success"
            />

            <StatCard
              label="Rejected"
              value={rejected}
              hint="Rejected customer claims"
              tone="danger"
            />
          </section>

          <section className="dashboard-grid">
            <article className="panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">
                    Customer Queue
                  </p>
                  <h2>Recent Claims</h2>
                </div>

                <button
                  className="text-button"
                  onClick={() =>
                    onNavigate('customer-claims')
                  }
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
                    .slice(0, 5)
                    .map((claim) => (
                      <div
                        className="compact-row"
                        key={claim.id}
                      >
                        <div>
                          <strong>
                            {claim.claim_id}
                          </strong>
                          <span>
                            {claim.customer_name}
                            {' · '}
                            {claim.product_name}
                          </span>
                        </div>

                        <StatusBadge
                          value={claim.status}
                        />
                      </div>
                    ))}
                </div>
              )}
            </article>

            <article className="panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">
                    Classification Engine
                  </p>
                  <h2>ML Activity</h2>
                </div>
              </div>

              <div className="model-summary">
                <div>
                  <span>Stored classifications</span>
                  <strong>{mlClaims.length}</strong>
                </div>

                <div>
                  <span>Macro F1</span>
                  <strong>
                    {MODEL_METRICS.pythonF1}
                  </strong>
                </div>

                <div>
                  <span>Mean confidence</span>
                  <strong>
                    {MODEL_METRICS.pythonConfidence}
                  </strong>
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
}) {
  const [claims, setClaims] = useState([])
  const [selected, setSelected] = useState(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] =
    useState('All')
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [reviewerComment, setReviewerComment] = useState('')
  const [reviewError, setReviewError] = useState('')

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
        ].some((value) =>
          String(value || '')
            .toLowerCase()
            .includes(term)
        )

      const matchesStatus =
        statusFilter === 'All' ||
        claim.status === statusFilter

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
      return
    }

    setUpdating(true)
    setReviewError('')

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

  return (
    <>
      <PageHeader
        eyebrow="Customer operations"
        title="Customer Claims"
        description="Review, search and update submitted warranty claims."
        action={
          <button className="button secondary" onClick={exportClaims} disabled={filtered.length === 0}>
            Export CSV
          </button>
        }
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
              placeholder="Search Claim ID, customer, product..."
            />
          </div>

          <select
            className="filter-select"
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(event.target.value)
            }
          >
            <option>All</option>
            <option>Under Review</option>
            <option>Manual Review</option>
            <option>Approved</option>
            <option>Rejected</option>
            <option>Additional Information Required</option>
            <option>Closed</option>
          </select>

          <span className="results-count">
            {filtered.length} claim(s)
          </span>
        </div>

        {loading ? (
          <LoadingState />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No matching claims"
            description="Try changing the search or status filter."
          />
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Claim ID</th>
                  <th>Customer</th>
                  <th>Product</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Submitted</th>
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
                    onClick={() =>
                      {
                        setSelected(claim)
                        setReviewerComment('')
                        setReviewError('')
                      }
                    }
                  >
                    <td className="mono">
                      {claim.claim_id}
                    </td>
                    <td>
                      <strong>
                        {claim.customer_name}
                      </strong>
                      <small>
                        {claim.email}
                      </small>
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
                Claim Detail
              </p>
              <h2>{selected.claim_id}</h2>
            </div>

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

          <div className="detail-grid">
            <div>
              <span>Customer</span>
              <strong>
                {selected.customer_name}
              </strong>
            </div>

            <div>
              <span>Email</span>
              <strong>{selected.email}</strong>
            </div>

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
            <span>Customer Description</span>
            <p>{selected.fault_description}</p>
          </div>

          {selected.decision && (
            <section className="claim-analysis">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">AI + Rule Analysis</p>
                  <h3>Assessment</h3>
                </div>
              </div>
              <div className="detail-grid">
                <div>
                  <span>Python prediction</span>
                  <strong>{selected.decision.ml_prediction}</strong>
                </div>
                <div>
                  <span>Python confidence</span>
                  <strong>{(selected.decision.ml_confidence * 100).toFixed(2)}%</strong>
                </div>
                <div>
                  <span>Final decision</span>
                  <strong>{selected.decision.final_decision}</strong>
                </div>
                <div>
                  <span>Model</span>
                  <strong>{selected.decision.model_name}</strong>
                </div>
                <div>
                  <span>Python model version</span>
                  <strong>{selected.decision.python_model_version || '—'}</strong>
                </div>
                <div>
                  <span>GTM model version</span>
                  <strong>{selected.decision.gtm_model_version || 'Not run'}</strong>
                </div>
                <div>
                  <span>Analysis timestamp</span>
                  <strong>{formatDate(selected.decision.analysis_timestamp)}</strong>
                </div>
              </div>
              {selected.decision.decision_reasons?.length > 0 && (
                <ul className="decision-reason-list">
                  {selected.decision.decision_reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              )}
              <details className="analysis-inputs">
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
            </section>
          )}

          <ClaimTimeline claimId={selected.claim_id} status={selected.status} />

          {canReview && <div className="decision-actions">
            <label className="review-note">
              Reviewer note
              <textarea
                rows="3"
                value={reviewerComment}
                onChange={(event) => setReviewerComment(event.target.value)}
                placeholder="Record the reason for this action"
              />
            </label>

            <div>
              <button
                className="button warning"
                disabled={updating}
                onClick={() =>
                  updateStatus('Under Review')
                }
              >
                Under Review
              </button>

              <button
                className="button success"
                disabled={updating}
                onClick={() =>
                  updateStatus('Approved')
                }
              >
                Approve
              </button>

              <button
                className="button danger"
                disabled={updating}
                onClick={() =>
                  updateStatus('Rejected')
                }
              >
                Reject
              </button>
              <button
                className="button warning"
                disabled={updating || !reviewerComment.trim()}
                onClick={() => updateStatus('Additional Information Required')}
              >
                Request More Information
              </button>
            </div>
          </div>}
          {reviewError && <div className="alert error">{reviewError}</div>}
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


function ModelInfo() {
  return (
    <>
      <PageHeader
        eyebrow="Model intelligence"
        title="Model Performance"
        description="Final locked-test comparison between the structured Python model and GTM G5."
      />

      <section className="hero-card">
        <div>
          <p className="eyebrow">
            Final Selection
          </p>
          <h2>Python Gradient Boosting</h2>
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
          hint="215 / 225 correct"
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
          value="10"
          hint="Across 225 claims"
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">
              Final Comparison
            </p>
            <h2>Python vs GTM G5</h2>
          </div>
        </div>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Python</th>
                <th>GTM G5</th>
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
                <td>10</td>
                <td>42</td>
              </tr>

              <tr>
                <td>SRS ≥ 85%</td>
                <td>
                  <StatusBadge value="PASS" />
                </td>
                <td>
                  <StatusBadge value="FAIL" />
                </td>
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
            <h2>G5 Ablation Summary</h2>
          </div>
        </div>

        <div className="split-info">
          <div>
            <span>Removed</span>
            <strong>
              DamageType, ExtendedWarranty,
              WarrantyDurationMonths
            </strong>
          </div>

          <div>
            <span>Removal rolled back</span>
            <strong>
              Brand, ClaimSubmissionChannel,
              ReceiptAvailable, PriorClaimCount
            </strong>
          </div>
        </div>
      </section>
    </>
  )
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
  const [form, setForm] = useState({
    name: '',
    category: '',
    brand: '',
    model: '',
    warranty_months: '',
  })

  useEffect(() => {
    api('/api/products')
      .then(setProducts)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [refreshKey])

  async function createProduct(event) {
    event.preventDefault()
    setError('')
    try {
      const product = await api('/api/products', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          warranty_months: Number(form.warranty_months),
        }),
      })
      setProducts((current) => [product, ...current])
      setForm({ name: '', category: '', brand: '', model: '', warranty_months: '' })
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  return (
    <>
      <PageHeader eyebrow="Catalog" title="Products" description="Product models, warranties, registered customers and active claims." />
      <form className="panel" onSubmit={createProduct}>
        <div className="panel-heading"><h2>Add product</h2></div>
        <div className="form-grid">
          <label className="form-field"><span>Product</span><input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label>
          <label className="form-field"><span>Category</span><input value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} required /></label>
          <label className="form-field"><span>Brand</span><input value={form.brand} onChange={(event) => setForm({ ...form, brand: event.target.value })} required /></label>
          <label className="form-field"><span>Model</span><input value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} required /></label>
          <label className="form-field"><span>Warranty months</span><input type="number" min="1" max="120" value={form.warranty_months} onChange={(event) => setForm({ ...form, warranty_months: event.target.value })} required /></label>
        </div>
        {error && <div className="alert error">{error}</div>}
        <div className="form-actions"><button className="button primary">Add product</button></div>
      </form>
      <section className="panel">
        {loading ? <LoadingState /> : products.length === 0 ? <EmptyState title="No products" description="Add a product to make it available for registration." /> : (
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Product</th><th>Category</th><th>Brand</th><th>Model</th><th>Warranty</th><th>Registered Customers</th><th>Active Claims</th></tr></thead><tbody>
            {products.map((product) => <tr key={product.id}><td>{product.name}</td><td>{product.category}</td><td>{product.brand}</td><td>{product.model}</td><td>{product.warranty_months} months</td><td>{product.registered_customers}</td><td>{product.active_claims}</td></tr>)}
          </tbody></table></div>
        )}
      </section>
    </>
  )
}


function AdminWarranties({ refreshKey }) {
  const [warranties, setWarranties] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/api/warranties')
      .then(setWarranties)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [refreshKey])

  async function toggleActive(warranty) {
    setError('')
    try {
      const updated = await api(`/api/warranties/${warranty.id}/active`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !warranty.is_active }),
      })
      setWarranties((current) => current.map((entry) =>
        entry.id === warranty.id ? { ...entry, ...updated } : entry
      ))
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  return (
    <>
      <PageHeader eyebrow="Coverage records" title="Warranties" description="Registered product coverage and active status." />
      <section className="panel">
        {error && <div className="alert error">{error}</div>}
        {loading ? <LoadingState /> : warranties.length === 0 ? <EmptyState title="No warranties" description="Warranty records are created when a customer registers a product." /> : (
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Customer</th><th>Product</th><th>Brand / Model</th><th>Serial</th><th>Start</th><th>End</th><th>Status</th><th /></tr></thead><tbody>
            {warranties.map((warranty) => <tr key={warranty.id}><td>{warranty.customer_email}</td><td>{warranty.product}</td><td>{warranty.brand} · {warranty.model}</td><td>{warranty.serial_number}</td><td>{warranty.start_date}</td><td>{warranty.end_date}</td><td>{warranty.is_active ? warranty.status : 'Inactive'}</td><td><button className="text-button" onClick={() => toggleActive(warranty)}>{warranty.is_active ? 'Deactivate' : 'Activate'}</button></td></tr>)}
          </tbody></table></div>
        )}
      </section>
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
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!email) {
      setClaims([])
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
        description="Submit warranty claims and track their progress."
        action={
          <button
            className="button primary"
            onClick={() => onNavigate('submit')}
          >
            + Submit Claim
          </button>
        }
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
          <p>
            Submit a warranty request, receive a claim ID,
            and follow the review status from submission to
            final decision.
          </p>
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
                  <div
                    className="compact-row"
                    key={claim.id}
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
                  </div>
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
  setEmail,
  onSubmitted,
  onNavigate,
}) {
  const [form, setForm] = useState({
    customer_name: '',
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
  })

  const [submitting, setSubmitting] =
    useState(false)

  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const [
    warrantyDocument,
    setWarrantyDocument,
  ] = useState(null)

  const [
    ocrOriginal,
    setOcrOriginal,
  ] = useState(null)

  const [
    ocrUploading,
    setOcrUploading,
  ] = useState(false)

  const [
    ocrError,
    setOcrError,
  ] = useState('')
  const [registeredProducts, setRegisteredProducts] = useState([])
  const [selectedProductId, setSelectedProductId] = useState('')

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
    form.receipt_available !== 'Yes' ? 'Receipt' : null,
    !warrantyDocument ? 'Warranty card' : null,
    form.product_image_available !== 'Yes' ? 'Product image' : null,
    !ocrOriginal?.serial_number ? 'Serial evidence' : null,
    form.fault_evidence_available !== 'Yes' ? 'Fault evidence' : null,
    form.previous_repair === 'Yes' && form.repair_report_available !== 'Yes'
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
      const previousRepair =
        form.previous_repair

      const payload = {
        customer_name:
          form.customer_name,

        email:
          form.email,

        product_name:
          form.product_name,

        model_number:
          form.model_number,

        serial_number:
          form.serial_number,

        purchase_date:
          form.purchase_date,

        fault_date:
          form.fault_date || null,

        damage_type:
          form.damage_type,

        claim_amount:
          form.claim_amount
            ? Number(form.claim_amount)
            : null,

        fault_description:
          form.fault_description,

        warranty_duration_months:
          form.warranty_duration_months
            ? Number(
                form.warranty_duration_months
              )
            : null,

        extended_warranty:
          'No',

        receipt_available:
          form.receipt_available,

        warranty_card_available:
          warrantyDocument
            ? 'Yes'
            : 'No',

        product_image_available:
          form.product_image_available,

        serial_evidence_available:
          ocrOriginal?.serial_number
            ? 'Yes'
            : 'No',

        fault_evidence_available:
          form.fault_evidence_available,

        evidence_serial_number:
          ocrOriginal?.serial_number ||
          null,

        evidence_model_number:
          ocrOriginal?.model_number ||
          null,

        previous_repair:
          previousRepair,

        repair_count:
          previousRepair === 'Yes'
            ? Number(
                form.repair_count || 0
              )
            : 0,

        repair_report_available:
          previousRepair === 'Yes'
            ? form
                .repair_report_available
            : 'Not Applicable',

        repair_authorized:
          previousRepair === 'Yes'
            ? form.repair_authorized
            : 'Not Applicable',

        ocr_confidence:
          warrantyDocument
            ?.ocr_confidence ??
          null,

        document_duplicate_indicator:
          'No',

        warranty_document_id:
          warrantyDocument
            ?.document_id ||
          null,

        warranty_ocr_data:
          ocrOriginal,

        warranty_ocr_confidence:
          warrantyDocument
            ?.ocr_confidence ??
          null,
      }

      const data = await api(
        '/api/customer/claims',
        {
          method: 'POST',
          body: JSON.stringify(
            payload
          ),
        }
      )

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
              <p className="eyebrow">
                Step 3
              </p>

              <h2>
                A Few Final Questions
              </h2>

              <p className="section-helper">
                These help AssureX determine
                whether additional review is
                needed.
              </p>
            </div>
          </div>

          <div className="form-grid">
            <label className="form-field">
              <span>
                Purchase receipt available?
              </span>

              <select
                name="receipt_available"
                value={
                  form.receipt_available
                }
                onChange={change}
                required
              >
                <option value="">
                  Select...
                </option>

                {yesNoOptions.map(
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
            </label>

            <label className="form-field">
              <span>
                Product photo available?
              </span>

              <select
                name="product_image_available"
                value={
                  form
                    .product_image_available
                }
                onChange={change}
                required
              >
                <option value="">
                  Select...
                </option>

                {yesNoOptions.map(
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
            </label>

            <label className="form-field">
              <span>
                Fault / damage photo
                available?
              </span>

              <select
                name="fault_evidence_available"
                value={
                  form
                    .fault_evidence_available
                }
                onChange={change}
                required
              >
                <option value="">
                  Select...
                </option>

                {yesNoOptions.map(
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
            </label>

            <label className="form-field">
              <span>
                Has this product been
                repaired before?
              </span>

              <select
                name="previous_repair"
                value={
                  form.previous_repair
                }
                onChange={change}
                required
              >
                <option value="No">
                  No
                </option>

                <option value="Yes">
                  Yes
                </option>
              </select>
            </label>

            {form.previous_repair ===
              'Yes' && (
              <>
                <label className="form-field">
                  <span>
                    Previous Repair Count
                  </span>

                  <input
                    type="number"
                    min="1"
                    name="repair_count"
                    value={
                      form.repair_count
                    }
                    onChange={change}
                    required
                  />
                </label>

                <label className="form-field">
                  <span>
                    Repair Report
                    Available?
                  </span>

                  <select
                    name="repair_report_available"
                    value={
                      form
                        .repair_report_available
                    }
                    onChange={change}
                    required
                  >
                    <option value="">
                      Select...
                    </option>

                    <option value="Yes">
                      Yes
                    </option>

                    <option value="No">
                      No
                    </option>
                  </select>
                </label>

                <label className="form-field">
                  <span>
                    Repaired by Authorized
                    Center?
                  </span>

                  <select
                    name="repair_authorized"
                    value={
                      form
                        .repair_authorized
                    }
                    onChange={change}
                    required
                  >
                    <option value="">
                      Select...
                    </option>

                    <option value="Yes">
                      Yes
                    </option>

                    <option value="No">
                      No
                    </option>

                    <option value="Unknown">
                      Not sure
                    </option>
                  </select>
                </label>
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

          <button
            className="button primary large"
            disabled={submitting || missingInformation.length > 0}
          >
            {submitting
              ? 'Evaluating Claim...'
              : 'Submit Claim'}
          </button>
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
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!email) {
      setClaims([])
      setSelected(null)
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
        description="Track your submitted warranty claims and review their current status."
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
            description="Enter the email used when submitting your warranty claim."
          />
        ) : claims.length === 0 ? (
          <EmptyState
            title="No claims found"
            description="There are no warranty claims associated with this email."
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
              <p className="eyebrow">AI + Rule Analysis</p>
              <div className="detail-grid">
                <div>
                  <span>Python prediction</span>
                  <strong>{selected.decision.ml_prediction}</strong>
                </div>
                <div>
                  <span>Python confidence</span>
                  <strong>{(selected.decision.ml_confidence * 100).toFixed(2)}%</strong>
                </div>
                <div>
                  <span>Final decision</span>
                  <strong>{selected.decision.final_decision}</strong>
                </div>
                <div>
                  <span>Python model version</span>
                  <strong>{selected.decision.python_model_version || '—'}</strong>
                </div>
                <div>
                  <span>GTM model version</span>
                  <strong>{selected.decision.gtm_model_version || 'Not run'}</strong>
                </div>
                <div>
                  <span>Analysis timestamp</span>
                  <strong>{formatDate(selected.decision.analysis_timestamp)}</strong>
                </div>
              </div>
              {selected.decision.decision_reasons?.length > 0 && (
                <ul className="decision-reason-list">
                  {selected.decision.decision_reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              )}
              <details className="analysis-inputs">
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
              <p className="reviewer-summary">
                Reviewer: {selected.decision.reviewer_decision || 'No override'}
                {selected.decision.reviewer_comment && ` · ${selected.decision.reviewer_comment}`}
              </p>
            </div>
          )}

          <div className="detail-grid">
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


function App({ onLogout, role, email }) {
  const [backendStatus, setBackendStatus] =
    useState('checking')

  const [adminPage, setAdminPage] =
    useState('dashboard')

  const [refreshKey, setRefreshKey] =
    useState(0)

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

  function refresh() {
    setRefreshKey((value) => value + 1)
  }

  const allAdminNavigation = [
    ['dashboard', 'Dashboard'],
    ['customer-claims', 'Customer Claims'],
    ['products', 'Products'],
    ['warranties', 'Warranties'],
    ['notifications', 'Notifications'],
    ['classify', 'New Classification'],
    ['history', 'ML History'],
    ['model', 'Model Intelligence'],
    ...(role === 'ADMIN' ? [['users', 'Users'], ['audit', 'Audit Logs']] : []),
  ]

  const adminNavigation = role === 'REVIEWER'
    ? allAdminNavigation.filter(([key]) => ['dashboard', 'customer-claims', 'products', 'warranties', 'notifications', 'profile'].includes(key))
    : role === 'SERVICE_CENTER'
      ? allAdminNavigation.filter(([key]) => ['dashboard', 'customer-claims', 'products', 'warranties', 'notifications', 'profile', 'classify', 'history', 'model'].includes(key))
      : [...allAdminNavigation, ['profile', 'Profile']]

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
                onClick={() => setAdminPage(key)}
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
        {adminPage === 'dashboard' && (
          <AdminDashboard
            onNavigate={setAdminPage}
            refreshKey={refreshKey}
          />
        )}

        {adminPage === 'customer-claims' && (
          <AdminCustomerClaims
            refreshKey={refreshKey}
            onChanged={refresh}
            canReview={role === 'ADMIN' || role === 'REVIEWER'}
          />
        )}

        {adminPage === 'products' && (
          <AdminProducts refreshKey={refreshKey} />
        )}

        {adminPage === 'warranties' && (
          <AdminWarranties refreshKey={refreshKey} />
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
