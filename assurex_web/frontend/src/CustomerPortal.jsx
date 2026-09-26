import { useState } from 'react'
import CustomerClaimForm from './CustomerClaimForm'

function CustomerPortal() {
  const [page, setPage] = useState('dashboard')

  if (page === 'submit') {
    return (
      <div className="customer-portal">
        <header className="topbar">
          <div>
            <p className="eyebrow">
              AssureX Customer Portal
            </p>

            <h1>Submit Claim</h1>
          </div>
        </header>

        <CustomerClaimForm
          onCancel={() => setPage('dashboard')}
        />
      </div>
    )
  }

  return (
    <div className="customer-portal">
      <header className="topbar">
        <div>
          <p className="eyebrow">
            AssureX Customer Portal
          </p>

          <h1>Warranty Claims</h1>
        </div>

        <button
          className="primary-button"
          onClick={() => setPage('submit')}
        >
          + Submit Claim
        </button>
      </header>

      <section className="hero-card">
        <div>
          <p className="eyebrow">
            Customer Warranty Service
          </p>

          <h2>Manage Your Warranty Claims</h2>

          <p>
            Submit a warranty claim, track its status,
            and review your previous claims.
          </p>
        </div>
      </section>

      <section className="stats-grid">
        <div className="stat-card">
          <span>My Claims</span>
          <strong>—</strong>
          <small>Total submitted claims</small>
        </div>

        <div className="stat-card">
          <span>Under Review</span>
          <strong>—</strong>
          <small>Claims being reviewed</small>
        </div>

        <div className="stat-card">
          <span>Approved</span>
          <strong>—</strong>
          <small>Approved claims</small>
        </div>

        <div className="stat-card">
          <span>Rejected</span>
          <strong>—</strong>
          <small>Rejected claims</small>
        </div>
      </section>
    </div>
  )
}

export default CustomerPortal
