import { useEffect, useState } from 'react'
import { api } from './api'
import './PipelineWorkspace.css'

export const pipelinePages = [
  ['ml-audit', '01 · Data audit'], ['ml-preprocessing', '02 · Preprocessing'],
  ['ml-text', '03 · Text / tabular models'], ['ml-image', '04 · Google image model'],
  ['ml-comparison', '05 · Model selection'],
]

function value(cell) {
  if (cell === null || cell === undefined || cell === '') return '—'
  return typeof cell === 'object' ? JSON.stringify(cell) : String(cell)
}
function Report({ title, report, heatmap = false }) {
  const [expanded, setExpanded] = useState(false)
  const rows = report?.rows || []
  const columns = Object.keys(rows[0] || {})
  return <section className="panel pipeline-report">
    <div className="panel-heading"><h2>{title}</h2><span className="pipeline-count">{rows.length} rows</span></div>
    {report?.source && <p className="pipeline-source">{report.source}</p>}
    {!rows.length ? <p className="pipeline-notice">Chưa có báo cáo cho bước này.</p> : <>
      <div className="table-wrapper"><table className="data-table"><thead><tr>{columns.map(c => <th key={c}>{c || 'Feature'}</th>)}</tr></thead>
        <tbody>{(expanded ? rows : rows.slice(0, 12)).map((row, i) => <tr key={i}>{columns.map((c, j) => {
          const number = Number(row[c])
          const color = heatmap && j > 0 && row[c] !== '' && Number.isFinite(number) ? { background: number >= 0 ? `rgba(14, 150, 128, ${Math.abs(number) * .65})` : `rgba(228, 123, 79, ${Math.abs(number) * .65})` } : undefined
          return <td key={c} style={color}>{heatmap && j > 0 && Number.isFinite(number) && row[c] !== '' ? number.toFixed(2) : value(row[c])}</td>
        })}</tr>)}</tbody></table></div>
      {rows.length > 12 && <button className="text-button" onClick={() => setExpanded(!expanded)}>{expanded ? 'Thu gọn' : `Xem toàn bộ ${rows.length} dòng`}</button>}
    </>}
  </section>
}
function Note({ title, children }) { return <section className="pipeline-note"><strong>{title}</strong><p>{children}</p></section> }
function FoldStatus() { return <Note title="Cross-validation · 5 folds / Hyperparameter tuning">Báo cáo hiện tại dùng validation holdout đã lưu làm cơ sở chọn model; tập test khóa chỉ dùng cho đánh giá cuối sau khi freeze.</Note> }

export default function PipelineWorkspace({ page, onNavigate }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  useEffect(() => { let active = true; api('/api/pipeline').then(d => { if (active) setData(d) }).catch(e => { if (active) setError(e.message) }); return () => { active = false } }, [])
  const index = pipelinePages.findIndex(([key]) => key === page)
  async function exportFeedback() {
    setBusy(true); setMessage('')
    try {
      const feedback = await api('/api/appeals/feedback/export')
      const url = URL.createObjectURL(new Blob([JSON.stringify(feedback, null, 2)], { type: 'application/json' }))
      const link = document.createElement('a'); link.href = url; link.download = 'assurex-reviewed-feedback.json'; link.click(); URL.revokeObjectURL(url)
      setMessage(`Đã xuất ${feedback.records.length} claim được reviewer xác nhận. Chưa khởi chạy huấn luyện hoặc thay model production.`)
    } catch (e) { setMessage(e.message) } finally { setBusy(false) }
  }
  if (error) return <div className="state-card" role="alert">{error}<button className="button secondary" onClick={() => window.location.reload()}>Thử lại</button></div>
  if (!data) return <div className="state-card">Đang đọc báo cáo ML V3…</div>
  const r = data.reports
  return <div className="pipeline-workspace">
    <header className="page-header"><div><p className="eyebrow">ADMIN WORKSPACE / MACHINE LEARNING</p><h1>{pipelinePages[index]?.[1].slice(5)}</h1><p className="page-description">Pipeline V3 · Báo cáo từ dữ liệu và artifacts hiện có</p></div><span className="pipeline-version">V3 / {String(index + 1).padStart(2, '0')} OF 05</span></header>
    <nav className="pipeline-steps" aria-label="ML pipeline">{pipelinePages.map(([key, label], i) => <button key={key} className={key === page ? 'active' : ''} onClick={() => onNavigate(key)} aria-current={key === page ? 'step' : undefined}><span>{String(i + 1).padStart(2, '0')}</span>{label.slice(5)}</button>)}</nav>
    {page === 'ml-audit' && <>
      <section className="stats-grid">{[['Bản ghi ban đầu', data.audit.rows], ['Số cột', data.audit.columns], ['Ô thiếu dữ liệu', data.audit.missing], ['Dòng trùng hoàn toàn', data.audit.duplicates]].map(([label, count]) => <article className="stat-card" key={label}><span>{label}</span><strong>{count.toLocaleString()}</strong><small>assurex_v3_raw.csv</small></article>)}</section>
      <Note title="01 / Hiểu dữ liệu trước khi xử lý">Kiểm tra schema, kiểu dữ liệu được suy luận, số giá trị thiếu và cardinality theo cột. Duplicate ở đây là các dòng giống hoàn toàn; các trùng lặp nghiệp vụ cần đối chiếu ClaimID trong bước làm sạch.</Note>
      <Report title="Data quality · Column profile" report={{ source: 'data/raw/assurex_v3_raw.csv', rows: data.audit.profile }} />
    </>}
    {page === 'ml-preprocessing' && <>
      <Note title="02 / Làm sạch → chọn cột → mã hóa → scale → split">Pipeline hiện tại dùng imputation, OneHotEncoder và StandardScaler trong sklearn Pipeline, fit trên train. Bảng dưới ghi lại việc loại cột nhiễu, rò rỉ nhãn và các cặp tương quan cần xem xét.</Note>
      <Report title="Cleaning summary" report={r.cleaning} /><Report title="Missing values · Before / after" report={r.missing} /><Report title="Noise & feature filtering" report={r.filter} />
      <Report title="Correlation matrix · Pearson" report={r.correlation} heatmap /><Note title="Đọc bảng correlation">Xanh: tương quan dương · cam: tương quan âm · độ đậm biểu thị |r|. Tương quan cao là tín hiệu cần đánh giá, không tự động đồng nghĩa phải xóa cột.</Note><Report title="Multicollinearity candidates" report={r.redundancy} />
      <div className="pipeline-split">{Object.entries(data.split.rows || {}).filter(([k]) => k !== 'source').map(([key, count]) => <div key={key}><strong>{key}</strong><span>{count} records</span><small>{Math.round((data.split.split_ratios[key] || 0) * 100)}%</small></div>)}</div><Report title="Train / validation / locked test" report={r.split} />
    </>}
    {page === 'ml-text' && <>
      <Note title="03 / Text & tabular · 3 candidate models">Dữ liệu hiện tại là đặc trưng có cấu trúc từ claim, không phải mô hình NLP trực tiếp trên văn bản tự do. So sánh Logistic Regression, Random Forest và Gradient Boosting bằng validation Macro F1.</Note>
      <FoldStatus /><Report title="Frozen hyperparameters · Final model" report={{ rows: Object.entries(data.freeze.hyperparameters || {}).map(([Parameter, Value]) => ({ Parameter, Value })) }} /><Report title="Candidate model comparison" report={r.models} />
      <Note title={`Feature selection · ${data.selection.initial_feature_count} → ${data.selection.selected_feature_count} features`}>Permutation importance trên validation; theo dõi mức giảm F1 sau mỗi lần bỏ feature và rollback khi vượt ngưỡng. Dataset cuối sử dụng danh sách feature đã được chốt trong artifact V3.</Note>
      <Report title="Feature importance" report={r.importance} /><Report title="Feature removal & rerun history" report={r.selection} />
      <Report title="Final refit · Locked test results" report={r.text_test} /><Report title="Confusion matrix" report={r.text_matrix} />
    </>}
    {page === 'ml-image' && <>
      <Note title="04 / Google Teachable Machine · G2 V3">Nhánh image hiện tại dùng ảnh claim-card sinh từ dữ liệu claim. Đây là mô hình Google Teachable Machine có sẵn trong dự án. Runtime inference: {data.active.google_model?.inference_status || 'unknown'}.</Note><FoldStatus />
      <Report title="Visual feature ablation & model iterations" report={r.image_ablation} />
      <Note title="Feature importance cho nhánh ảnh">Pipeline hiện có dùng visual ablation để đánh giá tác động của nhóm thông tin trên claim-card. Chưa có báo cáo pixel attribution hoặc importance theo feature; không suy diễn từ kết quả của nhánh text.</Note>
      <Report title="Final image model · Locked test" report={r.image_test} /><Report title="Image confusion matrix" report={r.image_matrix} />
    </>}
    {page === 'ml-comparison' && <>
      <section className="hero-card"><div><p className="eyebrow">CURRENT PRODUCTION MODEL</p><h2>{data.active.python_model?.name}</h2><p>{data.active.python_model?.version}</p><p>Được chọn bằng validation; test dùng để đánh giá sau khi freeze.</p></div><div className="metric-highlight"><span>Selected features</span><strong>{data.active.python_model?.selected_feature_count}</strong><small>{data.active.python_model?.runtime_status}</small></div></section>
      <Report title="Text vs Google image · Same locked test" report={r.comparison} />
      <div className="pipeline-two"><Report title="Text model" report={r.text_test} /><Report title="Google image model" report={r.image_test} /></div>
      <Note title="Customer → Prediction → Reviewer → Feedback → Next version">Customer gửi claim, model cung cấp dự đoán, reviewer ra quyết định và xử lý khiếu nại. Chỉ quyết định cuối do reviewer xác nhận, không còn khiếu nại chờ xử lý, được xuất làm dữ liệu ứng viên cho lần huấn luyện kế tiếp.</Note>
      <section className="panel"><h2>Chuẩn bị dữ liệu retraining</h2><p>Xuất feedback đã xác nhận để đưa qua cùng pipeline audit → preprocessing → training → comparison. Huấn luyện và phát hành version mới chưa được tự động hóa trong giao diện này.</p><button className="button primary" disabled={busy} onClick={exportFeedback}>{busy ? 'Đang xuất…' : 'Export reviewed feedback'}</button>{message && <p role="status">{message}</p>}</section>
    </>}
    <footer className="pipeline-footer"><button className="button secondary" disabled={index === 0} onClick={() => onNavigate(pipelinePages[index - 1][0])}>← Bước trước</button><span>Step {index + 1} / 5</span><button className="button primary" disabled={index === 4} onClick={() => onNavigate(pipelinePages[index + 1][0])}>Bước tiếp →</button></footer>
  </div>
}
