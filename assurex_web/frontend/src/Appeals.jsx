import { useEffect, useState } from 'react'
import { api } from './api'

export function AppealForm({ claim, onSubmitted }) {
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function submit(e) {
    e.preventDefault(); setBusy(true); setMessage('')
    try { await api('/api/appeals', { method: 'POST', body: JSON.stringify({ claim_id: claim.claim_id, reason: reason.trim() }) }); setMessage('Đã gửi khiếu nại. Reviewer sẽ xem xét lại hồ sơ.'); setReason(''); onSubmitted?.() } catch (error) { setMessage(error.message) } finally { setBusy(false) }
  }
  return <form className="panel" onSubmit={submit}><h3>Khiếu nại quyết định từ chối</h3><label className="form-field"><span>Lý do và thông tin bổ sung</span><textarea required minLength={10} maxLength={5000} value={reason} onChange={e => setReason(e.target.value)} /></label><button className="button primary" disabled={busy || reason.trim().length < 10}>{busy ? 'Đang gửi…' : 'Gửi khiếu nại'}</button>{message && <p role="status">{message}</p>}</form>
}

export default function Appeals({ customer = false }) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [filter, setFilter] = useState('All')
  useEffect(() => { api('/api/appeals').then(setRows).catch(e => setError(e.message)).finally(() => setLoading(false)) }, [])
  async function resolve(status) {
    setBusy(true); setError('')
    try {
      const updated = await api(`/api/appeals/${selected.id}`, { method: 'PATCH', body: JSON.stringify({ status, reviewer_comment: comment.trim() }) })
      setRows(current => current.map(row => row.id === updated.id ? updated : row)); setSelected(updated); setComment('')
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  return <><header className="page-header"><div><p className="eyebrow">CLAIM RESOLUTION</p><h1>{customer ? 'Khiếu nại của tôi' : 'Review appeals'}</h1><p className="page-description">Theo dõi và xem xét lại các claim bị từ chối.</p></div></header>
    {error && <p role="alert">{error}</p>}<section className="panel"><label>Trạng thái <select value={filter} onChange={e => setFilter(e.target.value)}>{['All', 'Pending', 'Approved', 'Rejected'].map(s => <option key={s}>{s}</option>)}</select></label>
      {loading ? <p>Đang tải…</p> : !rows.length ? <p>Chưa có khiếu nại.</p> : <div className="table-wrapper"><table className="data-table"><thead><tr><th>Claim</th><th>Lý do</th><th>Trạng thái</th><th>Ngày gửi</th><th /></tr></thead><tbody>{rows.filter(row => filter === 'All' || row.status === filter).map(row => <tr key={row.id}><td>{row.claim_id}</td><td>{row.reason}</td><td>{row.status}</td><td>{new Date(row.created_at).toLocaleString()}</td><td><button className="button secondary" onClick={() => { setSelected(row); setComment(''); setError('') }}>Chi tiết</button></td></tr>)}</tbody></table></div>}</section>
    {selected && <section className="panel"><h2>{selected.claim_id}</h2><p>{selected.reason}</p><p>Trạng thái: {selected.status}</p>{selected.reviewer_comment && <p>Reviewer: {selected.reviewer_comment}</p>}{!customer && selected.status === 'Pending' && <><label className="form-field"><span>Giải thích quyết định</span><textarea value={comment} onChange={e => setComment(e.target.value)} minLength={5} maxLength={5000} /></label><div className="decision-actions"><button className="button primary" disabled={busy || comment.trim().length < 5} onClick={() => resolve('Approved')}>Chấp nhận · Duyệt claim</button><button className="button secondary" disabled={busy || comment.trim().length < 5} onClick={() => resolve('Rejected')}>Từ chối khiếu nại</button></div></>}</section>}
  </>
}
