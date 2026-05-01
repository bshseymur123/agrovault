import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { shipmentsApi, documentsApi } from '../utils/api'
import { fmt, SHIPMENT_STATUS, CUSTOMS_STATUS, PIPELINE_STEPS, PIPELINE_ORDER } from '../utils/helpers'
import { useNotifyStore } from '../store/store'

const NEXT_STATUS = {
  draft: 'confirmed', confirmed: 'qc_sorting', qc_sorting: 'packaging',
  packaging: 'export_customs', export_customs: 'in_transit',
  in_transit: 'import_customs', import_customs: 'in_storage',
  in_storage: 'delivered', delivered: 'invoiced', invoiced: 'payment_received',
}

export default function ShipmentDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { push } = useNotifyStore()
  const [shipment, setShipment] = useState(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('overview')
  const [advancing, setAdvancing] = useState(false)
  const [documents, setDocuments] = useState([])
  const [uploadType, setUploadType] = useState('Commercial Invoice')
  const [uploading, setUploading] = useState(false)
  const [statusNote, setStatusNote] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)

  // QC form
  const [qcForm, setQcForm] = useState({ lot_number: '', inspector_name: '', grade_a_kg: '', grade_b_kg: '', rejected_kg: '', packaging_type: '5kg export cartons', pallets_count: '', cold_chain_maintained: true, notes: '' })
  const [savingQc, setSavingQc] = useState(false)

  const load = () => {
    shipmentsApi.get(id).then((r) => setShipment(r.data)).finally(() => setLoading(false))
    documentsApi.list(id).then((r) => setDocuments(r.data)).catch(() => {})
  }

  useEffect(() => { load() }, [id])

  const advanceStatus = async () => {
    const next = NEXT_STATUS[shipment.status]
    if (!next) return
    setConfirmOpen(false)
    setAdvancing(true)
    try {
      await shipmentsApi.updateStatus(id, next, statusNote)
      push('success', `Status → ${SHIPMENT_STATUS[next]?.label}`)
      setStatusNote('')
      load()
    } catch { push('error', 'Failed to advance status') }
    finally { setAdvancing(false) }
  }

  const saveQC = async (e) => {
    e.preventDefault(); setSavingQc(true)
    try {
      const p = { ...qcForm, grade_a_kg: parseFloat(qcForm.grade_a_kg) || 0, grade_b_kg: parseFloat(qcForm.grade_b_kg) || 0, rejected_kg: parseFloat(qcForm.rejected_kg) || 0, pallets_count: parseInt(qcForm.pallets_count) || null }
      await shipmentsApi.createQC(id, p)
      push('success', 'QC record saved')
      load()
    } catch { push('error', 'Failed to save QC') }
    finally { setSavingQc(false) }
  }

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}><span className="spinner" /></div>
  if (!shipment) return <div className="empty-state"><div>Shipment not found</div></div>

  const st = SHIPMENT_STATUS[shipment.status] || { label: shipment.status, pill: 'pill-grey' }
  const currentIdx = PIPELINE_ORDER.indexOf(shipment.status)
  const nextStatus = NEXT_STATUS[shipment.status]

  const totalWeight = shipment.weight_kg
  const latestQC = shipment.qc_records?.slice(-1)[0]
  const gradeAPct = latestQC ? ((latestQC.grade_a_kg / totalWeight) * 100).toFixed(1) : null

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 300 }}>{shipment.shipment_ref}</h1>
            <span className={`pill ${st.pill}`}>{st.label}</span>
            <span className={`pill ${shipment.shipment_type === 'import' ? 'pill-blu' : 'pill-grn'}`}>{shipment.shipment_type}</span>
          </div>
          <div style={{ fontSize: 12, color: 'var(--txt3)', marginTop: 4 }}>
            {shipment.product_name} · {fmt.kg(shipment.weight_kg)} · {shipment.origin_country} → {shipment.destination_country}
          </div>
        </div>
        <div className="page-actions">
          {nextStatus && (
            <button className="btn btn-primary" onClick={() => setConfirmOpen(true)} disabled={advancing}>
              {advancing ? <span className="spinner" style={{ width: 13, height: 13 }} /> : `→ ${SHIPMENT_STATUS[nextStatus]?.label}`}
            </button>
          )}
          <button className="btn btn-secondary" onClick={() => navigate('/shipments')}>← Back</button>
        </div>
      </div>

      {/* Pipeline timeline */}
      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="timeline-wrap">
          <div className="timeline">
            {PIPELINE_STEPS.map((step, i) => (
              <div key={step.key} className="tl-step">
                <div className={`tl-dot ${i < currentIdx ? 'done' : i === currentIdx ? 'active' : ''}`} />
                <div className="tl-label">{step.label}</div>
              </div>
            ))}
          </div>
        </div>
        {nextStatus && (
          <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
            <input className="form-input" style={{ maxWidth: 320 }} placeholder="Optional note for this status change..." value={statusNote} onChange={(e) => setStatusNote(e.target.value)} />
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="tab-bar">
        {['overview', 'qc', 'customs', 'transactions', 'documents', 'history'].map((t) => (
          <div key={t} className={`tab-item ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
            {t === 'customs' && shipment.customs_records?.some((c) => c.status === 'hold') && (
              <span className="pill pill-red" style={{ marginLeft: 6, fontSize: 9 }}>Hold</span>
            )}
          </div>
        ))}
      </div>

      {/* Overview tab */}
      {tab === 'overview' && (
        <div className="grid-2">
          <div className="panel">
            <div className="panel-title" style={{ marginBottom: 12 }}>Shipment Details</div>
            {[
              ['Product', `${shipment.product_name}${shipment.product_variety ? ' — ' + shipment.product_variety : ''}`],
              ['HS Code', shipment.hs_code || '—'],
              ['Weight', fmt.kg(shipment.weight_kg)],
              ['Declared Value', fmt.usd(shipment.declared_value_usd)],
              ['Origin', `${shipment.origin_country}${shipment.origin_city ? ', ' + shipment.origin_city : ''}`],
              ['Destination', `${shipment.destination_country}${shipment.destination_city ? ', ' + shipment.destination_city : ''}`],
              ['Supplier', shipment.supplier_name || '—'],
              ['Buyer', shipment.buyer_name || '—'],
              ['Transport', shipment.transport_mode?.replace(/_/g, ' ')],
              ['Carrier', shipment.carrier_name || '—'],
              ['Tracking #', shipment.tracking_number || '—'],
              ['Storage Bay', shipment.storage_bay || '—'],
              ['Departure', fmt.date(shipment.departure_date)],
              ['Expected Arrival', fmt.date(shipment.expected_arrival)],
              ['Actual Arrival', fmt.date(shipment.actual_arrival)],
              ['Created', fmt.datetime(shipment.created_at)],
            ].map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--surface2)', fontSize: 12 }}>
                <span style={{ color: 'var(--txt3)' }}>{k}</span>
                <span style={{ textAlign: 'right', maxWidth: '55%' }}>{v}</span>
              </div>
            ))}
          </div>
          <div>
            {latestQC && (
              <div className="panel" style={{ marginBottom: 14 }}>
                <div className="panel-title" style={{ marginBottom: 10 }}>Latest QC Summary</div>
                <div className="kpi-grid kpi-grid-3">
                  <div className="kpi-card" style={{ padding: '10px 12px' }}>
                    <div className="kpi-label">Grade A</div>
                    <div className="kpi-value" style={{ fontSize: 20, color: 'var(--grn)' }}>{gradeAPct}%</div>
                  </div>
                  <div className="kpi-card" style={{ padding: '10px 12px' }}>
                    <div className="kpi-label">Grade B</div>
                    <div className="kpi-value" style={{ fontSize: 20, color: 'var(--amb)' }}>{((latestQC.grade_b_kg / totalWeight) * 100).toFixed(1)}%</div>
                  </div>
                  <div className="kpi-card" style={{ padding: '10px 12px' }}>
                    <div className="kpi-label">Rejected</div>
                    <div className="kpi-value" style={{ fontSize: 20, color: 'var(--red)' }}>{((latestQC.rejected_kg / totalWeight) * 100).toFixed(1)}%</div>
                  </div>
                </div>
              </div>
            )}
            {shipment.notes && (
              <div className="panel">
                <div className="panel-title" style={{ marginBottom: 8 }}>Notes</div>
                <div style={{ fontSize: 12, color: 'var(--txt2)', lineHeight: 1.6 }}>{shipment.notes}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* QC Tab */}
      {tab === 'qc' && (
        <div className="grid-2">
          <div className="panel">
            <div className="section-title">Log QC Inspection</div>
            <form onSubmit={saveQC} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="form-row">
                <div className="form-group"><label className="form-label">Lot Number</label>
                  <input className="form-input" required value={qcForm.lot_number} onChange={(e) => setQcForm((f) => ({ ...f, lot_number: e.target.value }))} /></div>
                <div className="form-group"><label className="form-label">Inspector</label>
                  <input className="form-input" required value={qcForm.inspector_name} onChange={(e) => setQcForm((f) => ({ ...f, inspector_name: e.target.value }))} /></div>
              </div>
              <div className="form-row-3">
                <div className="form-group"><label className="form-label">Grade A (kg)</label>
                  <input className="form-input" type="number" step="0.1" value={qcForm.grade_a_kg} onChange={(e) => setQcForm((f) => ({ ...f, grade_a_kg: e.target.value }))} /></div>
                <div className="form-group"><label className="form-label">Grade B (kg)</label>
                  <input className="form-input" type="number" step="0.1" value={qcForm.grade_b_kg} onChange={(e) => setQcForm((f) => ({ ...f, grade_b_kg: e.target.value }))} /></div>
                <div className="form-group"><label className="form-label">Rejected (kg)</label>
                  <input className="form-input" type="number" step="0.1" value={qcForm.rejected_kg} onChange={(e) => setQcForm((f) => ({ ...f, rejected_kg: e.target.value }))} /></div>
              </div>
              <div className="form-row">
                <div className="form-group"><label className="form-label">Packaging Type</label>
                  <select className="form-select" value={qcForm.packaging_type} onChange={(e) => setQcForm((f) => ({ ...f, packaging_type: e.target.value }))}>
                    <option>5kg export cartons</option><option>10kg bulk crates</option>
                    <option>1kg consumer packs</option><option>Loose bulk</option>
                  </select></div>
                <div className="form-group"><label className="form-label">Pallets</label>
                  <input className="form-input" type="number" value={qcForm.pallets_count} onChange={(e) => setQcForm((f) => ({ ...f, pallets_count: e.target.value }))} /></div>
              </div>
              <div className="form-group"><label className="form-label">Notes</label>
                <textarea className="form-textarea" rows={2} value={qcForm.notes} onChange={(e) => setQcForm((f) => ({ ...f, notes: e.target.value }))} /></div>
              <button className="btn btn-primary" type="submit" disabled={savingQc}>
                {savingQc ? 'Saving...' : 'Save QC Record'}
              </button>
            </form>
          </div>
          <div className="panel">
            <div className="section-title">QC History</div>
            {shipment.qc_records?.length === 0 ? (
              <div className="empty-state"><div className="empty-state-text">No QC records yet</div></div>
            ) : shipment.qc_records?.map((q) => (
              <div key={q.id} style={{ padding: '12px 0', borderBottom: '1px solid var(--surface2)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: 12, fontWeight: 500 }}>{q.lot_number}</span>
                  <span className="txt-small txt-muted">{fmt.date(q.inspection_date)} — {q.inspector_name}</span>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <span className="pill pill-grn">A: {fmt.kg(q.grade_a_kg)}</span>
                  <span className="pill pill-amb">B: {fmt.kg(q.grade_b_kg)}</span>
                  <span className="pill pill-red">Rej: {fmt.kg(q.rejected_kg)}</span>
                  {q.cold_chain_maintained ? <span className="pill pill-grn">✓ Cold chain</span> : <span className="pill pill-red">⚠ Chain break</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Customs Tab */}
      {tab === 'customs' && (
        <div className="panel">
          <div className="section-title">Customs Records</div>
          {shipment.customs_records?.length === 0 ? (
            <div className="empty-state"><div className="empty-state-text">No customs records yet</div></div>
          ) : shipment.customs_records?.map((c) => {
            const cs = CUSTOMS_STATUS[c.status] || { label: c.status, pill: 'pill-grey' }
            return (
              <div key={c.id} style={{ padding: '14px 0', borderBottom: '1px solid var(--surface2)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                      <span style={{ fontSize: 12, fontWeight: 500, textTransform: 'capitalize' }}>{c.direction} Customs</span>
                      <span className={`pill ${cs.pill}`}>{cs.label}</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--txt3)' }}>
                      {c.border_point && <span>📍 {c.border_point} · </span>}
                      {c.declaration_ref && <span>Ref: {c.declaration_ref} · </span>}
                      Duty: {fmt.usd(c.duty_amount_usd)} · VAT: {fmt.usd(c.vat_amount_usd)}
                    </div>
                    {c.hold_reason && (
                      <div style={{ marginTop: 6, fontSize: 12, color: 'var(--red)', background: 'var(--red-l)', padding: '6px 10px', borderRadius: 3 }}>
                        ⚠ Hold reason: {c.hold_reason}
                      </div>
                    )}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--txt3)', textAlign: 'right' }}>
                    {c.submitted_at && <div>Submitted: {fmt.datetime(c.submitted_at)}</div>}
                    {c.cleared_at && <div style={{ color: 'var(--grn)' }}>Cleared: {fmt.datetime(c.cleared_at)}</div>}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Transactions Tab */}
      {tab === 'transactions' && (
        <div className="panel">
          <div className="section-title">Linked Transactions</div>
          {shipment.transactions?.length === 0 ? (
            <div className="empty-state"><div className="empty-state-text">No transactions linked</div></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Ref</th><th>Type</th><th>Description</th><th>Amount</th><th>Counterparty</th><th>Status</th><th>Date</th></tr></thead>
              <tbody>
                {shipment.transactions?.map((t) => (
                  <tr key={t.id}>
                    <td className="mono">{t.ref}</td>
                    <td>{t.transaction_type?.replace(/_/g, ' ')}</td>
                    <td>{t.description}</td>
                    <td style={{ color: t.amount_usd > 0 ? 'var(--grn)' : 'var(--red)', fontFamily: 'var(--font-mono)' }}>
                      {t.amount_usd > 0 ? '+' : ''}{fmt.usd(t.amount_usd)}
                    </td>
                    <td>{t.counterparty || '—'}</td>
                    <td><span className={`pill ${t.status === 'paid' ? 'pill-grn' : t.status === 'overdue' ? 'pill-red' : 'pill-amb'}`}>{t.status}</span></td>
                    <td className="mono txt-small">{fmt.date(t.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* History Tab */}
      {tab === 'history' && (
        <div className="panel">
          <div className="section-title">Status Change History</div>
          {shipment.status_history?.map((h, i) => (
            <div key={i} className="activity-item">
              <div className="activity-dot" style={{ background: 'var(--grn-t)' }} />
              <div>
                <div className="activity-text">
                  {h.from_status ? <>{h.from_status} → </> : 'Created → '}<strong>{h.to_status}</strong>
                </div>
                {h.note && <div style={{ fontSize: 11, color: 'var(--txt2)', marginTop: 2 }}>{h.note}</div>}
                <div className="activity-time">{fmt.datetime(h.changed_at)}</div>
              </div>
            </div>
          ))}
        </div>
      )}


      {/* Documents Tab */}
      {tab === 'documents' && (
        <div className="panel">
          <div className="section-title">Documents</div>
          <div style={{ marginBottom: 16, display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div className="form-group" style={{ flex: 1, minWidth: 180 }}>
              <label className="form-label">Document Type</label>
              <select className="form-select" value={uploadType} onChange={(e) => setUploadType(e.target.value)}>
                {['Commercial Invoice','Bill of Lading','Packing List','Certificate of Origin',
                  'Phytosanitary Certificate','Pesticide Residue Report','Customs Declaration',
                  'Insurance Certificate','Quality Certificate','Other'].map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ flex: 2, minWidth: 200 }}>
              <label className="form-label">Choose File (PDF, image, Word, Excel — max 20 MB)</label>
              <input
                className="form-input"
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx,.xls,.xlsx,.csv,.txt"
                disabled={uploading}
                onChange={async (e) => {
                  const file = e.target.files[0]
                  if (!file) return
                  setUploading(true)
                  try {
                    await documentsApi.upload(id, uploadType, file)
                    push('success', `${uploadType} uploaded`)
                    const r = await documentsApi.list(id)
                    setDocuments(r.data)
                  } catch {
                    push('error', 'Upload failed — check file size and type')
                  } finally {
                    setUploading(false)
                    e.target.value = ''
                  }
                }}
              />
            </div>
            {uploading && <span className="spinner" style={{ width: 18, height: 18 }} />}
          </div>

          {documents.length === 0 ? (
            <div className="empty-state"><div className="empty-state-icon">📄</div><div className="empty-state-text">No documents uploaded yet</div></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Type</th><th>Filename</th><th>Uploaded</th><th>Action</th></tr></thead>
              <tbody>
                {documents.map((d) => (
                  <tr key={d.id}>
                    <td><span className="pill pill-blu" style={{ fontSize: 10 }}>{d.doc_type}</span></td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{d.filename}</td>
                    <td className="mono txt-small">{fmt.datetime(d.uploaded_at)}</td>
                    <td style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-sm btn-secondary" onClick={async () => {
                        try {
                          const r = await documentsApi.download(id, d.id)
                          const url = URL.createObjectURL(r.data)
                          const a = document.createElement('a')
                          a.href = url; a.download = d.filename; a.click()
                          URL.revokeObjectURL(url)
                        } catch { push('error', 'Download failed') }
                      }}>↓ Download</button>
                      <button className="btn btn-sm btn-danger" onClick={async () => {
                        if (!confirm(`Delete "${d.filename}"?`)) return
                        try {
                          await documentsApi.delete(id, d.id)
                          setDocuments((prev) => prev.filter((x) => x.id !== d.id))
                          push('success', 'Document deleted')
                        } catch { push('error', 'Delete failed') }
                      }}>✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ── Status Advance Confirmation Modal ───────────────────────────── */}
      {confirmOpen && nextStatus && (
        <div className="modal-overlay" onClick={() => setConfirmOpen(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-hd">
              <div className="modal-title">Confirm Status Change</div>
              <button className="modal-close" onClick={() => setConfirmOpen(false)}>×</button>
            </div>
            <div style={{ fontSize: 13, color: 'var(--txt2)', marginBottom: 16 }}>
              You are about to advance <strong>{shipment.shipment_ref}</strong> from{' '}
              <span className={`pill ${SHIPMENT_STATUS[shipment.status]?.pill}`}>
                {SHIPMENT_STATUS[shipment.status]?.label}
              </span>{' '}to{' '}
              <span className={`pill ${SHIPMENT_STATUS[nextStatus]?.pill}`}>
                {SHIPMENT_STATUS[nextStatus]?.label}
              </span>.
              <br /><br />This action is logged and cannot be undone.
            </div>
            <div className="form-group" style={{ marginBottom: 16 }}>
              <label className="form-label">Note (optional)</label>
              <input
                className="form-input"
                placeholder="Add a note about this transition..."
                value={statusNote}
                onChange={(e) => setStatusNote(e.target.value)}
                autoFocus
              />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary" onClick={advanceStatus} disabled={advancing}>
                {advancing ? 'Saving...' : `Confirm → ${SHIPMENT_STATUS[nextStatus]?.label}`}
              </button>
              <button className="btn btn-secondary" onClick={() => setConfirmOpen(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
