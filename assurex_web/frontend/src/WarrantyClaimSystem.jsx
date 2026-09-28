import React, { useState, useEffect, useMemo } from 'react'
import { api } from './api'
import {
  MODEL_14_FEATURES,
  getFaultCategoriesForProduct,
  FAULT_CATEGORIES_BY_PRODUCT_CATEGORY,
} from './claimFields'

// Shared mock storage to persist tickets across views within the session
const LOCAL_STORAGE_TICKETS_KEY = 'assurex_v3_tickets'

function loadStoredTickets() {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_TICKETS_KEY)
    if (raw) return JSON.parse(raw)
  } catch {
    // fallback
  }

  // Initial seed tickets
  return [
    {
      ticket_id: 'TCK-8819201',
      customer_name: 'Bui Ngoc Mai',
      customer_email: 'ngoc.mai07@example.com',
      customer_phone: '0912345678',
      product_code: 'AX26-00001',
      product_name: 'NovaBook 14 Ultra',
      product_model: 'NB14-2026',
      serial_number: 'NB142026-00001',
      purchase_date: '2026-07-17',
      warranty_expiry: '2028-07-16',
      incident_date: '2026-09-24',
      problem_category: 'Display Failure',
      fault_description: 'Screen displays horizontal flickering lines continuously upon boot. No physical impact.',
      previous_repair: 'No',
      repair_centre: '',
      repair_date: '',
      evidence: {
        purchase_invoice: { filename: 'Invoice_NovaStore_9021.pdf', size: '245 KB' },
        serial_image: { filename: 'Serial_Tag_NB142026.jpg', size: '1.2 MB' },
        fault_evidence: { filename: 'Screen_Flicker_Video.mp4', size: '4.8 MB' },
        repair_report: null,
      },
      model_features: {
        RepairAuthorized: 'Not Applicable',
        SerialNumberMatch: 'Yes',
        ProductModelConsistent: 'Yes',
        DuplicateClaimIndicator: 'No',
        ContradictionIndicator: 'No',
        OCRConfidence: 0.95,
        ClaimReportingDelayDays: 3,
        WarrantyRemainingDays: 658,
        ClaimReportingWithinPeriod: 'Yes',
        FaultCovered: 'Yes',
        RequiredDocumentsComplete: 'Yes',
        MissingDocumentCount: 0,
        ProductIdentityMatch: 'Yes',
        OCRQualityBand: 'High',
      },
      ai_prediction: 'WARRANTY',
      ai_confidence: 0.95,
      ai_reason: 'Standard OEM manufacturing defect verified under active warranty coverage',
      status: 'WAITING_REVIEW',
      ground_truth: null,
      reviewer_note: null,
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      ticket_id: 'TCK-8819202',
      customer_name: 'Nguyen Van An',
      customer_email: 'an.nguyen@example.com',
      customer_phone: '0987654321',
      product_code: 'AX26-00002',
      product_name: 'ThinkPad T14 Gen 4',
      product_model: '21HD0001US',
      serial_number: 'PF4X9812',
      purchase_date: '2025-11-10',
      warranty_expiry: '2027-11-09',
      incident_date: '2026-09-17',
      problem_category: 'Keyboard & Trackpad Failure',
      fault_description: 'Keyboard keys intermittently stop responding during normal typing. Device previously serviced at local shop.',
      previous_repair: 'Yes',
      repair_centre: 'FastFix Independent Tech Shop',
      repair_date: '2026-07-20',
      evidence: {
        purchase_invoice: { filename: 'TechWorld_Receipt_4491.pdf', size: '310 KB' },
        serial_image: { filename: 'ThinkPad_Serial_Photo.jpg', size: '980 KB' },
        fault_evidence: { filename: 'Keyboard_Tester_Log.png', size: '640 KB' },
        repair_report: null, // missing
      },
      model_features: {
        RepairAuthorized: 'No',
        SerialNumberMatch: 'Yes',
        ProductModelConsistent: 'Yes',
        DuplicateClaimIndicator: 'No',
        ContradictionIndicator: 'No',
        OCRConfidence: 0.95,
        ClaimReportingDelayDays: 10,
        WarrantyRemainingDays: 408,
        ClaimReportingWithinPeriod: 'Yes',
        FaultCovered: 'Yes',
        RequiredDocumentsComplete: 'No',
        MissingDocumentCount: 1,
        ProductIdentityMatch: 'Yes',
        OCRQualityBand: 'High',
      },
      ai_prediction: 'REVIEW_REQUIRED',
      ai_confidence: 0.78,
      ai_reason: 'Prior unauthorized third-party repair detected without certified repair report',
      status: 'WAITING_REVIEW',
      ground_truth: null,
      reviewer_note: null,
      created_at: new Date(Date.now() - 7200000).toISOString(),
    },
    {
      ticket_id: 'TCK-8819203',
      customer_name: 'Tran Thi Lan',
      customer_email: 'lan.tran@example.com',
      customer_phone: '0901234567',
      product_code: 'AX26-00003',
      product_name: 'Galaxy S24 Ultra',
      product_model: 'SM-S928B',
      serial_number: 'R5CW109K',
      purchase_date: '2024-03-01',
      warranty_expiry: '2025-02-28',
      incident_date: '2026-08-15',
      problem_category: 'Liquid Damage',
      fault_description: 'Phone fell into water pool, screen shattered with liquid ingress behind display glass.',
      previous_repair: 'No',
      repair_centre: '',
      repair_date: '',
      evidence: {
        purchase_invoice: { filename: 'PhoneMart_Receipt_1182.pdf', size: '180 KB' },
        serial_image: { filename: 'Serial_Backplate.jpg', size: '890 KB' },
        fault_evidence: { filename: 'Liquid_Damage_Photo.jpg', size: '1.5 MB' },
        repair_report: null,
      },
      model_features: {
        RepairAuthorized: 'Not Applicable',
        SerialNumberMatch: 'Yes',
        ProductModelConsistent: 'Yes',
        DuplicateClaimIndicator: 'No',
        ContradictionIndicator: 'No',
        OCRConfidence: 0.95,
        ClaimReportingDelayDays: 43,
        WarrantyRemainingDays: -576,
        ClaimReportingWithinPeriod: 'No',
        FaultCovered: 'No',
        RequiredDocumentsComplete: 'Yes',
        MissingDocumentCount: 0,
        ProductIdentityMatch: 'Yes',
        OCRQualityBand: 'High',
      },
      ai_prediction: 'NOT_WARRANTY',
      ai_confidence: 0.98,
      ai_reason: 'Defect excluded: physical impact, liquid ingress, or user abuse; warranty expired',
      status: 'REVIEWED',
      ground_truth: 'Invalid Claim',
      reviewer_note: 'Liquid damage verified, device is beyond warranty coverage window. Claim rejected.',
      reviewed_at: new Date(Date.now() - 1800000).toISOString(),
      created_at: new Date(Date.now() - 86400000).toISOString(),
    },
  ]
}

function friendlyErrorMessage(error, fallback = 'Unable to complete the request.') {
  if (!error) return fallback
  if (typeof error === 'string') return error
  if (error.message && error.message !== '[object Object]') return error.message
  const detail = error.data?.detail || error.detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => [Array.isArray(item?.loc) ? item.loc.join('.') : '', item?.msg].filter(Boolean).join(': '))
      .filter(Boolean)
      .join('; ') || fallback
  }
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') return JSON.stringify(detail)
  return fallback
}

// ==============================================================================
// 1. CUSTOMER - WARRANTY CLAIM FORM (CLEAN CUSTOMER INPUTS → FEATURE ENGINE)
// ==============================================================================

export function CustomerWarrantyClaimForm({ email = '', customerName = '', onCreated, onCancel }) {
  // Identity comes from the authenticated session and is never a claim source of truth.
  const customer = {
    customer_name: customerName || email,
    email,
  }

  // Section 2: Product Identification
  const [productCodeInput, setProductCodeInput] = useState('')
  const [productRecord, setProductRecord] = useState(null)
  const [lookingUp, setLookingUp] = useState(false)

  // Section 3: Claim Incident
  const [incidentDate, setIncidentDate] = useState('')
  const [problemCategory, setProblemCategory] = useState('')
  const [faultDescription, setFaultDescription] = useState('')

  const currentFaultCategories = useMemo(
    () => getFaultCategoriesForProduct(productRecord?.category),
    [productRecord?.category]
  )
  const selectedCategoryInfo = useMemo(
    () => currentFaultCategories.find((c) => c.value === problemCategory),
    [currentFaultCategories, problemCategory]
  )

  const isOtherFaultCategory = problemCategory === 'Other'

  // Section 4: Repair History
  const [previousRepair, setPreviousRepair] = useState('No')
  const [repairCentre, setRepairCentre] = useState('')
  const [repairDate, setRepairDate] = useState('')
  const [evidenceAnswers, setEvidenceAnswers] = useState({
    purchase_invoice_available: 'No',
    serial_image_available: 'No',
    fault_evidence_available: 'No',
    repair_report_available: 'No',
  })

  // Active Preset & State
  const [submitting, setSubmitting] = useState(false)
  const [errors, setErrors] = useState({})
  const [createdTicket, setCreatedTicket] = useState(null)
  const [submitError, setSubmitError] = useState('')

  // Handle Product Code Lookup
  async function handleProductLookup(code) {
    const targetCode = code !== undefined ? code : productCodeInput
    if (!targetCode.trim()) {
      setErrors((prev) => ({ ...prev, product_code: 'Enter the Registered Product Code shown in My Products (REG-xxxxx).' }))
      return
    }
    setLookingUp(true)
    try {
      const found = await api(`/api/claims/v3/product/${encodeURIComponent(targetCode.trim())}`)
      setProductRecord(found)
      setProductCodeInput(found.product_code)
      const faultCats = getFaultCategoriesForProduct(found.category)
      if (faultCats && faultCats.length > 0) {
        setProblemCategory(faultCats.find((cat) => cat.value !== 'Other')?.value || 'Other')
      }
      if (found.repair_history?.has_external_repair_on_record) {
        setPreviousRepair('Yes')
        setRepairCentre(found.repair_history.latest_external_repair_centre || '')
        setRepairDate(found.repair_history.latest_external_repair_date || '')
      } else {
        setPreviousRepair('No')
        setRepairCentre('')
        setRepairDate('')
      }
      setErrors((prev) => ({ ...prev, product_code: '', problem_category: '' }))
    } catch (error) {
      setProductRecord(null)
      setErrors((prev) => ({
        ...prev,
        product_code: friendlyErrorMessage(error, 'Registered Product Code was not found for this account.'),
      }))
    } finally {
      setLookingUp(false)
    }
  }

  // Validation
  function validate() {
    const errs = {}
    if (!productRecord) errs.product_code = 'Verify a Registered Product Code that belongs to your account.'
    if (!incidentDate) errs.incident_date = 'Please select the date the incident/defect occurred.'
    if (!problemCategory) errs.problem_category = 'Please select a fault category for your product.'
    if (problemCategory === 'Other' && (!faultDescription?.trim() || faultDescription.trim().length < 10))
      errs.fault_description = 'Please describe the fault or symptom when category is Other (minimum 10 characters).'

    if (previousRepair === 'Yes') {
      if (!repairCentre?.trim()) errs.repair_centre = 'Please state the repair centre name.'
    }
    setErrors(errs)
    if (Object.keys(errs).length > 0) {
      setSubmitError(Object.values(errs)[0])
    }
    return Object.keys(errs).length === 0
  }

  // Submit Claim
  async function handleSubmit(e) {
    e.preventDefault()
    if (submitting) return
    setSubmitError('')

    if (!validate()) {
      window.scrollTo({ top: 0, behavior: 'smooth' })
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        product_code: productRecord.product_code,
        incident_date: incidentDate,
        problem_category: problemCategory,
        fault_description: isOtherFaultCategory ? faultDescription.trim() : '',
        previous_repair: previousRepair,
        repair_centre: repairCentre?.trim() || '',
        repair_date: repairDate || null,
        ...evidenceAnswers,
      }
      const response = await api('/api/claims/v3/ticket', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      const created = response.ticket

      setErrors({})
      setCreatedTicket(created)
      window.requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: 'smooth' }))
      if (onCreated) onCreated(created)
    } catch (err) {
      setSubmitError(friendlyErrorMessage(err, 'Unable to submit claim.'))
    } finally {
      setSubmitting(false)
    }
  }

  function resetForm() {
    setCreatedTicket(null)
    setProductCodeInput('')
    setProductRecord(null)
    setIncidentDate('')
    setProblemCategory('')
    setFaultDescription('')
    setPreviousRepair('No')
    setRepairCentre('')
    setRepairDate('')
    setEvidenceAnswers({
      purchase_invoice_available: 'No',
      serial_image_available: 'No',
      fault_evidence_available: 'No',
      repair_report_available: 'No',
    })
    setErrors({})
  }

  // ============================================================================
  // SUCCESS SCREEN
  // ============================================================================
  if (createdTicket) {
    const isWarranty = createdTicket.ai_prediction === 'WARRANTY'
    const isNotWarranty = createdTicket.ai_prediction === 'NOT_WARRANTY'

    return (
      <div
        className="ticket-success-card"
        style={{
          background: 'var(--ax-surface, #ffffff)',
          border: '1px solid var(--ax-border, #e2e8f0)',
          borderRadius: '16px',
          padding: '36px',
          maxWidth: '780px',
          margin: '24px auto',
          boxShadow: '0 10px 30px rgba(0,0,0,0.06)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: isWarranty
                ? 'rgba(34, 197, 94, 0.15)'
                : isNotWarranty
                  ? 'rgba(239, 68, 68, 0.15)'
                  : 'rgba(234, 179, 8, 0.15)',
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
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 800, color: '#0f172a' }}>
            {isWarranty
              ? 'Warranty Ticket Created · AI Eligible'
              : isNotWarranty
                ? 'Warranty Ticket Created · AI Ineligible'
                : 'Warranty Ticket Created · Queued for Reviewer'}
          </h2>
          <p style={{ margin: '8px 0 0', color: 'var(--ax-text-soft, #64748b)', fontSize: '13.5px' }}>
            Ticket ID: <strong className="mono" style={{ color: '#2563eb' }}>{createdTicket.ticket_id}</strong> ·
            The claim is queued for official Reviewer Ground Truth sign-off.
          </p>
        </div>

        {/* AI Prediction Box */}
        <div
          style={{
            background: 'var(--ax-surface-alt, #f8fafc)',
            borderRadius: '12px',
            padding: '20px',
            border: '1px solid var(--ax-border, #e2e8f0)',
            marginBottom: '24px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              AI Model V3 Assessment
            </span>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '4px',
                background: isWarranty ? '#dcfce7' : isNotWarranty ? '#fee2e2' : '#fef9c3',
                color: isWarranty ? '#15803d' : isNotWarranty ? '#b91c1c' : '#a16207',
              }}
            >
              Confidence: {Math.round((createdTicket.ai_confidence || 0.95) * 100)}%
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', fontSize: '13px' }}>
            <div>
              <span style={{ color: 'var(--ax-text-faint, #64748b)', display: 'block', fontSize: '11.5px' }}>Device & Model:</span>
              <strong>{createdTicket.product_name} ({createdTicket.product_model})</strong>
            </div>
            <div>
              <span style={{ color: 'var(--ax-text-faint, #64748b)', display: 'block', fontSize: '11.5px' }}>Customer:</span>
              <strong>{createdTicket.customer_name} ({createdTicket.customer_email})</strong>
            </div>
            <div>
              <span style={{ color: 'var(--ax-text-faint, #64748b)', display: 'block', fontSize: '11.5px' }}>Fault Category:</span>
              <strong>{createdTicket.problem_category || problemCategory || 'Hardware Defect'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--ax-text-faint, #64748b)', display: 'block', fontSize: '11.5px' }}>AI Prediction:</span>
              <strong style={{ color: isWarranty ? '#15803d' : isNotWarranty ? '#b91c1c' : '#ca8a04' }}>
                {createdTicket.ai_prediction}
              </strong>
            </div>
            <div>
              <span style={{ color: 'var(--ax-text-faint, #64748b)', display: 'block', fontSize: '11.5px' }}>Queue Status:</span>
              <span className="days-left-badge active">{createdTicket.status || 'WAITING_REVIEW'}</span>
            </div>
          </div>

          <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid #e2e8f0', fontSize: '12.5px', color: 'var(--ax-text-soft, #475569)' }}>
            <strong>Analysis: </strong>{createdTicket.ai_reason || `${createdTicket.model_name || 'Model V3'} assessment` }
          </div>
        </div>

        {/* Active V3 Features Summary */}
        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ margin: '0 0 10px', fontSize: '13px', fontWeight: 700, color: 'var(--ax-text, #1e293b)' }}>
            14 Automated Features Used by Model V3:
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '8px', fontSize: '12px' }}>
            {MODEL_14_FEATURES.map((feat) => {
              const val = createdTicket.model_features?.[feat]
              return (
                <div key={feat} style={{ background: '#f8fafc', padding: '6px 10px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <span style={{ fontSize: '11px', color: '#64748b', display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {feat}
                  </span>
                  <strong style={{ color: '#0f172a' }}>{String(val ?? '—')}</strong>
                </div>
              )
            })}
          </div>
        </div>

        {createdTicket.diagnostic_features && Object.keys(createdTicket.diagnostic_features).length > 0 && (
          <div style={{ marginBottom: '24px' }}>
            <h4 style={{ margin: '0 0 10px', fontSize: '13px', fontWeight: 700, color: '#334155' }}>
              Backend verification signals:
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '8px', fontSize: '12px' }}>
              {Object.entries(createdTicket.diagnostic_features).map(([feat, val]) => (
                <div key={feat} style={{ background: '#fff7ed', padding: '6px 10px', borderRadius: '6px', border: '1px solid #fed7aa' }}>
                  <span style={{ fontSize: '11px', color: '#9a3412', display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {feat}
                  </span>
                  <strong style={{ color: '#7c2d12' }}>{String(val ?? '—')}</strong>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <button type="button" className="button primary" onClick={resetForm}>
            Submit Another Claim
          </button>
          {onCancel && (
            <button type="button" className="button secondary" onClick={onCancel}>
              Return to Home
            </button>
          )}
        </div>
      </div>
    )
  }

  // ============================================================================
  // MAIN CLAIM FORM VIEW
  // ============================================================================
  return (
    <div className="claim-system-container" style={{ maxWidth: '880px', margin: '0 auto', padding: '16px' }}>
      <header className="page-header" style={{ marginBottom: '20px' }}>
        <div>
          <p className="eyebrow">Customer Portal</p>
          <h1>Warranty Claim Request</h1>
        </div>
      </header>

      {submitError && (
        <div className="alert error" style={{ marginBottom: '20px' }}>
          {submitError}
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        {/* GROUP 1: CUSTOMER INFORMATION */}
        <section
          className="panel"
          style={{
            marginBottom: '20px',
            padding: '22px',
            borderRadius: '12px',
            background: 'var(--ax-surface, #ffffff)',
            border: '1px solid var(--ax-border, #e2e8f0)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <span style={{ background: '#eff6ff', color: '#2563eb', width: '26px', height: '26px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 800 }}>
              1
            </span>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>
              Customer Information
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>
                Full Name <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <input
                type="text"
                value={customer.customer_name}
                readOnly
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  background: '#f8fafc',
                  fontSize: '13px',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>
                Email Address <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <input
                type="email"
                value={customer.email}
                readOnly
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  background: '#f8fafc',
                  fontSize: '13px',
                }}
              />
            </div>
          </div>
        </section>

        {/* GROUP 2: PRODUCT IDENTIFICATION & DATABASE LOOKUP */}
        <section
          className="panel"
          style={{
            marginBottom: '20px',
            padding: '22px',
            borderRadius: '12px',
            background: 'var(--ax-surface, #ffffff)',
            border: '1px solid var(--ax-border, #e2e8f0)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <span style={{ background: '#eff6ff', color: '#2563eb', width: '26px', height: '26px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 800 }}>
              2
            </span>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>
              Product Identification & Verification
            </h3>
          </div>

          {/* Registered Product Code Lookup Bar */}
          <div style={{ marginBottom: '16px', background: '#f8fafc', padding: '14px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '12.5px', fontWeight: 700, color: '#334155' }}>
              Registered Product Code:
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                placeholder="Enter registration code from My Products (e.g. REG-00001)"
                value={productCodeInput}
                onChange={(e) => {
                  setProductCodeInput(e.target.value.toUpperCase())
                  setProductRecord(null)
                }}
                style={{
                  flex: 1,
                  padding: '9px 12px',
                  borderRadius: '6px',
                  border: `1px solid ${errors.product_code ? '#ef4444' : '#cbd5e1'}`,
                  fontSize: '13px',
                  fontWeight: 600,
                }}
              />
              <button
                type="button"
                className="button primary"
                disabled={lookingUp}
                onClick={() => handleProductLookup(productCodeInput)}
                style={{ padding: '8px 16px', fontSize: '13px' }}
              >
                {lookingUp ? 'Checking…' : '⌕ Verify Registration'}
              </button>
            </div>
            {errors.product_code && <p style={{ color: '#ef4444', fontSize: '11.5px', margin: '6px 0 0' }}>{errors.product_code}</p>}
          </div>

          {/* Autofilled Product Record (Read-Only) */}
          {productRecord ? (
            <div
              style={{
                background: '#ffffff',
                border: '1px solid #cbd5e1',
                borderRadius: '8px',
                padding: '16px',
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '14px',
                fontSize: '12.5px',
              }}
            >
              <div>
                <span style={{ color: '#64748b', display: 'block', fontSize: '11.5px' }}>Registered Product Code:</span>
                <strong className="mono" style={{ color: '#2563eb' }}>{productRecord.product_code}</strong>
              </div>
              <div>
                <span style={{ color: '#64748b', display: 'block', fontSize: '11.5px' }}>Product Name:</span>
                <strong>{productRecord.product_name}</strong>
              </div>
              <div>
                <span style={{ color: '#64748b', display: 'block', fontSize: '11.5px' }}>Model Number:</span>
                <strong className="mono">{productRecord.model_number}</strong>
              </div>
              <div>
                <span style={{ color: '#64748b', display: 'block', fontSize: '11.5px' }}>Serial Number:</span>
                <strong className="mono" style={{ color: '#2563eb' }}>{productRecord.serial_number}</strong>
              </div>
              <div>
                <span style={{ color: '#64748b', display: 'block', fontSize: '11.5px' }}>Purchase Date:</span>
                <strong>{productRecord.purchase_date}</strong>
              </div>
              <div>
                <span style={{ color: '#64748b', display: 'block', fontSize: '11.5px' }}>Warranty Expiry:</span>
                <strong style={{ color: productRecord.status === 'expired' ? '#dc2626' : '#16a34a' }}>
                  {productRecord.warranty_expiry_date}
                </strong>
                <span
                  style={{
                    display: 'inline-block',
                    marginLeft: '6px',
                    fontSize: '10.5px',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    background: productRecord.status === 'expired' ? '#fee2e2' : '#dcfce7',
                    color: productRecord.status === 'expired' ? '#b91c1c' : '#15803d',
                  }}
                >
                  {productRecord.status === 'expired' ? 'Expired' : 'Active'}
                </span>
              </div>
              <div>
                <span style={{ color: '#64748b', display: 'block', fontSize: '11.5px' }}>Provider:</span>
                <span>{productRecord.warranty_provider}</span>
              </div>
            </div>
          ) : (
            <div style={{ padding: '16px', background: '#fffbeb', borderRadius: '8px', border: '1px solid #fef3c7', fontSize: '12.5px', color: '#92400e' }}>
              Enter the Registered Product Code shown in My Products, for example REG-00003. The system will only return a product owned by the signed-in account.
            </div>
          )}
        </section>

        {/* GROUP 3: CLAIM INCIDENT INFORMATION */}
        <section
          className="panel"
          style={{
            marginBottom: '20px',
            padding: '22px',
            borderRadius: '12px',
            background: 'var(--ax-surface, #ffffff)',
            border: '1px solid var(--ax-border, #e2e8f0)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <span style={{ background: '#eff6ff', color: '#2563eb', width: '26px', height: '26px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 800 }}>
              3
            </span>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>
              Claim Incident Details
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(180px, 240px) 1fr', gap: '16px', marginBottom: '16px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>
                Incident Date <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <input
                type="date"
                value={incidentDate}
                onChange={(e) => {
                  setIncidentDate(e.target.value)
                  setErrors({ ...errors, incident_date: '' })
                }}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '6px',
                  border: `1px solid ${errors.incident_date ? '#ef4444' : '#cbd5e1'}`,
                  fontSize: '13px',
                }}
              />
              {errors.incident_date && <p style={{ color: '#ef4444', fontSize: '11.5px', margin: '4px 0 0' }}>{errors.incident_date}</p>}
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label style={{ margin: 0, fontSize: '13px', fontWeight: 600 }}>
                  Fault Category <span style={{ color: '#ef4444' }}>*</span>
                </label>
                {productRecord?.category && (
                  <span style={{ fontSize: '11.5px', color: '#2563eb', fontWeight: 600, background: '#eff6ff', padding: '2px 8px', borderRadius: '4px' }}>
                    Customized for {productRecord.category}
                  </span>
                )}
              </div>
              <select
                value={problemCategory}
                onChange={(e) => {
                  setProblemCategory(e.target.value)
                  setErrors({ ...errors, problem_category: '' })
                }}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '6px',
                  border: `1px solid ${errors.problem_category ? '#ef4444' : '#cbd5e1'}`,
                  fontSize: '13px',
                  background: '#ffffff',
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                <option value="">-- Select a fault category --</option>
                {currentFaultCategories.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
              {errors.problem_category && (
                <p style={{ color: '#ef4444', fontSize: '11.5px', margin: '4px 0 0' }}>{errors.problem_category}</p>
              )}
            </div>
          </div>

          {/* Fault Category Policy & Symptom Helper Box */}
          {selectedCategoryInfo && (
            <div
              style={{
                marginBottom: '16px',
                padding: '12px 14px',
                borderRadius: '8px',
                background: selectedCategoryInfo.isCovered ? '#f0fdf4' : '#fef2f2',
                border: `1px solid ${selectedCategoryInfo.isCovered ? '#bbf7d0' : '#fecaca'}`,
                display: 'flex',
                gap: '12px',
                alignItems: 'flex-start',
              }}
            >
              <div
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  background: selectedCategoryInfo.isCovered ? '#dcfce7' : '#fee2e2',
                  color: selectedCategoryInfo.isCovered ? '#15803d' : '#b91c1c',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800,
                  fontSize: '12px',
                  flexShrink: 0,
                  marginTop: '1px',
                }}
              >
                {selectedCategoryInfo.isCovered ? '✓' : '✕'}
              </div>
              <div style={{ flex: 1, fontSize: '12.5px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
                  <strong style={{ color: selectedCategoryInfo.isCovered ? '#166534' : '#991b1b', fontSize: '13px' }}>
                    {selectedCategoryInfo.isCovered ? 'Covered defect' : 'Excluded from warranty'}
                  </strong>
                  <span
                    style={{
                      fontSize: '11px',
                      padding: '1px 6px',
                      borderRadius: '4px',
                      background: selectedCategoryInfo.isCovered ? '#bbf7d0' : '#fca5a5',
                      color: selectedCategoryInfo.isCovered ? '#14532d' : '#7f1d1d',
                      fontWeight: 700,
                    }}
                  >
                    FaultCovered: {selectedCategoryInfo.isCovered ? 'Yes' : 'No'}
                  </span>
                </div>
                <p style={{ margin: '0 0 4px', color: '#334155', lineHeight: 1.4 }}>
                  <strong>Typical symptoms:</strong> {selectedCategoryInfo.description}
                </p>
                <span style={{ fontSize: '11.5px', color: selectedCategoryInfo.isCovered ? '#15803d' : '#b91c1c', fontStyle: 'italic' }}>
                  {selectedCategoryInfo.isCovered
                    ? 'AssureX warranty policy normally covers manufacturing or component defects under normal use.'
                    : 'Policy warning: accidental, physical, liquid, pest, misuse, or external power damage is normally rejected.'}
                </span>
              </div>
            </div>
          )}

          {isOtherFaultCategory ? (
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>
                Fault Description <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <textarea
                rows="3"
                placeholder="Describe the issue because you selected Other..."
                value={faultDescription}
                onChange={(e) => {
                  setFaultDescription(e.target.value)
                  setErrors({ ...errors, fault_description: '' })
                }}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: `1px solid ${errors.fault_description ? '#ef4444' : '#cbd5e1'}`,
                  fontSize: '13px',
                  fontFamily: 'inherit',
                  lineHeight: 1.5,
                }}
              />
              {errors.fault_description && <p style={{ color: '#ef4444', fontSize: '11.5px', margin: '4px 0 0' }}>{errors.fault_description}</p>}
            </div>
          ) : (
            <div style={{ padding: '12px 14px', borderRadius: '8px', background: '#f8fafc', border: '1px solid #e2e8f0', fontSize: '12.5px', color: '#475569' }}>
              No written description is required for a predefined category. Choose <strong>Other</strong> if the category list does not match your issue.
            </div>
          )}
        </section>

        {/* GROUP 4: REPAIR HISTORY */}
        <section
          className="panel"
          style={{
            marginBottom: '20px',
            padding: '22px',
            borderRadius: '12px',
            background: 'var(--ax-surface, #ffffff)',
            border: '1px solid var(--ax-border, #e2e8f0)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <span style={{ background: '#eff6ff', color: '#2563eb', width: '26px', height: '26px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 800 }}>
              4
            </span>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>
              External Repair History
            </h3>
          </div>

          {productRecord ? (
            <div
              style={{
                background: productRecord.repair_history?.has_assurex_records ? '#f8fafc' : '#f0fdf4',
                border: `1px solid ${productRecord.repair_history?.has_assurex_records ? '#cbd5e1' : '#bbf7d0'}`,
                borderRadius: '8px',
                padding: '12px 14px',
                marginBottom: '14px',
                fontSize: '12.5px',
                color: '#334155',
              }}
            >
              <strong style={{ display: 'block', marginBottom: '4px', color: '#0f172a' }}>
                AssureX service records
              </strong>
              {productRecord.repair_history?.has_assurex_records ? (
                <span>
                  Backend found {productRecord.repair_history.assurex_claim_count} prior claim/service record(s)
                  for this registered product.
                  {productRecord.repair_history.has_external_repair_on_record
                    ? ` Latest external repair on record: ${productRecord.repair_history.latest_external_repair_centre || 'Unknown centre'}${productRecord.repair_history.latest_external_repair_date ? ` on ${productRecord.repair_history.latest_external_repair_date}` : ''}.`
                    : ' No external repair declaration is recorded in AssureX history.'}
                </span>
              ) : (
                <span>No AssureX repair or claim history found for this registered product.</span>
              )}
            </div>
          ) : (
            <div
              style={{
                background: '#fffbeb',
                border: '1px solid #fde68a',
                borderRadius: '8px',
                padding: '12px 14px',
                marginBottom: '14px',
                fontSize: '12.5px',
                color: '#92400e',
              }}
            >
              Verify a registered product first so the system can check AssureX repair records.
            </div>
          )}

          <div style={{ marginBottom: '14px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>
              Has this product been repaired outside AssureX beyond the records shown above?
            </label>
            <div style={{ display: 'flex', gap: '16px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '13.5px' }}>
                <input
                  type="radio"
                  name="previous_repair"
                  value="No"
                  checked={previousRepair === 'No'}
                  onChange={() => setPreviousRepair('No')}
                />
                No — no external repair
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '13.5px' }}>
                <input
                  type="radio"
                  name="previous_repair"
                  value="Yes"
                  checked={previousRepair === 'Yes'}
                  onChange={() => setPreviousRepair('Yes')}
                />
                Yes — repaired outside AssureX
              </label>
            </div>
          </div>

          {previousRepair === 'Yes' && (
            <div
              style={{
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '16px',
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: '14px',
              }}
            >
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '12.5px', fontWeight: 600 }}>
                  Repair Centre / Facility Name <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. AssureX Official Service or Third-party shop"
                  value={repairCentre}
                  onChange={(e) => {
                    setRepairCentre(e.target.value)
                    setErrors({ ...errors, repair_centre: '' })
                  }}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: `1px solid ${errors.repair_centre ? '#ef4444' : '#cbd5e1'}`,
                    fontSize: '13px',
                  }}
                />
                {errors.repair_centre && <p style={{ color: '#ef4444', fontSize: '11.5px', margin: '4px 0 0' }}>{errors.repair_centre}</p>}
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '12.5px', fontWeight: 600 }}>
                  Previous Repair Date
                </label>
                <input
                  type="date"
                  value={repairDate}
                  onChange={(e) => setRepairDate(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '13px',
                  }}
                />
              </div>
            </div>
          )}
        </section>

        {/* GROUP 5: EVIDENCE QUESTIONS */}
        <section className="panel" style={{ marginBottom: '20px', padding: '22px', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <span style={{ background: '#eff6ff', color: '#2563eb', width: '26px', height: '26px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 800 }}>5</span>
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>Evidence Availability</h3>
              <small>Answer Yes/No. You do not need to upload photos or documents in this simplified claim flow.</small>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
            {[
              ['purchase_invoice_available', 'Do you have purchase proof, invoice, or receipt?'],
              ['serial_image_available', 'Do you have proof of the serial number or product identity?'],
              ['fault_evidence_available', 'Do you have evidence that shows the fault or symptom?'],
              ['repair_report_available', 'Do you have an external repair report?', previousRepair === 'Yes'],
            ]
              .filter(([, , visible = true]) => visible)
              .map(([field, label]) => (
                <div key={field} style={{ border: '1px solid #cbd5e1', borderRadius: '10px', padding: '14px', background: '#ffffff' }}>
                  <strong style={{ display: 'block', fontSize: '13px', marginBottom: '10px' }}>{label}</strong>
                  <div style={{ display: 'flex', gap: '14px' }}>
                    {['Yes', 'No'].map((choice) => (
                      <label key={choice} style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '13.5px' }}>
                        <input
                          type="radio"
                          name={field}
                          value={choice}
                          checked={evidenceAnswers[field] === choice}
                          onChange={() => setEvidenceAnswers((current) => ({ ...current, [field]: choice }))}
                        />
                        {choice}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        </section>

        {/* FORM ACTIONS */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '12px',
            alignItems: 'center',
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
            style={{ minWidth: '240px', padding: '12px 24px', fontSize: '14px', fontWeight: 700 }}
          >
            {submitting ? 'Evaluating AI Model...' : 'Submit Warranty Claim →'}
          </button>
        </div>
      </form>
    </div>
  )
}

// ==============================================================================
// 2. REVIEWER - DASHBOARD QUEUE & SPLIT DETAIL VIEW
// ==============================================================================

export function ReviewerWarrantyDesk() {
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedTicket, setSelectedTicket] = useState(null)

  // Filters
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL_QUEUE')

  // Review Decision State
  const [reviewerNote, setReviewerNote] = useState('')
  const [submittingDecision, setSubmittingDecision] = useState(false)
  const [decisionFeedback, setDecisionFeedback] = useState('')

  useEffect(() => {
    api('/api/warranty/reviewer/tickets')
      .then((response) => setTickets(response.tickets || []))
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [])

  async function handleRecordDecision(decision) {
    if (!selectedTicket) return
    setSubmittingDecision(true)
    setError('')
    try {
      const response = await api(`/api/warranty/reviewer/tickets/${encodeURIComponent(selectedTicket.ticket_id)}/decision`, {
        method: 'POST',
        body: JSON.stringify({ decision, reviewer_note: reviewerNote.trim() || null }),
      })
      const updatedTicket = { ...selectedTicket, ...response.ticket }
      setTickets((current) => current.map((ticket) => ticket.ticket_id === updatedTicket.ticket_id ? updatedTicket : ticket))
      setSelectedTicket(updatedTicket)
      setReviewerNote('')
      setDecisionFeedback(response.message)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmittingDecision(false)
    }
  }

  const filteredTickets = useMemo(() => {
    return tickets.filter((t) => {
      if (statusFilter === 'WAITING' && t.status !== 'WAITING_REVIEW') return false
      if (statusFilter === 'REVIEWED' && t.status !== 'REVIEWED') return false
      if (search.trim()) {
        const q = search.trim().toLowerCase()
        const matchId = (t.ticket_id || '').toLowerCase().includes(q)
        const matchName = (t.customer_name || '').toLowerCase().includes(q)
        const matchModel = (t.product_model || '').toLowerCase().includes(q)
        const matchCode = (t.product_code || '').toLowerCase().includes(q)
        return matchId || matchName || matchModel || matchCode
      }
      return true
    })
  }, [tickets, statusFilter, search])

  // ----------------------------------------------------------------------------
  // SPLIT DETAIL VIEW
  // ----------------------------------------------------------------------------
  if (selectedTicket) {
    const isReviewed = selectedTicket.status === 'REVIEWED'
    const isWarranty = selectedTicket.ai_prediction === 'WARRANTY'
    const isNotWarranty = selectedTicket.ai_prediction === 'NOT_WARRANTY'
    const feats = selectedTicket.model_features || {}
    const derived = selectedTicket.derived_data || selectedTicket.derived || {}
    const policy = selectedTicket.policy || derived.policy || {}
    const policyMissingEvidence = policy.missing_evidence || derived.policy_missing_evidence || []
    const policyEvidenceComplete = policy.required_evidence_complete ?? derived.policy_required_evidence_complete

    return (
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px' }}>
        {/* Navigation & Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
          <button
            className="button secondary"
            onClick={() => {
              setSelectedTicket(null)
              setDecisionFeedback('')
            }}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            ← Back to Claim Queue
          </button>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', color: '#64748b' }}>Processing status:</span>
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
          <div className="alert success" style={{ marginBottom: '18px' }}>
            ✓ {decisionFeedback}
          </div>
        )}

        {/* 2-Column Split View */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1.3fr) minmax(0, 0.7fr)',
            gap: '20px',
            alignItems: 'start',
          }}
        >
          {/* LEFT COLUMN: CUSTOMER INPUTS & 14 DERIVED FEATURES */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Customer & Product Card */}
            <div className="panel" style={{ padding: '20px', borderRadius: '12px', background: '#ffffff', border: '1px solid #e2e8f0' }}>
              <p className="eyebrow" style={{ color: '#2563eb', fontWeight: 700, fontSize: '11px' }}>
                CUSTOMER & EQUIPMENT RECORD
              </p>
              <h3 style={{ margin: '4px 0 14px', fontSize: '18px' }}>
                {selectedTicket.product_name} ({selectedTicket.product_model})
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', fontSize: '12.5px' }}>
                <div>
                  <span style={{ color: '#64748b', display: 'block', fontSize: '11px' }}>Customer Name:</span>
                  <strong>{selectedTicket.customer_name}</strong>
                </div>
                <div>
                  <span style={{ color: '#64748b', display: 'block', fontSize: '11px' }}>Contact Email:</span>
                  <strong>{selectedTicket.customer_email}</strong>
                </div>
                <div>
                  <span style={{ color: '#64748b', display: 'block', fontSize: '11px' }}>Product Code:</span>
                  <strong className="mono" style={{ color: '#2563eb' }}>{selectedTicket.product_code}</strong>
                </div>
                <div>
                  <span style={{ color: '#64748b', display: 'block', fontSize: '11px' }}>Serial Number:</span>
                  <strong className="mono">{selectedTicket.serial_number}</strong>
                </div>
                <div>
                  <span style={{ color: '#64748b', display: 'block', fontSize: '11px' }}>Purchase Date:</span>
                  <span>{selectedTicket.purchase_date}</span>
                </div>
                <div>
                  <span style={{ color: '#64748b', display: 'block', fontSize: '11px' }}>Warranty Expiry:</span>
                  <span>{selectedTicket.warranty_expiry}</span>
                </div>
              </div>
            </div>

            {/* Claim Incident & Evidence */}
            <div className="panel" style={{ padding: '20px', borderRadius: '12px', background: '#ffffff', border: '1px solid #e2e8f0' }}>
              <p className="eyebrow" style={{ color: '#2563eb', fontWeight: 700, fontSize: '11px' }}>
                FAULT DESCRIPTION
              </p>

              <div style={{ margin: '10px 0 0', padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '13px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
                  <span style={{ color: '#64748b', fontSize: '11.5px' }}>
                    Incident Date: <strong>{selectedTicket.incident_date}</strong> · Previous Repair: <strong>{selectedTicket.previous_repair}</strong>
                  </span>
                  {selectedTicket.problem_category && (
                    <span style={{ fontSize: '11.5px', fontWeight: 700, padding: '2px 8px', borderRadius: '4px', background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe' }}>
                      Category: {selectedTicket.problem_category}
                    </span>
                  )}
                </div>
                <p style={{ margin: 0, color: '#1e293b', fontStyle: 'italic' }}>
                  "{selectedTicket.fault_description}"
                </p>
              </div>

              {/* Legacy Evidence Files List if present */}
              {selectedTicket.evidence && Object.values(selectedTicket.evidence).some(Boolean) && (
                <div style={{ marginTop: '14px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#334155', display: 'block', marginBottom: '8px' }}>
                    Attached Evidence Files:
                  </span>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '8px', fontSize: '12px' }}>
                    {Object.entries(selectedTicket.evidence).map(([key, file]) => (
                      <div key={key} style={{ background: '#f8fafc', padding: '8px 10px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                        <span style={{ fontSize: '11px', color: '#64748b', display: 'block', textTransform: 'capitalize' }}>
                          {key.replace('_', ' ')}:
                        </span>
                        {file ? (
                          <span style={{ color: '#16a34a', fontWeight: 600 }}>✓ {file.filename}</span>
                        ) : (
                          <span style={{ color: '#94a3b8' }}>— Not attached</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Active V3 Features Grid */}
            <div className="panel" style={{ padding: '20px', borderRadius: '12px', background: '#ffffff', border: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <div>
                  <p className="eyebrow" style={{ color: '#2563eb', fontWeight: 700, fontSize: '11px' }}>
                    FEATURE ENGINEERING ENGINE
                  </p>
                  <h4 style={{ margin: 0, fontSize: '15px' }}>14 Features Used by Model V3</h4>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px', fontSize: '12px' }}>
                {MODEL_14_FEATURES.map((feat) => {
                  const val = feats[feat]
                  return (
                    <div key={feat} style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                      <span style={{ fontSize: '11px', color: '#64748b', display: 'block' }}>{feat}</span>
                      <strong style={{ fontSize: '13px', color: '#0f172a' }}>{String(val ?? '—')}</strong>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Category policy reference for reviewer decisions */}
            <div className="panel" style={{ padding: '20px', borderRadius: '12px', background: '#eff6ff', border: '1px solid #bfdbfe' }}>
              <p className="eyebrow" style={{ color: '#1d4ed8', fontWeight: 800, fontSize: '11px' }}>
                POLICY REFERENCE
              </p>
              <h4 style={{ margin: '4px 0 12px', fontSize: '15px' }}>Category warranty rules</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px', fontSize: '12px' }}>
                <div><span style={{ color: '#64748b', display: 'block', fontSize: '11px' }}>Product category</span><strong>{policy.category || selectedTicket.product_category || derived.policy_category || '—'}</strong></div>
                <div><span style={{ color: '#64748b', display: 'block', fontSize: '11px' }}>Component</span><strong>{policy.component || derived.policy_component || selectedTicket.claimed_component || 'Main Unit'}</strong></div>
                <div><span style={{ color: '#64748b', display: 'block', fontSize: '11px' }}>Policy version</span><strong>{policy.version || derived.policy_version || '—'}</strong></div>
                <div><span style={{ color: '#64748b', display: 'block', fontSize: '11px' }}>Fault coverage</span><strong style={{ color: feats.FaultCovered === 'No' ? '#dc2626' : '#15803d' }}>{feats.FaultCovered || 'Unknown'}</strong></div>
                <div><span style={{ color: '#64748b', display: 'block', fontSize: '11px' }}>Reporting window</span><strong>{feats.ClaimReportingWithinPeriod || 'Unknown'}</strong></div>
                <div><span style={{ color: '#64748b', display: 'block', fontSize: '11px' }}>Required evidence</span><strong>{policyEvidenceComplete || feats.RequiredDocumentsComplete || 'Unknown'}</strong></div>
              </div>
              {(policy.excluded_causes || policy.covered_faults || policyMissingEvidence.length > 0) && (
                <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid #bfdbfe', fontSize: '12px' }}>
                  {policy.covered_faults?.length > 0 && <p style={{ margin: '4px 0' }}><strong>Covered faults:</strong> {policy.covered_faults.join(', ')}</p>}
                  {policy.excluded_causes?.length > 0 && <p style={{ margin: '4px 0', color: '#b91c1c' }}><strong>Excluded causes:</strong> {policy.excluded_causes.join(', ')}</p>}
                  {policyMissingEvidence.length > 0 && <p style={{ margin: '4px 0', color: '#b45309' }}><strong>Missing policy evidence:</strong> {policyMissingEvidence.join(', ')}</p>}
                </div>
              )}
              <p style={{ margin: '12px 0 0', fontSize: '11px', color: '#475569' }}>Use this policy summary with the evidence and AI result before recording the official decision.</p>
            </div>
          </div>

          {/* RIGHT COLUMN: AI PREDICTION & REVIEWER DECISION */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* AI Prediction Box */}
            <div
              className="panel"
              style={{
                padding: '22px',
                borderRadius: '12px',
                background: '#ffffff',
                border: '1px solid #cbd5e1',
                textAlign: 'center',
              }}
            >
              <span style={{ fontSize: '11.5px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#3b82f6' }}>
                AI Model V3 Prediction
              </span>

              <div style={{ margin: '14px 0 6px' }}>
                <div
                  style={{
                    fontSize: '26px',
                    fontWeight: 900,
                    color: isWarranty ? '#16a34a' : isNotWarranty ? '#dc2626' : '#d97706',
                  }}
                >
                  {selectedTicket.ai_prediction}
                </div>
                <div style={{ fontSize: '12.5px', fontWeight: 700, color: '#64748b', marginTop: '2px' }}>
                  Model Confidence: {Math.round((selectedTicket.ai_confidence || 0.95) * 100)}%
                </div>
              </div>

              <div
                style={{
                  padding: '10px 12px',
                  borderRadius: '6px',
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  fontSize: '12px',
                  color: '#475569',
                  textAlign: 'left',
                  marginTop: '12px',
                }}
              >
                <strong>Evaluation: </strong>{selectedTicket.ai_reason}
              </div>
            </div>

            {/* Reviewer Decision Form */}
            <div
              className="panel"
              style={{
                padding: '22px',
                borderRadius: '12px',
                background: '#ffffff',
                border: '1px solid #cbd5e1',
              }}
            >
              <p className="eyebrow" style={{ color: '#0f172a', fontWeight: 800, fontSize: '11px' }}>
                OFFICIAL GROUND TRUTH SIGN-OFF
              </p>
              <h4 style={{ margin: '4px 0 12px', fontSize: '14.5px' }}>
                Record Reviewer Ground Truth:
              </h4>

              {isReviewed ? (
                <div style={{ background: '#f8fafc', padding: '14px', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12.5px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ color: '#64748b' }}>Official Ground Truth:</span>
                    <strong style={{ color: selectedTicket.ground_truth === 'Valid Claim' ? '#16a34a' : '#dc2626' }}>
                      {selectedTicket.ground_truth}
                    </strong>
                  </div>
                  <div>
                    <span style={{ color: '#64748b', display: 'block', marginBottom: '2px' }}>Reviewer Audit Note:</span>
                    <p style={{ margin: 0, color: '#1e293b', fontStyle: 'italic' }}>
                      "{selectedTicket.reviewer_note}"
                    </p>
                  </div>
                  <div style={{ marginTop: '10px', fontSize: '11px', color: '#94a3b8' }}>
                    Reviewed on {new Date(selectedTicket.reviewed_at).toLocaleString()}
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <textarea
                    rows="3"
                    placeholder="Enter audit notes or justification for this decision..."
                    value={reviewerNote}
                    onChange={(e) => setReviewerNote(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      border: '1px solid #cbd5e1',
                      fontSize: '12.5px',
                    }}
                  />

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <button
                      type="button"
                      className="button primary"
                      disabled={submittingDecision}
                      onClick={() => handleRecordDecision('APPROVE')}
                      style={{ background: '#16a34a', borderColor: '#16a34a', padding: '10px' }}
                    >
                      ✓ Approve (Valid)
                    </button>
                    <button
                      type="button"
                      className="button secondary"
                      disabled={submittingDecision}
                      onClick={() => handleRecordDecision('REJECT')}
                      style={{ color: '#dc2626', borderColor: '#fca5a5', padding: '10px' }}
                    >
                      ✕ Reject (Invalid)
                    </button>
                  </div>
                  <p style={{ margin: 0, fontSize: '11px', color: '#94a3b8', textAlign: 'center' }}>
                    Your decision establishes official Ground Truth for the ML retraining dataset.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ----------------------------------------------------------------------------
  // QUEUE TABLE VIEW
  // ----------------------------------------------------------------------------
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px' }}>
      <header className="page-header" style={{ marginBottom: '16px' }}>
        <div>
          <p className="eyebrow">Reviewer Workspace</p>
          <h1>Warranty Reviewer Desk</h1>
        </div>
      </header>

      {/* Toolbar */}
      <div className="toolbar" style={{ marginBottom: '16px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="Search ticket ID, customer, model, product code..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1, minWidth: '240px', padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px' }}
        />

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px' }}
        >
          <option value="ALL_QUEUE">All Claims ({tickets.length})</option>
          <option value="WAITING">Awaiting Review ({tickets.filter((t) => t.status === 'WAITING_REVIEW').length})</option>
          <option value="REVIEWED">Reviewed ({tickets.filter((t) => t.status === 'REVIEWED').length})</option>
        </select>
      </div>

      {/* Claims Table */}
      <div className="panel" style={{ padding: 0, borderRadius: '12px', overflow: 'hidden', border: '1px solid #e2e8f0' }}>
        <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left' }}>
              <th style={{ padding: '12px 16px' }}>Ticket ID</th>
              <th style={{ padding: '12px 16px' }}>Customer & Equipment</th>
              <th style={{ padding: '12px 16px' }}>Fault Summary</th>
              <th style={{ padding: '12px 16px' }}>AI Prediction</th>
              <th style={{ padding: '12px 16px' }}>Status</th>
              <th style={{ padding: '12px 16px' }}>Ground Truth</th>
              <th style={{ padding: '12px 16px', textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredTickets.map((t) => {
              const isReviewed = t.status === 'REVIEWED'
              return (
                <tr key={t.ticket_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '12px 16px' }}>
                    <strong className="mono" style={{ color: '#2563eb' }}>{t.ticket_id}</strong>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>{new Date(t.created_at).toLocaleDateString()}</div>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <strong>{t.customer_name}</strong>
                    <div style={{ fontSize: '12px', color: '#64748b' }}>{t.product_name} · <span className="mono">{t.product_code}</span></div>
                  </td>
                  <td style={{ padding: '12px 16px', maxWidth: '280px' }}>
                    {t.problem_category && (
                      <div style={{ marginBottom: '4px' }}>
                        <span style={{
                          fontSize: '11px',
                          fontWeight: 600,
                          padding: '2px 7px',
                          borderRadius: '4px',
                          background: '#f1f5f9',
                          color: '#1e293b',
                          border: '1px solid #e2e8f0',
                          display: 'inline-block',
                        }}>
                          {t.problem_category}
                        </span>
                      </div>
                    )}
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '12.5px', color: '#475569' }} title={t.fault_description}>
                      {t.fault_description}
                    </div>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <span
                      style={{
                        fontSize: '11.5px',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background: t.ai_prediction === 'WARRANTY' ? '#dcfce7' : t.ai_prediction === 'NOT_WARRANTY' ? '#fee2e2' : '#fef9c3',
                        color: t.ai_prediction === 'WARRANTY' ? '#15803d' : t.ai_prediction === 'NOT_WARRANTY' ? '#b91c1c' : '#a16207',
                      }}
                    >
                      {t.ai_prediction}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <span className="days-left-badge active" style={{ fontSize: '11px' }}>
                      {t.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    {isReviewed ? (
                      <strong style={{ color: t.ground_truth === 'Valid Claim' ? '#16a34a' : '#dc2626' }}>
                        {t.ground_truth}
                      </strong>
                    ) : (
                      <span style={{ color: '#94a3b8' }}>— Pending</span>
                    )}
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                    <button
                      className="button secondary"
                      onClick={() => setSelectedTicket(t)}
                      style={{ padding: '4px 10px', fontSize: '12px' }}
                    >
                      {isReviewed ? 'View Details →' : 'Review →'}
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ==============================================================================
// 3. RETRAINING DATASET VIEWER
// ==============================================================================

export function WarrantyRetrainingDataset() {
  const tickets = loadStoredTickets().filter((t) => t.ground_truth != null)

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px' }}>
      <header className="page-header" style={{ marginBottom: '16px' }}>
        <div>
          <p className="eyebrow">ML Retraining Pipeline</p>
          <h1>Retraining Dataset (14 Features + Ground Truth)</h1>
        </div>
      </header>

      <div className="panel" style={{ padding: '16px', borderRadius: '12px', background: '#f8fafc', border: '1px solid #e2e8f0', marginBottom: '16px' }}>
        <p style={{ margin: 0, fontSize: '13px', color: '#475569' }}>
          This table feeds the continuous learning cycle for Python Model V3. Each ticket contains the 14 engineered features alongside the reviewer's official Ground Truth label.
        </p>
      </div>

      <div className="panel" style={{ padding: 0, borderRadius: '12px', overflow: 'hidden', border: '1px solid #e2e8f0' }}>
        <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left' }}>
              <th style={{ padding: '10px 14px' }}>Ticket ID</th>
              <th style={{ padding: '10px 14px' }}>Product</th>
              <th style={{ padding: '10px 14px' }}>Fault Covered</th>
              <th style={{ padding: '10px 14px' }}>Remaining Days</th>
              <th style={{ padding: '10px 14px' }}>AI Prediction</th>
              <th style={{ padding: '10px 14px' }}>Ground Truth</th>
              <th style={{ padding: '10px 14px' }}>Audit Note</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((t) => (
              <tr key={t.ticket_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={{ padding: '10px 14px' }}>
                  <strong className="mono" style={{ color: '#2563eb' }}>{t.ticket_id}</strong>
                </td>
                <td style={{ padding: '10px 14px' }}>{t.product_name}</td>
                <td style={{ padding: '10px 14px' }}>{t.model_features?.FaultCovered || '—'}</td>
                <td style={{ padding: '10px 14px' }}>{t.model_features?.WarrantyRemainingDays ?? '—'}d</td>
                <td style={{ padding: '10px 14px' }}>{t.ai_prediction}</td>
                <td style={{ padding: '10px 14px' }}>
                  <strong style={{ color: t.ground_truth === 'Valid Claim' ? '#16a34a' : '#dc2626' }}>
                    {t.ground_truth}
                  </strong>
                </td>
                <td style={{ padding: '10px 14px', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {t.reviewer_note || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export const RetrainingDatasetViewer = WarrantyRetrainingDataset
