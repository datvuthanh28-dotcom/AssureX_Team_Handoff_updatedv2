import React, { useState, useEffect, useMemo } from 'react'
import { api } from './api'
import { MODEL_14_FEATURES, claim14FieldGroups, CLAIM_PRESETS } from './claimFields'

// Allowed constants matching SRS and Backend validation
export const ALLOWED_PRODUCT_TYPES = [
  'Laptop',
  'Smartphone',
  'Tablet',
  'Monitor',
  'Printer',
  'Other',
]

export const ALLOWED_PROBLEM_CATEGORIES = [
  'Power / Cannot Turn On',
  'Battery',
  'Screen / Display',
  'Keyboard',
  'Performance',
  'Software',
  'Network / Connectivity',
  'Overheating',
  'Physical Damage',
  'Other',
]

// Default feature values matching V3 ML model
const DEFAULT_14_FEATURES = {
  ProductIdentityMatch: 'Yes',
  SerialNumberMatch: 'Yes',
  ProductModelConsistent: 'Yes',
  WarrantyRemainingDays: 180,
  FaultCovered: 'Yes',
  ClaimReportingDelayDays: 3,
  ClaimReportingWithinPeriod: 'Yes',
  RepairAuthorized: 'Not Applicable',
  DuplicateClaimIndicator: 'No',
  ContradictionIndicator: 'No',
  RequiredDocumentsComplete: 'Yes',
  MissingDocumentCount: 0,
  OCRConfidence: 0.95,
  OCRQualityBand: 'High',
}

// ==============================================================================
// 1. CUSTOMER - WARRANTY CLAIM FORM (STRICTLY 14 MODEL FEATURES - NO IMAGE UPLOAD)
// ==============================================================================

export function CustomerWarrantyClaimForm({ onCreated, onCancel }) {
  // Metadata context
  const [meta, setMeta] = useState({
    product_type: 'Laptop',
    product_model: 'Lenovo ThinkPad T14 Gen 4',
    order_code: 'ORD-2026-88192',
    purchase_date: new Date().toISOString().split('T')[0],
    usage_duration: 6,
    problem_category: 'Screen / Display',
    problem_description: 'Screen displays flickering horizontal lines continuously after startup, device has no physical impact or liquid damage.',
  })

  // The 14 Features finalized during ML Model training
  const [features, setFeatures] = useState({ ...DEFAULT_14_FEATURES })

  const [activePreset, setActivePreset] = useState('valid')
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [createdTicket, setCreatedTicket] = useState(null)
  const [submitError, setSubmitError] = useState('')

  function handleFeatureChange(name, value) {
    setFeatures((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }))
    }
  }

  function handleMetaChange(field, value) {
    setMeta((prev) => ({ ...prev, [field]: value }))
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }))
    }
  }

  function applyPreset(preset) {
    setActivePreset(preset.id)
    setFeatures({ ...preset.features })
    if (preset.meta) {
      setMeta((prev) => ({ ...prev, ...preset.meta }))
    }
    setErrors({})
    setSubmitError('')
  }

  // Frontend Validation for the 14 features and essential fields
  function validate() {
    const errs = {}

    // Product Model
    if (!meta.product_model || meta.product_model.trim().length < 2) {
      errs.product_model = 'Please enter product model name (minimum 2 characters).'
    }

    // OCR Confidence (0.0 to 1.0)
    const ocrConf = Number(features.OCRConfidence)
    if (isNaN(ocrConf) || ocrConf < 0 || ocrConf > 1) {
      errs.OCRConfidence = 'OCR Confidence must be a valid number between 0.00 and 1.00.'
    }

    // Delay Days (>= 0)
    const delay = Number(features.ClaimReportingDelayDays)
    if (isNaN(delay) || delay < 0) {
      errs.ClaimReportingDelayDays = 'Reporting delay days cannot be negative.'
    }

    // Missing Document Count (>= 0)
    const missingDocs = Number(features.MissingDocumentCount)
    if (isNaN(missingDocs) || missingDocs < 0) {
      errs.MissingDocumentCount = 'Missing document count cannot be negative.'
    }

    // Warranty Remaining Days (number)
    const remainingDays = Number(features.WarrantyRemainingDays)
    if (isNaN(remainingDays)) {
      errs.WarrantyRemainingDays = 'Warranty remaining days must be a valid integer.'
    }

    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitError('')

    if (!validate()) {
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        // Context metadata
        product_type: meta.product_type,
        product_model: meta.product_model.trim(),
        order_code: meta.order_code ? meta.order_code.trim() : null,
        purchase_date: meta.purchase_date,
        usage_duration: parseInt(meta.usage_duration, 10) || 1,
        problem_category: meta.problem_category,
        problem_description: meta.problem_description ? meta.problem_description.trim() : '',

        // THE 14 FINAL ML FEATURES
        ProductIdentityMatch: features.ProductIdentityMatch,
        SerialNumberMatch: features.SerialNumberMatch,
        ProductModelConsistent: features.ProductModelConsistent,
        WarrantyRemainingDays: Number(features.WarrantyRemainingDays),
        FaultCovered: features.FaultCovered,
        ClaimReportingDelayDays: Number(features.ClaimReportingDelayDays),
        ClaimReportingWithinPeriod: features.ClaimReportingWithinPeriod,
        RepairAuthorized: features.RepairAuthorized,
        DuplicateClaimIndicator: features.DuplicateClaimIndicator,
        ContradictionIndicator: features.ContradictionIndicator,
        RequiredDocumentsComplete: features.RequiredDocumentsComplete,
        MissingDocumentCount: Number(features.MissingDocumentCount),
        OCRConfidence: Number(features.OCRConfidence),
        OCRQualityBand: features.OCRQualityBand,
      }

      const response = await api('/api/warranty/claims', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      if (response && response.ticket) {
        setCreatedTicket(response.ticket)
        if (onCreated) onCreated(response.ticket)
      } else {
        throw new Error('Invalid response format from server.')
      }
    } catch (err) {
      if (err.errors && typeof err.errors === 'object') {
        setErrors((prev) => ({ ...prev, ...err.errors }))
      }
      setSubmitError(err.message || 'Unable to submit warranty claim.')
    } finally {
      setSubmitting(false)
    }
  }

  function resetForm() {
    setFeatures({ ...DEFAULT_14_FEATURES })
    setErrors({})
    setCreatedTicket(null)
    setSubmitError('')
    setActivePreset('valid')
  }

  // ============================================================================
  // SUCCESS SCREEN
  // ============================================================================
  if (createdTicket) {
    const isWarranty = createdTicket.ai_prediction === 'WARRANTY'
    const isNotWarranty = createdTicket.ai_prediction === 'NOT_WARRANTY'
    const isReview = createdTicket.ai_prediction === 'REVIEW_REQUIRED'

    return (
      <div
        className="ticket-success-card"
        style={{
          background: 'var(--ax-surface, #ffffff)',
          border: '1px solid var(--ax-border, #e2e8f0)',
          borderRadius: '12px',
          padding: '36px',
          maxWidth: '720px',
          margin: '20px auto',
          boxShadow: '0 8px 30px rgba(0,0,0,0.06)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: isWarranty ? 'rgba(34, 197, 94, 0.15)' : isNotWarranty ? 'rgba(239, 68, 68, 0.15)' : 'rgba(234, 179, 8, 0.15)',
              color: isWarranty ? '#16a34a' : isNotWarranty ? '#dc2626' : '#ca8a04',
              fontSize: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
            }}
          >
            {isWarranty ? '✓' : isNotWarranty ? '✕' : '⏳'}
          </div>
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 800 }}>
            {isWarranty
              ? 'Claim Submitted · Warranty Eligible'
              : isNotWarranty
                ? 'Claim Submitted · Ineligible Under Policy'
                : 'Claim Submitted · Awaiting Reviewer Decision'}
          </h2>
        </div>

        {/* Ticket Summary Details */}
        <div
          style={{
            background: 'var(--ax-surface-alt, #f8fafc)',
            borderRadius: '10px',
            padding: '20px',
            marginBottom: '24px',
            border: '1px solid var(--ax-border, #cbd5e1)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontSize: '13px', color: 'var(--ax-text-soft, #475569)' }}>Claim Ticket ID:</span>
            <strong className="mono" style={{ fontSize: '16px', color: '#2563eb' }}>
              {createdTicket.ticket_id}
            </strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontSize: '13px', color: 'var(--ax-text-soft, #475569)' }}>Device:</span>
            <strong>{createdTicket.product_type} · {createdTicket.product_model}</strong>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontSize: '13px', color: 'var(--ax-text-soft, #475569)' }}>AI Model Prediction:</span>
            <span
              style={{
                fontWeight: 800,
                fontSize: '13px',
                padding: '4px 12px',
                borderRadius: '6px',
                background: isWarranty ? '#dcfce7' : isNotWarranty ? '#fee2e2' : '#fef9c3',
                color: isWarranty ? '#15803d' : isNotWarranty ? '#b91c1c' : '#a16207',
                border: `1px solid ${isWarranty ? '#86efac' : isNotWarranty ? '#fca5a5' : '#fde047'}`,
              }}
            >
              {createdTicket.ai_prediction}
              {createdTicket.ai_confidence != null && ` (${(createdTicket.ai_confidence * 100).toFixed(0)}%)`}
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '13px', color: 'var(--ax-text-soft, #475569)' }}>Workflow Status:</span>
            <span style={{ fontWeight: 700, fontSize: '13px', color: '#ea580c' }}>
              ⏳ {createdTicket.status === 'WAITING_REVIEW' ? 'Awaiting Reviewer Decision' : createdTicket.status}
            </span>
          </div>
        </div>

        {/* 14 Features Applied Snapshot */}
        <details style={{ marginBottom: '24px', fontSize: '13px' }}>
          <summary style={{ cursor: 'pointer', fontWeight: 600, color: '#2563eb' }}>
            Review 14 features evaluated by AI Model ▾
          </summary>
          <div
            style={{
              marginTop: '10px',
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '8px',
              background: '#ffffff',
              padding: '12px',
              borderRadius: '8px',
              border: '1px solid var(--ax-border, #e2e8f0)',
            }}
          >
            {MODEL_14_FEATURES.map((feat) => {
              const val = createdTicket.model_features?.[feat] ?? features[feat]
              return (
                <div key={feat} style={{ padding: '6px 8px', background: '#f8fafc', borderRadius: '4px', fontSize: '12px' }}>
                  <div style={{ color: 'var(--ax-text-faint, #64748b)', fontSize: '11px' }}>{feat}</div>
                  <strong style={{ color: '#0f172a' }}>{String(val)}</strong>
                </div>
              )
            })}
          </div>
        </details>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <button className="button primary" onClick={resetForm} style={{ minWidth: '180px' }}>
            Submit Another Claim
          </button>
          {onCancel && (
            <button className="button secondary" onClick={onCancel}>
              Back to Home
            </button>
          )}
        </div>
      </div>
    )
  }

  // ============================================================================
  // MAIN FORM (14 FEATURES - PURE FORM INPUT, ZERO IMAGE/CAMERA UPLOAD)
  // ============================================================================
  return (
    <div className="warranty-claim-container" style={{ maxWidth: '880px', margin: '0 auto', padding: '16px' }}>
      <div className="panel" style={{ padding: '32px', borderRadius: '14px', background: '#ffffff', border: '1px solid var(--ax-border, #e2e8f0)', boxShadow: '0 4px 20px rgba(0,0,0,0.04)' }}>
        {/* Header */}
        <div className="panel-heading" style={{ marginBottom: '20px' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 800 }}>
              Warranty Claim Request
            </h1>
          </div>
        </div>

        {/* 1-Click Test Presets */}
        <div
          style={{
            background: 'var(--ax-surface-alt, #f8fafc)',
            borderRadius: '10px',
            padding: '16px',
            marginBottom: '26px',
            border: '1px solid var(--ax-border, #e2e8f0)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              ⚡ 1-Click Test Presets:
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
            {CLAIM_PRESETS.map((preset) => {
              const isSelected = activePreset === preset.id
              const toneBg = preset.tone === 'success' ? '#dcfce7' : preset.tone === 'warning' ? '#fef9c3' : '#fee2e2'
              const toneBorder = preset.tone === 'success' ? '#86efac' : preset.tone === 'warning' ? '#fde047' : '#fca5a5'
              const toneText = preset.tone === 'success' ? '#15803d' : preset.tone === 'warning' ? '#a16207' : '#b91c1c'

              return (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => applyPreset(preset)}
                  style={{
                    textAlign: 'left',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    border: `2px solid ${isSelected ? '#2563eb' : 'var(--ax-border, #e2e8f0)'}`,
                    background: isSelected ? 'rgba(37, 99, 235, 0.05)' : '#ffffff',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontSize: '13px', color: '#0f172a' }}>{preset.name}</strong>
                    <span
                      style={{
                        fontSize: '10.5px',
                        fontWeight: 700,
                        padding: '1px 6px',
                        borderRadius: '4px',
                        background: toneBg,
                        border: `1px solid ${toneBorder}`,
                        color: toneText,
                      }}
                    >
                      {preset.badge}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {submitError && (
          <div
            className="alert error"
            style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid #ef4444',
              color: '#dc2626',
              padding: '12px 16px',
              borderRadius: '8px',
              marginBottom: '20px',
              fontSize: '13px',
            }}
          >
            <strong>Error submitting claim:</strong> {submitError}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          {/* SECTION 0: PRODUCT CONTEXT INFORMATION */}
          <div
            style={{
              marginBottom: '24px',
              padding: '18px',
              background: '#f8fafc',
              borderRadius: '10px',
              border: '1px solid var(--ax-border, #e2e8f0)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <span style={{ fontSize: '16px' }}>📦</span>
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>
                Device Identification
              </h3>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
              {/* Product Type */}
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '12.5px', fontWeight: 600 }}>
                  Product Category <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <select
                  value={meta.product_type}
                  onChange={(e) => handleMetaChange('product_type', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--ax-border, #cbd5e1)',
                    fontSize: '13px',
                  }}
                >
                  {ALLOWED_PRODUCT_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              {/* Product Model */}
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '12.5px', fontWeight: 600 }}>
                  Product Model <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. ThinkPad T14 Gen 4"
                  value={meta.product_model}
                  onChange={(e) => handleMetaChange('product_model', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    border: `1px solid ${errors.product_model ? '#ef4444' : 'var(--ax-border, #cbd5e1)'}`,
                    fontSize: '13px',
                  }}
                />
                {errors.product_model && (
                  <span style={{ display: 'block', color: '#ef4444', fontSize: '11px', marginTop: '3px' }}>
                    {errors.product_model}
                  </span>
                )}
              </div>

              {/* Order / Serial Code */}
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '12.5px', fontWeight: 600 }}>
                  Order ID / Serial Number (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. ORD-2026-88192"
                  value={meta.order_code}
                  onChange={(e) => handleMetaChange('order_code', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--ax-border, #cbd5e1)',
                    fontSize: '13px',
                  }}
                />
              </div>

              {/* Problem Category */}
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '12.5px', fontWeight: 600 }}>
                  Technical Issue Category
                </label>
                <select
                  value={meta.problem_category}
                  onChange={(e) => handleMetaChange('problem_category', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--ax-border, #cbd5e1)',
                    fontSize: '13px',
                  }}
                >
                  {ALLOWED_PROBLEM_CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* THE 14 FEATURES ORGANIZED IN 4 CARDS */}
          {claim14FieldGroups.map((group, groupIdx) => (
            <div
              key={group.title}
              style={{
                marginBottom: '22px',
                padding: '20px',
                borderRadius: '10px',
                border: '1px solid var(--ax-border, #e2e8f0)',
                background: '#ffffff',
              }}
            >
              <div style={{ marginBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      background: '#eff6ff',
                      color: '#2563eb',
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '12px',
                      fontWeight: 800,
                    }}
                  >
                    {groupIdx + 1}
                  </span>
                  <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: '#1e293b' }}>
                    {group.title}
                  </h3>
                </div>
              </div>

              {/* Fields Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
                {group.fields.map((field) => {
                  const val = features[field.name]
                  const hasErr = Boolean(errors[field.name])

                  return (
                    <div key={field.name} style={{ display: 'flex', flexDirection: 'column' }}>
                      <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>
                        {field.label}
                      </label>

                      {field.type === 'select' ? (
                        <select
                          value={val}
                          onChange={(e) => handleFeatureChange(field.name, e.target.value)}
                          style={{
                            width: '100%',
                            padding: '8px 10px',
                            borderRadius: '6px',
                            border: `1px solid ${hasErr ? '#ef4444' : 'var(--ax-border, #cbd5e1)'}`,
                            fontSize: '13px',
                            background: '#ffffff',
                          }}
                        >
                          {field.options.map((opt) => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="number"
                          step={field.step || 1}
                          min={field.min != null ? field.min : undefined}
                          max={field.max != null ? field.max : undefined}
                          value={val}
                          onChange={(e) => handleFeatureChange(field.name, e.target.value)}
                          style={{
                            width: '100%',
                            padding: '8px 10px',
                            borderRadius: '6px',
                            border: `1px solid ${hasErr ? '#ef4444' : 'var(--ax-border, #cbd5e1)'}`,
                            fontSize: '13px',
                            background: '#ffffff',
                          }}
                        />
                      )}

                      {hasErr && (
                        <span style={{ color: '#ef4444', fontSize: '11px', marginTop: '3px' }}>
                          {errors[field.name]}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}

          {/* Problem Description */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>
              Detailed Symptom / Defect Description:
            </label>
            <textarea
              rows="3"
              placeholder="Describe the hardware issue, symptoms observed, and any initial troubleshooting steps..."
              value={meta.problem_description}
              onChange={(e) => handleMetaChange('problem_description', e.target.value)}
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--ax-border, #cbd5e1)',
                fontSize: '13px',
                fontFamily: 'inherit',
                lineHeight: 1.5,
              }}
            />
          </div>

          {/* Form Actions */}
          <div
            style={{
              display: 'flex',
              gap: '12px',
              alignItems: 'center',
              justifyContent: 'flex-end',
              borderTop: '1px solid var(--ax-border, #e2e8f0)',
              paddingTop: '20px',
            }}
          >
            {onCancel && (
              <button type="button" className="button secondary" onClick={onCancel} disabled={submitting}>
                Cancel
              </button>
            )}
            <button
              type="submit"
              className="button primary"
              disabled={submitting}
              style={{ minWidth: '220px', padding: '12px 20px', fontSize: '14px', fontWeight: 700 }}
            >
              {submitting ? 'Submitting & Evaluating AI Model...' : 'Submit Warranty Claim →'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ==============================================================================
// 2. REVIEWER - DASHBOARD QUEUE & SPLIT DETAIL VIEW (14 FEATURES DISPLAY)
// ==============================================================================

export function ReviewerWarrantyDesk() {
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedTicket, setSelectedTicket] = useState(null)

  // Filters
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL_QUEUE')
  const [predFilter, setPredFilter] = useState('ALL')
  const [typeFilter, setTypeFilter] = useState('ALL')

  // Review Decision State
  const [decisionModal, setDecisionModal] = useState(null) // 'APPROVE' | 'REJECT' | null
  const [reviewerNote, setReviewerNote] = useState('')
  const [submittingDecision, setSubmittingDecision] = useState(false)
  const [decisionFeedback, setDecisionFeedback] = useState('')

  useEffect(() => {
    loadTickets()
  }, [])

  async function loadTickets() {
    setLoading(true)
    setError('')
    try {
      const data = await api('/api/warranty/claims')
      const list = Array.isArray(data) ? data : data?.tickets || []
      setTickets(list)
    } catch (err) {
      setError(err.message || 'Unable to load warranty tickets.')
    } finally {
      setLoading(false)
    }
  }

  // Filtered tickets
  const filteredTickets = useMemo(() => {
    return tickets.filter((t) => {
      // Status filter
      if (statusFilter === 'ALL_QUEUE') {
        if (!['WAITING_REVIEW', 'REVIEW_REQUIRED', 'AI_ERROR'].includes(t.status)) return false
      } else if (statusFilter !== 'ALL') {
        if (t.status !== statusFilter) return false
      }

      // Prediction filter
      if (predFilter !== 'ALL' && t.ai_prediction !== predFilter) {
        return false
      }

      // Product Type filter
      if (typeFilter !== 'ALL' && t.product_type !== typeFilter) {
        return false
      }

      // Search text
      if (search.trim()) {
        const query = search.trim().toLowerCase()
        const matchId = (t.ticket_id || '').toLowerCase().includes(query)
        const matchModel = (t.product_model || '').toLowerCase().includes(query)
        const matchOrder = (t.order_code || '').toLowerCase().includes(query)
        const matchDesc = (t.problem_description || '').toLowerCase().includes(query)
        if (!matchId && !matchModel && !matchOrder && !matchDesc) return false
      }

      return true
    })
  }, [tickets, statusFilter, predFilter, typeFilter, search])

  // KPIs
  const kpis = useMemo(() => {
    const queue = tickets.filter((t) => ['WAITING_REVIEW', 'REVIEW_REQUIRED', 'AI_ERROR'].includes(t.status))
    const lowConf = queue.filter((t) => (t.ai_confidence != null && t.ai_confidence < 0.70) || t.ai_prediction === 'REVIEW_REQUIRED')
    const aiError = queue.filter((t) => t.status === 'AI_ERROR')
    const reviewed = tickets.filter((t) => t.status === 'REVIEWED' && t.ground_truth != null)
    return {
      queueCount: queue.length,
      lowConfCount: lowConf.length,
      errorCount: aiError.length,
      reviewedCount: reviewed.length,
    }
  }, [tickets])

  async function handleConfirmDecision() {
    if (!selectedTicket || !decisionModal) return
    setSubmittingDecision(true)
    setDecisionFeedback('')

    try {
      const payload = {
        decision: decisionModal,
        reviewer_note: reviewerNote.trim() || undefined,
      }

      const res = await api(`/api/warranty/reviewer/tickets/${encodeURIComponent(selectedTicket.ticket_id)}/decision`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      if (res && res.ticket) {
        // Update local ticket list
        setTickets((curr) =>
          curr.map((item) => (item.ticket_id === res.ticket.ticket_id ? { ...item, ...res.ticket } : item))
        )
        setSelectedTicket((prev) => ({ ...prev, ...res.ticket }))
        setDecisionModal(null)
        setReviewerNote('')
        setDecisionFeedback(`Decision successfully recorded! Ground Truth established as '${res.ticket.ground_truth}'.`)
        setTimeout(() => setDecisionFeedback(''), 5000)
      }
    } catch (err) {
      alert(`Failed to confirm decision: ${err.message}`)
    } finally {
      setSubmittingDecision(false)
    }
  }

  function getPredColor(pred) {
    if (pred === 'WARRANTY') return { bg: '#dcfce7', text: '#15803d', border: '#bbf7d0' }
    if (pred === 'NOT_WARRANTY') return { bg: '#fee2e2', text: '#b91c1c', border: '#fecaca' }
    if (pred === 'REVIEW_REQUIRED') return { bg: '#fef9c3', text: '#a16207', border: '#fef08a' }
    return { bg: '#f1f5f9', text: '#475569', border: '#e2e8f0' }
  }

  // ----------------------------------------------------------------------------
  // VIEW B: REVIEWER DETAIL PAGE (2-COLUMN SPLIT VIEW)
  // ----------------------------------------------------------------------------
  if (selectedTicket) {
    const isReviewed = selectedTicket.status === 'REVIEWED' && selectedTicket.ground_truth != null
    const confidence = selectedTicket.ai_confidence
    const isLowConfidence = confidence != null && confidence < 0.70
    const predStyle = getPredColor(selectedTicket.ai_prediction)
    const feats = selectedTicket.model_features || {}

    return (
      <div className="reviewer-detail-view" style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px' }}>
        {/* Breadcrumb Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
          <button
            className="button secondary"
            onClick={() => {
              setSelectedTicket(null)
              setDecisionFeedback('')
            }}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            ← Back to Ticket Queue
          </button>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', color: 'var(--ax-text-faint, #64748b)' }}>Processing status:</span>
            <span
              style={{
                fontWeight: 700,
                fontSize: '12px',
                padding: '3px 10px',
                borderRadius: '20px',
                background: isReviewed ? '#dcfce7' : '#fff7ed',
                color: isReviewed ? '#15803d' : '#ea580c',
                border: `1px solid ${isReviewed ? '#bbf7d0' : '#fed7aa'}`,
              }}
            >
              {selectedTicket.status}
            </span>
          </div>
        </div>

        {decisionFeedback && (
          <div
            className="alert success"
            style={{
              background: '#dcfce7',
              border: '1px solid #86efac',
              color: '#15803d',
              padding: '12px 18px',
              borderRadius: '8px',
              marginBottom: '18px',
              fontSize: '13.5px',
            }}
          >
            ✓ {decisionFeedback}
          </div>
        )}

        {/* 2-COLUMN SPLIT GRID */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 0.8fr)',
            gap: '24px',
            alignItems: 'start',
          }}
        >
          {/* ================================================================= */}
          {/* LEFT COLUMN – CUSTOMER DATA & 14 MODEL FEATURES */}
          {/* ================================================================= */}
          <div
            className="panel"
            style={{
              padding: '24px',
              borderRadius: '12px',
              background: 'var(--ax-surface, #ffffff)',
              border: '1px solid var(--ax-border, #e2e8f0)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '16px' }}>
              <div>
                <p className="eyebrow" style={{ color: '#2563eb', fontWeight: 700, fontSize: '11px', letterSpacing: '0.06em', margin: 0 }}>
                  CUSTOMER INPUT DATA (14 FEATURES)
                </p>
                <h2 style={{ margin: '4px 0 0', fontSize: '20px' }}>
                  Claim Record · <span className="mono" style={{ color: '#2563eb' }}>{selectedTicket.ticket_id}</span>
                </h2>
              </div>
              <span style={{ fontSize: '12px', color: 'var(--ax-text-faint, #64748b)' }}>
                {selectedTicket.created_at ? new Date(selectedTicket.created_at).toLocaleString() : ''}
              </span>
            </div>

            {/* General Equipment Info */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '12px',
                background: 'var(--ax-surface-alt, #f8fafc)',
                padding: '14px 16px',
                borderRadius: '8px',
                border: '1px solid var(--ax-border, #e2e8f0)',
                marginBottom: '18px',
                fontSize: '13px',
              }}
            >
              <div>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--ax-text-faint, #64748b)', fontWeight: 600 }}>Device</span>
                <div style={{ fontWeight: 700, marginTop: '2px' }}>{selectedTicket.product_type} · {selectedTicket.product_model}</div>
              </div>
              <div>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--ax-text-faint, #64748b)', fontWeight: 600 }}>Issue Category</span>
                <div style={{ fontWeight: 700, marginTop: '2px' }}>{selectedTicket.problem_category}</div>
              </div>
              {selectedTicket.order_code && (
                <div>
                  <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--ax-text-faint, #64748b)', fontWeight: 600 }}>Order ID / Serial</span>
                  <div style={{ fontWeight: 700, marginTop: '2px' }} className="mono">{selectedTicket.order_code}</div>
                </div>
              )}
              <div>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--ax-text-faint, #64748b)', fontWeight: 600 }}>Usage Duration</span>
                <div style={{ fontWeight: 700, marginTop: '2px' }}>{selectedTicket.usage_duration} months</div>
              </div>
            </div>

            {/* Problem Description */}
            {selectedTicket.problem_description && (
              <div style={{ marginBottom: '20px' }}>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--ax-text-faint, #64748b)', fontWeight: 600 }}>
                  Customer Problem Description:
                </span>
                <div
                  style={{
                    marginTop: '4px',
                    padding: '10px 14px',
                    background: 'var(--ax-surface-alt, #f8fafc)',
                    borderRadius: '6px',
                    border: '1px solid var(--ax-border, #e2e8f0)',
                    fontSize: '13px',
                    lineHeight: 1.5,
                  }}
                >
                  {selectedTicket.problem_description}
                </div>
              </div>
            )}

            {/* 14 Features Grouped Display */}
            <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 700, color: '#334155' }}>
              14 Features Evaluated by ML Model:
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {claim14FieldGroups.map((grp) => (
                <div
                  key={grp.title}
                  style={{
                    border: '1px solid var(--ax-border, #e2e8f0)',
                    borderRadius: '8px',
                    padding: '12px 14px',
                  }}
                >
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#2563eb', marginBottom: '8px' }}>
                    {grp.title}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
                    {grp.fields.map((f) => {
                      const val = feats[f.name] !== undefined ? feats[f.name] : selectedTicket[f.name]
                      const valStr = String(val ?? '—')

                      // Tone highlight
                      let valBg = '#f1f5f9'
                      let valColor = '#334155'
                      if (valStr === 'Yes' || valStr === 'High') {
                        valBg = '#dcfce7'
                        valColor = '#166534'
                      } else if (valStr === 'No' || valStr === 'Low') {
                        valBg = '#fee2e2'
                        valColor = '#991b1b'
                      }

                      return (
                        <div
                          key={f.name}
                          style={{
                            background: '#f8fafc',
                            padding: '8px 12px',
                            borderRadius: '6px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            gap: '8px',
                          }}
                        >
                          <span style={{ fontSize: '12px', color: '#334155', fontWeight: 600 }}>{f.label}</span>
                          <span
                            style={{
                              fontSize: '11.5px',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: '4px',
                              background: valBg,
                              color: valColor,
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {valStr}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ================================================================= */}
          {/* RIGHT COLUMN – AI PREDICTION & REVIEWER DECISION */}
          {/* ================================================================= */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* AI Prediction Box */}
            <div
              className="panel"
              style={{
                padding: '24px',
                borderRadius: '12px',
                background: 'var(--ax-surface, #ffffff)',
                border: '1px solid var(--ax-border, #e2e8f0)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <p className="eyebrow" style={{ color: '#7c3aed', fontWeight: 700, fontSize: '11px', letterSpacing: '0.06em', margin: 0 }}>
                  AI MODEL PREDICTION RESULTS (V3)
                </p>
                <span style={{ fontSize: '11px', color: 'var(--ax-text-faint, #64748b)' }}>Automated Inference</span>
              </div>

              {/* Prediction badge */}
              <div
                style={{
                  padding: '18px',
                  borderRadius: '10px',
                  background: predStyle.bg,
                  border: `1px solid ${predStyle.border}`,
                  textAlign: 'center',
                  marginBottom: '14px',
                }}
              >
                <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: predStyle.text, opacity: 0.8, fontWeight: 700 }}>
                  14-Feature Model Inference
                </span>
                <div style={{ fontSize: '26px', fontWeight: 800, color: predStyle.text, margin: '6px 0 2px' }}>
                  {selectedTicket.ai_prediction || 'NO_PREDICTION'}
                </div>
                {confidence != null && (
                  <div style={{ fontSize: '14px', fontWeight: 700, color: predStyle.text }}>
                    Confidence: {(confidence * 100).toFixed(1)}%
                  </div>
                )}
              </div>

              {/* Confidence Alert */}
              {confidence != null && (
                <div
                  style={{
                    padding: '10px 14px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: 600,
                    marginBottom: '12px',
                    background: isLowConfidence ? '#fef9c3' : '#dcfce7',
                    border: `1px solid ${isLowConfidence ? '#fde047' : '#86efac'}`,
                    color: isLowConfidence ? '#a16207' : '#15803d',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                >
                  <span>{isLowConfidence ? '⚠️' : '✓'}</span>
                  <span>
                    {isLowConfidence
                      ? 'Low Confidence (<70%) or Review Required · Manual inspection recommended'
                      : 'High Model Confidence (≥70%)'}
                  </span>
                </div>
              )}

              {selectedTicket.ai_error_message && (
                <div style={{ padding: '8px 12px', borderRadius: '6px', background: '#fee2e2', color: '#b91c1c', fontSize: '11.5px', marginBottom: '12px' }}>
                  <strong>AI Engine Notice:</strong> {selectedTicket.ai_error_message}
                </div>
              )}

              <p style={{ margin: 0, fontSize: '11.5px', color: 'var(--ax-text-faint, #64748b)', fontStyle: 'italic', lineHeight: 1.4 }}>
                * Advisory note: AI prediction supports the reviewer and does not replace human authorization.
              </p>
            </div>

            {/* Reviewer Action / Ground Truth Card */}
            <div
              className="panel"
              style={{
                padding: '24px',
                borderRadius: '12px',
                background: 'var(--ax-surface, #ffffff)',
                border: '1px solid var(--ax-border, #e2e8f0)',
              }}
            >
              <p className="eyebrow" style={{ color: '#0284c7', fontWeight: 700, fontSize: '11px', letterSpacing: '0.06em', margin: '0 0 10px' }}>
                REVIEWER DECISION (GROUND TRUTH)
              </p>

              {isReviewed ? (
                // Already reviewed state: Display Ground Truth
                <div>
                  <div
                    style={{
                      padding: '14px 16px',
                      borderRadius: '8px',
                      background: selectedTicket.ground_truth === 'Valid Claim' || selectedTicket.ground_truth === 'WARRANTY' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      border: `1px solid ${selectedTicket.ground_truth === 'Valid Claim' || selectedTicket.ground_truth === 'WARRANTY' ? '#22c55e' : '#ef4444'}`,
                      marginBottom: '14px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '12px', color: 'var(--ax-text-soft, #475569)' }}>Decision:</span>
                      <strong
                        style={{
                          fontSize: '15px',
                          color: selectedTicket.reviewer_decision === 'APPROVE' ? '#16a34a' : '#dc2626',
                        }}
                      >
                        {selectedTicket.reviewer_decision}
                      </strong>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', borderTop: '1px dashed var(--ax-border, #cbd5e1)', paddingTop: '6px' }}>
                      <span style={{ fontSize: '12px', fontWeight: 600 }}>Final Ground Truth:</span>
                      <strong style={{ fontSize: '15px', color: selectedTicket.reviewer_decision === 'APPROVE' ? '#16a34a' : '#dc2626' }}>
                        {selectedTicket.ground_truth}
                      </strong>
                    </div>
                  </div>

                  {selectedTicket.reviewer_note && (
                    <div style={{ marginBottom: '12px' }}>
                      <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--ax-text-faint, #64748b)', fontWeight: 600 }}>
                        Reviewer Audit Notes:
                      </span>
                      <div style={{ fontSize: '12.5px', marginTop: '4px', fontStyle: 'italic', color: 'var(--ax-text-soft, #334155)' }}>
                        "{selectedTicket.reviewer_note}"
                      </div>
                    </div>
                  )}

                  <div style={{ fontSize: '11px', color: 'var(--ax-text-faint, #64748b)' }}>
                    Reviewed at: {selectedTicket.reviewed_at ? new Date(selectedTicket.reviewed_at).toLocaleString() : '—'}
                  </div>
                </div>
              ) : (
                // Pending decision state: APPROVE / REJECT controls
                <div>
                  <p style={{ margin: '0 0 14px', fontSize: '13px', color: 'var(--ax-text-soft, #475569)', lineHeight: 1.5 }}>
                    Review technical features and AI recommendations to finalize claim approval or rejection:
                  </p>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '14px' }}>
                    <button
                      type="button"
                      className="button"
                      style={{
                        background: '#16a34a',
                        color: '#ffffff',
                        border: 'none',
                        padding: '12px',
                        fontSize: '14px',
                        fontWeight: 700,
                        borderRadius: '8px',
                        cursor: 'pointer',
                      }}
                      onClick={() => setDecisionModal('APPROVE')}
                    >
                      ✓ APPROVE (VALID CLAIM)
                    </button>

                    <button
                      type="button"
                      className="button"
                      style={{
                        background: '#dc2626',
                        color: '#ffffff',
                        border: 'none',
                        padding: '12px',
                        fontSize: '14px',
                        fontWeight: 700,
                        borderRadius: '8px',
                        cursor: 'pointer',
                      }}
                      onClick={() => setDecisionModal('REJECT')}
                    >
                      ✕ REJECT (INVALID CLAIM)
                    </button>
                  </div>

                  <p style={{ margin: 0, fontSize: '11.5px', color: 'var(--ax-text-faint, #64748b)', textAlign: 'center' }}>
                    This decision establishes the official <strong>Ground Truth</strong> stored in the Retraining Dataset.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* DECISION CONFIRMATION MODAL */}
        {decisionModal && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 9999,
              padding: '20px',
            }}
          >
            <div
              style={{
                background: 'var(--ax-surface, #ffffff)',
                borderRadius: '12px',
                padding: '28px',
                maxWidth: '520px',
                width: '100%',
                boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
              }}
            >
              <h3 style={{ margin: '0 0 10px', fontSize: '18px', fontWeight: 800 }}>
                Confirm Claim {decisionModal === 'APPROVE' ? 'APPROVAL' : 'REJECTION'}
              </h3>
              <p style={{ margin: '0 0 16px', fontSize: '13.5px', color: 'var(--ax-text-soft, #475569)', lineHeight: 1.5 }}>
                You are about to record a <strong>{decisionModal}</strong> decision for ticket <span className="mono">{selectedTicket.ticket_id}</span>.
                This decision will establish the <strong>Ground Truth</strong> as{' '}
                <span style={{ color: decisionModal === 'APPROVE' ? '#16a34a' : '#dc2626', fontWeight: 700 }}>
                  {decisionModal === 'APPROVE' ? 'Valid Claim' : 'Invalid Claim'}
                </span>.
              </p>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, marginBottom: '6px' }}>
                  Reviewer Justification / Audit Notes (Optional)
                </label>
                <textarea
                  rows="3"
                  placeholder="e.g., Verified hardware diagnostics, confirmed serial matches original invoice, covered under warranty policy..."
                  value={reviewerNote}
                  onChange={(e) => setReviewerNote(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--ax-border, #cbd5e1)',
                    fontSize: '13px',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setDecisionModal(null)}
                  disabled={submittingDecision}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="button"
                  style={{
                    background: decisionModal === 'APPROVE' ? '#16a34a' : '#dc2626',
                    color: '#ffffff',
                    border: 'none',
                    padding: '8px 18px',
                    fontWeight: 700,
                    borderRadius: '6px',
                    cursor: 'pointer',
                  }}
                  onClick={handleConfirmDecision}
                  disabled={submittingDecision}
                >
                  {submittingDecision ? 'Saving...' : `Confirm ${decisionModal}`}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  // ----------------------------------------------------------------------------
  // VIEW A: REVIEWER QUEUE TABLE
  // ----------------------------------------------------------------------------
  return (
    <div className="reviewer-queue-container" style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px' }}>
      {/* Page Title */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <p className="eyebrow" style={{ color: '#2563eb', fontWeight: 700, fontSize: '12px', letterSpacing: '0.05em' }}>
            ASSUREX CLAIM OPERATIONS · HUMAN-IN-THE-LOOP
          </p>
          <h1 style={{ margin: '4px 0 0', fontSize: '26px', fontWeight: 800 }}>Warranty Reviewer Desk</h1>
        </div>

        <button className="button secondary" onClick={loadTickets} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          ↻ Refresh Queue
        </button>
      </div>

      {/* KPI Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '20px' }}>
        <div style={{ background: 'var(--ax-surface, #ffffff)', padding: '16px 18px', borderRadius: '10px', border: '1px solid var(--ax-border, #e2e8f0)' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--ax-text-faint, #64748b)', fontWeight: 600 }}>Awaiting Review</span>
          <div style={{ fontSize: '26px', fontWeight: 800, color: '#ea580c', margin: '4px 0 0' }}>{kpis.queueCount}</div>
        </div>

        <div style={{ background: 'var(--ax-surface, #ffffff)', padding: '16px 18px', borderRadius: '10px', border: '1px solid var(--ax-border, #e2e8f0)' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--ax-text-faint, #64748b)', fontWeight: 600 }}>Low Confidence ({"<"}70%)</span>
          <div style={{ fontSize: '26px', fontWeight: 800, color: '#ca8a04', margin: '4px 0 0' }}>{kpis.lowConfCount}</div>
        </div>

        <div style={{ background: 'var(--ax-surface, #ffffff)', padding: '16px 18px', borderRadius: '10px', border: '1px solid var(--ax-border, #e2e8f0)' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--ax-text-faint, #64748b)', fontWeight: 600 }}>AI Exceptions / Errors</span>
          <div style={{ fontSize: '26px', fontWeight: 800, color: '#dc2626', margin: '4px 0 0' }}>{kpis.errorCount}</div>
        </div>

        <div style={{ background: 'var(--ax-surface, #ffffff)', padding: '16px 18px', borderRadius: '10px', border: '1px solid var(--ax-border, #e2e8f0)' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--ax-text-faint, #64748b)', fontWeight: 600 }}>Reviewed (Ground Truth)</span>
          <div style={{ fontSize: '26px', fontWeight: 800, color: '#16a34a', margin: '4px 0 0' }}>{kpis.reviewedCount}</div>
        </div>
      </div>

      {/* Filter and Search Toolbar */}
      <div className="panel" style={{ padding: '16px 20px', borderRadius: '10px', marginBottom: '18px', background: 'var(--ax-surface, #ffffff)', border: '1px solid var(--ax-border, #e2e8f0)' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          {/* Search box */}
          <div style={{ flex: '1 1 240px' }}>
            <input
              type="text"
              placeholder="Search Ticket ID, Model, Serial, description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid var(--ax-border, #cbd5e1)',
                background: 'var(--ax-input-bg, #fff)',
                fontSize: '13px'
              }}
            />
          </div>

          {/* Status filter */}
          <div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid var(--ax-border, #cbd5e1)',
                background: 'var(--ax-input-bg, #fff)',
                fontSize: '13px'
              }}
            >
              <option value="ALL_QUEUE">Active Queue (Waiting Review)</option>
              <option value="WAITING_REVIEW">WAITING_REVIEW</option>
              <option value="REVIEW_REQUIRED">REVIEW_REQUIRED</option>
              <option value="AI_ERROR">AI_ERROR</option>
              <option value="REVIEWED">REVIEWED (Completed)</option>
              <option value="ALL">All Records</option>
            </select>
          </div>

          {/* AI Prediction filter */}
          <div>
            <select
              value={predFilter}
              onChange={(e) => setPredFilter(e.target.value)}
              style={{
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid var(--ax-border, #cbd5e1)',
                background: 'var(--ax-input-bg, #fff)',
                fontSize: '13px'
              }}
            >
              <option value="ALL">All AI Predictions</option>
              <option value="WARRANTY">AI: WARRANTY</option>
              <option value="NOT_WARRANTY">AI: NOT_WARRANTY</option>
              <option value="REVIEW_REQUIRED">AI: REVIEW_REQUIRED</option>
            </select>
          </div>

          {/* Product Type filter */}
          <div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              style={{
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid var(--ax-border, #cbd5e1)',
                background: 'var(--ax-input-bg, #fff)',
                fontSize: '13px'
              }}
            >
              <option value="ALL">All Product Categories</option>
              {ALLOWED_PRODUCT_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="panel" style={{ borderRadius: '10px', overflow: 'hidden', background: 'var(--ax-surface, #ffffff)', border: '1px solid var(--ax-border, #e2e8f0)' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--ax-text-faint, #64748b)' }}>
            Loading reviewer queue...
          </div>
        ) : error ? (
          <div style={{ padding: '24px', color: '#dc2626', textAlign: 'center' }}>
            {error}
          </div>
        ) : filteredTickets.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--ax-text-faint, #64748b)' }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>📋</div>
            <h3 style={{ margin: '0 0 4px', fontSize: '16px' }}>No claims match current filters</h3>
            <p style={{ margin: 0, fontSize: '13px' }}>Try adjusting search keyword or status filter.</p>
          </div>
        ) : (
          <div className="table-wrapper" style={{ overflowX: 'auto' }}>
            <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--ax-surface-alt, #f8fafc)', borderBottom: '1px solid var(--ax-border, #e2e8f0)' }}>
                  <th style={{ padding: '12px 16px' }}>Ticket ID</th>
                  <th style={{ padding: '12px 16px' }}>Device</th>
                  <th style={{ padding: '12px 16px' }}>Issue</th>
                  <th style={{ padding: '12px 16px' }}>AI Prediction</th>
                  <th style={{ padding: '12px 16px' }}>Confidence</th>
                  <th style={{ padding: '12px 16px' }}>Created Date</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                  <th style={{ padding: '12px 16px', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredTickets.map((t) => {
                  const predColor = getPredColor(t.ai_prediction)
                  const isLow = t.ai_confidence != null && t.ai_confidence < 0.70
                  return (
                    <tr
                      key={t.ticket_id}
                      style={{ borderBottom: '1px solid var(--ax-border, #e2e8f0)', cursor: 'pointer' }}
                      onClick={() => setSelectedTicket(t)}
                    >
                      <td style={{ padding: '12px 16px' }}>
                        <strong className="mono" style={{ color: '#2563eb' }}>{t.ticket_id}</strong>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 600 }}>{t.product_type}</div>
                        <small style={{ color: 'var(--ax-text-faint, #64748b)' }}>{t.product_model}</small>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          fontSize: '11.5px',
                          background: 'rgba(0,0,0,0.04)',
                          padding: '2px 8px',
                          borderRadius: '12px',
                          border: '1px solid var(--ax-border, #e2e8f0)'
                        }}>
                          {t.problem_category}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          fontWeight: 700,
                          fontSize: '11px',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          background: predColor.bg,
                          color: predColor.text,
                          border: `1px solid ${predColor.border}`
                        }}>
                          {t.ai_prediction || 'PENDING'}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        {t.ai_confidence != null ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontWeight: 600, color: isLow ? '#ca8a04' : 'inherit' }}>
                              {(t.ai_confidence * 100).toFixed(0)}%
                            </span>
                            {isLow && <span title="Low confidence, manual review recommended" style={{ fontSize: '11px' }}>⚠️</span>}
                          </div>
                        ) : (
                          <span style={{ color: 'var(--ax-text-faint, #64748b)' }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--ax-text-faint, #64748b)', whiteSpace: 'nowrap' }}>
                        {t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          fontSize: '11px',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: '12px',
                          background: t.status === 'REVIEWED' ? '#dcfce7' : t.status === 'AI_ERROR' ? '#fee2e2' : '#fff7ed',
                          color: t.status === 'REVIEWED' ? '#15803d' : t.status === 'AI_ERROR' ? '#b91c1c' : '#ea580c'
                        }}>
                          {t.status}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                        <button
                          className="button secondary"
                          style={{ padding: '4px 10px', fontSize: '12px' }}
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedTicket(t)
                          }}
                        >
                          Review →
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}


// ==============================================================================
// 3. RETRAINING DATASET VIEWER & EXPORTER (14 FEATURES + GROUND TRUTH)
// ==============================================================================

export function WarrantyRetrainingDataset() {
  const [dataset, setDataset] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadDataset()
  }, [])

  async function loadDataset() {
    setLoading(true)
    setError('')
    try {
      const data = await api('/api/retraining/dataset')
      const list = Array.isArray(data) ? data : data?.records || data?.data || []
      setDataset(list)
    } catch (err) {
      setError(err.message || 'Unable to load retraining dataset.')
    } finally {
      setLoading(false)
    }
  }

  function downloadJson() {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(dataset, null, 2))
    const link = document.createElement('a')
    link.setAttribute('href', dataStr)
    link.setAttribute('download', `assurex_retraining_dataset_14features_${new Date().toISOString().split('T')[0]}.json`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  }

  function downloadCsv() {
    if (!dataset.length) return
    const headers = [
      'ticket_id',
      ...MODEL_14_FEATURES,
      'ai_prediction',
      'ai_confidence',
      'ground_truth',
      'reviewer_decision',
      'reviewer_note',
      'reviewed_at',
    ]

    const csvRows = [headers.join(',')]
    for (const row of dataset) {
      const feats = row.model_features || {}
      const values = headers.map((header) => {
        const val = row[header] !== undefined ? row[header] : feats[header] ?? ''
        return `"${String(val).replace(/"/g, '""')}"`
      })
      csvRows.push(values.join(','))
    }

    const csvStr = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvRows.join('\n'))
    const link = document.createElement('a')
    link.setAttribute('href', csvStr)
    link.setAttribute('download', `assurex_retraining_dataset_14features_${new Date().toISOString().split('T')[0]}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  }

  return (
    <div className="retraining-dataset-container" style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <p className="eyebrow" style={{ color: '#0284c7', fontWeight: 700, fontSize: '12px', letterSpacing: '0.05em' }}>
            ML PIPELINE · CONTINUOUS LEARNING & RETRAINING
          </p>
          <h1 style={{ margin: '4px 0 0', fontSize: '24px', fontWeight: 800 }}>
            Retraining Dataset (14 Features + Ground Truth)
          </h1>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="button secondary" onClick={downloadCsv} disabled={dataset.length === 0}>
            Download CSV (14 Features) ↓
          </button>
          <button className="button primary" onClick={downloadJson} disabled={dataset.length === 0}>
            Download JSON ↓
          </button>
        </div>
      </div>

      {/* Dataset Summary card */}
      <div
        className="panel"
        style={{
          padding: '18px 24px',
          borderRadius: '10px',
          marginBottom: '20px',
          background: 'var(--ax-surface, #ffffff)',
          border: '1px solid var(--ax-border, #e2e8f0)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '14px',
        }}
      >
        <div>
          <span style={{ fontSize: '12px', color: 'var(--ax-text-faint, #64748b)' }}>Verified Ground Truth Records:</span>
          <div style={{ fontSize: '28px', fontWeight: 800, color: '#2563eb' }}>{dataset.length} records</div>
        </div>
      </div>

      {/* Dataset Table */}
      <div className="panel" style={{ borderRadius: '10px', overflow: 'hidden', background: 'var(--ax-surface, #ffffff)', border: '1px solid var(--ax-border, #e2e8f0)' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--ax-text-faint, #64748b)' }}>
            Loading retraining dataset...
          </div>
        ) : error ? (
          <div style={{ padding: '24px', color: '#dc2626', textAlign: 'center' }}>{error}</div>
        ) : dataset.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--ax-text-faint, #64748b)' }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>📁</div>
            <h3 style={{ margin: '0 0 4px', fontSize: '16px' }}>No verified records yet</h3>
            <p style={{ margin: 0, fontSize: '13px' }}>
              When a Reviewer approves or rejects a claim in the Reviewer Desk, records will automatically appear here.
            </p>
          </div>
        ) : (
          <div className="table-wrapper" style={{ overflowX: 'auto' }}>
            <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12.5px' }}>
              <thead>
                <tr style={{ background: 'var(--ax-surface-alt, #f8fafc)', borderBottom: '1px solid var(--ax-border, #e2e8f0)' }}>
                  <th style={{ padding: '10px 14px' }}>Ticket ID</th>
                  <th style={{ padding: '10px 14px' }}>Device</th>
                  <th style={{ padding: '10px 14px' }}>Fault Covered</th>
                  <th style={{ padding: '10px 14px' }}>Warranty Days</th>
                  <th style={{ padding: '10px 14px' }}>AI Prediction</th>
                  <th style={{ padding: '10px 14px' }}>Ground Truth</th>
                  <th style={{ padding: '10px 14px' }}>Reviewer Notes</th>
                  <th style={{ padding: '10px 14px' }}>Reviewed Date</th>
                </tr>
              </thead>
              <tbody>
                {dataset.map((row) => {
                  const feats = row.model_features || {}
                  const isMatch = (feats.FaultCovered ?? row.FaultCovered) === 'Yes'
                  const gt = row.ground_truth
                  const isApproved = gt === 'Valid Claim' || gt === 'WARRANTY'

                  return (
                    <tr key={row.ticket_id} style={{ borderBottom: '1px solid var(--ax-border, #e2e8f0)' }}>
                      <td style={{ padding: '10px 14px' }}>
                        <strong className="mono" style={{ color: '#2563eb' }}>{row.ticket_id}</strong>
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <div>{row.product_type}</div>
                        <small style={{ color: 'var(--ax-text-faint, #64748b)' }}>{row.product_model}</small>
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: isMatch ? '#dcfce7' : '#fee2e2',
                            color: isMatch ? '#15803d' : '#b91c1c',
                          }}
                        >
                          {feats.FaultCovered ?? row.FaultCovered ?? '—'}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        {feats.WarrantyRemainingDays ?? row.WarrantyRemainingDays ?? '—'}d
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span
                          style={{
                            fontSize: '11px',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: '#f1f5f9',
                            fontWeight: 600,
                          }}
                        >
                          {row.ai_prediction || '—'}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <strong
                          style={{
                            fontSize: '12px',
                            color: isApproved ? '#15803d' : '#b91c1c',
                          }}
                        >
                          {gt}
                        </strong>
                      </td>
                      <td style={{ padding: '10px 14px', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={row.reviewer_note || ''}>
                        {row.reviewer_note || '—'}
                      </td>
                      <td style={{ padding: '10px 14px', color: 'var(--ax-text-faint, #64748b)' }}>
                        {row.reviewed_at ? new Date(row.reviewed_at).toLocaleDateString() : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
