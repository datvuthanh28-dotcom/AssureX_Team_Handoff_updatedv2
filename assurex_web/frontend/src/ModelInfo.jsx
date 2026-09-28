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
          <strong>99.11%</strong>
        </div>
      </section>

      <section className="stats-grid model-stats">
        <div className="stat-card">
          <span>Macro F1</span>
          <strong>99.11%</strong>
          <small>Python Gradient Boosting</small>
        </div>

        <div className="stat-card">
          <span>Mean Confidence</span>
          <strong>93.93%</strong>
          <small>Python Gradient Boosting</small>
        </div>

        <div className="stat-card">
          <span>Test Errors</span>
          <strong>2</strong>
          <small>2 / 225 claims</small>
        </div>

        <div className="stat-card">
          <span>AUC-ROC</span>
          <strong>99.96%</strong>
          <small>Python Gradient Boosting</small>
        </div>
      </section>

      <section className="form-section">
        <div className="form-section-header">
          <p className="eyebrow">Model Comparison</p>
          <h2>Python V3 vs GTM G2 V3</h2>
        </div>

        <div className="history-table-wrapper">
          <table className="history-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Python</th>
                <th>GTM G2 V3</th>
              </tr>
            </thead>

            <tbody>
              <tr>
                <td>Accuracy</td>
                <td>99.11%</td>
                <td>86.22%</td>
              </tr>

              <tr>
                <td>Macro Precision</td>
                <td>99.13%</td>
                <td>87.52%</td>
              </tr>

              <tr>
                <td>Macro Recall</td>
                <td>99.11%</td>
                <td>86.22%</td>
              </tr>

              <tr>
                <td>Macro F1</td>
                <td>99.11%</td>
                <td>86.10%</td>
              </tr>

              <tr>
                <td>Mean Confidence</td>
                <td>93.93%</td>
                <td>87.67%</td>
              </tr>

              <tr>
                <td>AUC-ROC</td>
                <td>99.96%</td>
                <td>92.48%</td>
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
