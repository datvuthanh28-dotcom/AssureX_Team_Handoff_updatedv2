import { useEffect, useState } from 'react'

const API_URL = 'http://127.0.0.1:8000'

function ClaimHistory() {
  const [claims, setClaims] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedClaim, setSelectedClaim] = useState(null)

  useEffect(() => {
    fetch(`${API_URL}/api/claims`)
      .then((response) => response.json())
      .then((data) => setClaims(data))
      .catch((error) => {
        console.error('Failed to load claim history:', error)
      })
      .finally(() => setLoading(false))
  }, [])

  async function openClaim(claimId) {
    try {
      const response = await fetch(
        `${API_URL}/api/claims/${claimId}`
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to load claim.')
      }

      setSelectedClaim(data)
    } catch (error) {
      console.error(error)
    }
  }

  if (loading) {
    return <p>Loading claim history...</p>
  }

  return (
    <>
      <section className="form-section">
        <div className="form-section-header">
          <p className="eyebrow">Stored Claims</p>
          <h2>Claim History</h2>
        </div>

        <div className="history-table-wrapper">
          <table className="history-table">
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
              {claims.map((claim) => (
                <tr
                  key={claim.id}
                  onClick={() => openClaim(claim.claim_id)}
                  style={{ cursor: 'pointer' }}
                >
                  <td>{claim.claim_id}</td>
                  <td>{claim.predicted_class}</td>
                  <td>
                    {(claim.confidence * 100).toFixed(2)}%
                  </td>
                  <td>{claim.model_name}</td>
                  <td>
                    {new Date(claim.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {selectedClaim && (
        <section className="form-section claim-detail">
          <div className="form-section-header">
            <p className="eyebrow">Claim Detail</p>
            <h2>{selectedClaim.claim_id}</h2>
          </div>

          <div className="detail-grid">
            <div>
              <span>Prediction</span>
              <strong>{selectedClaim.predicted_class}</strong>
            </div>

            <div>
              <span>Confidence</span>
              <strong>
                {(selectedClaim.confidence * 100).toFixed(2)}%
              </strong>
            </div>

            <div>
              <span>Model</span>
              <strong>{selectedClaim.model_name}</strong>
            </div>

            <div>
              <span>Created</span>
              <strong>
                {new Date(
                  selectedClaim.created_at
                ).toLocaleString()}
              </strong>
            </div>
          </div>
        </section>
      )}
    </>
  )
}

export default ClaimHistory
