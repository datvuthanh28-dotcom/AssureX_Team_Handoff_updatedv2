import { useState } from 'react'

function CustomerClaimForm({ onCancel }) {
  const [formData, setFormData] = useState({
    customerName: '',
    email: '',
    productName: '',
    serialNumber: '',
    purchaseDate: '',
    claimAmount: '',
    faultDescription: '',
  })

  function handleChange(event) {
    const { name, value } = event.target

    setFormData((current) => ({
      ...current,
      [name]: value,
    }))
  }

  function handleSubmit(event) {
    event.preventDefault()

    console.log('Customer claim:', formData)
  }

  return (
    <form className="claim-form" onSubmit={handleSubmit}>
      <section className="form-section">
        <div className="form-section-header">
          <p className="eyebrow">Warranty Claim</p>
          <h2>Submit a New Claim</h2>
        </div>

        <div className="form-grid">
          <label className="form-field">
            <span>Full Name</span>
            <input
              name="customerName"
              value={formData.customerName}
              onChange={handleChange}
              required
            />
          </label>

          <label className="form-field">
            <span>Email</span>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
            />
          </label>

          <label className="form-field">
            <span>Product Name</span>
            <input
              name="productName"
              value={formData.productName}
              onChange={handleChange}
              required
            />
          </label>

          <label className="form-field">
            <span>Serial Number</span>
            <input
              name="serialNumber"
              value={formData.serialNumber}
              onChange={handleChange}
              required
            />
          </label>

          <label className="form-field">
            <span>Purchase Date</span>
            <input
              type="date"
              name="purchaseDate"
              value={formData.purchaseDate}
              onChange={handleChange}
              required
            />
          </label>

          <label className="form-field">
            <span>Claim Amount</span>
            <input
              type="number"
              min="0"
              step="0.01"
              name="claimAmount"
              value={formData.claimAmount}
              onChange={handleChange}
              required
            />
          </label>
        </div>

        <label className="form-field customer-description">
          <span>Describe the Problem</span>
          <textarea
            name="faultDescription"
            value={formData.faultDescription}
            onChange={handleChange}
            rows="5"
            required
          />
        </label>
      </section>

      <div className="form-actions">
        <button
          type="button"
          className="nav-item customer-cancel"
          onClick={onCancel}
        >
          Cancel
        </button>

        <button type="submit" className="primary-button">
          Submit Claim
        </button>
      </div>
    </form>
  )
}

export default CustomerClaimForm
