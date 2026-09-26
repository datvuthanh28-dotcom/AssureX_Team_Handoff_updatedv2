function ModelInfo() {
  return (
    <div className="model-info-page">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Final Model Selection</p>
          <h2>Python Gradient Boosting</h2>
          <p>
            Primary model selected using Macro F1 on the same
            locked 225-claim test set.
          </p>
        </div>

        <div className="metric-highlight">
          <span>Test Accuracy</span>
          <strong>95.56%</strong>
        </div>
      </section>

      <section className="stats-grid model-stats">
        <div className="stat-card">
          <span>Macro F1</span>
          <strong>95.59%</strong>
          <small>Python Gradient Boosting</small>
        </div>

        <div className="stat-card">
          <span>Mean Confidence</span>
          <strong>93.20%</strong>
          <small>Python Gradient Boosting</small>
        </div>

        <div className="stat-card">
          <span>Test Errors</span>
          <strong>10</strong>
          <small>10 / 225 claims</small>
        </div>

        <div className="stat-card">
          <span>SRS ≥ 85%</span>
          <strong>PASS</strong>
          <small>Accuracy requirement</small>
        </div>
      </section>

      <section className="form-section">
        <div className="form-section-header">
          <p className="eyebrow">Model Comparison</p>
          <h2>Python vs GTM G5</h2>
        </div>

        <div className="history-table-wrapper">
          <table className="history-table">
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
                <td>95.56%</td>
                <td>81.33%</td>
              </tr>

              <tr>
                <td>Macro Precision</td>
                <td>95.82%</td>
                <td>83.28%</td>
              </tr>

              <tr>
                <td>Macro Recall</td>
                <td>95.56%</td>
                <td>81.33%</td>
              </tr>

              <tr>
                <td>Macro F1</td>
                <td>95.59%</td>
                <td>81.29%</td>
              </tr>

              <tr>
                <td>Mean Confidence</td>
                <td>93.20%</td>
                <td>87.74%</td>
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
    </div>
  )
}

export default ModelInfo
