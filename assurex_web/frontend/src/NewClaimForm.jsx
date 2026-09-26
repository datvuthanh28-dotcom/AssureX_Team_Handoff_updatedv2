import { useState } from 'react'
import { claimFieldGroups } from './claimFields'

const API_URL = 'http://127.0.0.1:8000'

function NewClaimForm() {
  const [claimId, setClaimId] = useState('')
  const [formData, setFormData] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  function handleChange(field, value) {
    setFormData((current) => ({
      ...current,
      [field.name]:
        field.type === 'number' && value !== ''
          ? Number(value)
          : value,
    }))
  }

  async function handleSubmit(event) {
    event.preventDefault()

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const response = await fetch(`${API_URL}/api/claims/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          claim_id: claimId,
          input_data: formData,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || 'Claim classification failed.'
        )
      }

      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <form className="claim-form" onSubmit={handleSubmit}>
        <section className="form-section">
          <div className="form-section-header">
            <div>
              <p className="eyebrow">Claim Identification</p>
              <h2>Claim Information</h2>
            </div>
          </div>

          <div className="form-grid">
            <label className="form-field">
              <span>Claim ID</span>

              <input
                type="text"
                value={claimId}
                onChange={(event) => setClaimId(event.target.value)}
                placeholder="e.g. CLM01001"
                required
              />
            </label>
          </div>
        </section>

        {claimFieldGroups.map((group) => (
          <section className="form-section" key={group.title}>
            <div className="form-section-header">
              <h3>{group.title}</h3>
            </div>

            <div className="form-grid">
              {group.fields.map((field) => (
                <label className="form-field" key={field.name}>
                  <span>{field.label}</span>

                  {field.type === 'select' ? (
                    <select
                      value={formData[field.name] ?? ''}
                      onChange={(event) =>
                        handleChange(field, event.target.value)
                      }
                      required
                    >
                      <option value="">Select...</option>

                      {field.options.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="number"
                      min={field.min}
                      max={field.max}
                      step={field.step}
                      value={formData[field.name] ?? ''}
                      onChange={(event) =>
                        handleChange(field, event.target.value)
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
          <div className="form-section">
            <strong>Error:</strong> {error}
          </div>
        )}

        {result && (
          <section className="form-section">
            <p className="eyebrow">Classification Result</p>

            <h2>{result.predicted_class}</h2>

            <p>
              Confidence:{' '}
              <strong>
                {(result.confidence * 100).toFixed(2)}%
              </strong>
            </p>

            <p>
              Model: {result.model_name}
            </p>
          </section>
        )}

        <div className="form-actions">
          <button
            type="submit"
            className="primary-button"
            disabled={loading}
          >
            {loading ? 'Classifying...' : 'Classify Claim'}
          </button>
        </div>
      </form>
    </>
  )
}

export default NewClaimForm
