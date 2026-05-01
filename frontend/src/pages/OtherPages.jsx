import { useEffect, useState } from 'react'
import { customsApi, transactionsApi, analyticsApi, shipmentsApi, documentsApi, storageApi } from '../utils/api'
import { fmt, CUSTOMS_STATUS, TXN_STATUS, TXN_TYPE } from '../utils/helpers'
import { useNotifyStore } from '../store/store'

// ── CSV Export utility ────────────────────────────────────────────────────────
function exportCSV(rows, filename) {
  if (!rows.length) return
  const headers = Object.keys(rows[0])
  const csv = [
    headers.join(','),
    ...rows.map((r) => headers.map((h) => `"${String(r[h] ?? '').replace(/"/g, '""')}"`).join(',')),
  ].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

// ─── Customs Page ─────────────────────────────────────────────────────────────
export function CustomsPage() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const { push } = useNotifyStore()

  const REQUIRED_DOCS = [
    'Commercial Invoice', 'Bill of Lading', 'Packing List',
    'Certificate of Origin', 'Phytosanitary Certificate',
    'Pesticide Residue Report', 'Customs Declaration',
  ]

  useEffect(() => {
    customsApi.list(filter ? { status: filter } : {}).then((r) => setRecords(r.data)).finally(() => setLoading(false))
  }, [filter])

  const updateStatus = async (id, status) => {
    try {
      await customsApi.updateStatus(id, { status })
      push('success', `Customs status → ${CUSTOMS_STATUS[status]?.label}`)
      setLoading(true)
      customsApi.list(filter ? { status: filter } : {}).then((r) => setRecords(r.data)).finally(() => setLoading(false))
    } catch { push('error', 'Failed to update status') }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Customs Clearance</h1>
        <select className="form-select" style={{ width: 160 }} value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All Statuses</option>
          {Object.entries(CUSTOMS_STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
      </div>

      <div className="grid-2">
        <div className="panel">
          <div className="section-title">Clearance Queue</div>
          {loading ? <div style={{ textAlign: 'center', padding: 30 }}><span className="spinner" /></div>
            : records.length === 0 ? <div className="empty-state"><div className="empty-state-text">No records</div></div>
            : records.map((c) => {
              const cs = CUSTOMS_STATUS[c.status] || { label: c.status, pill: 'pill-grey' }
              return (
                <div key={c.id} style={{ padding: '14px 0', borderBottom: '1px solid var(--surface2)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', gap: 8, marginBottom: 5, alignItems: 'center' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--blu-t)' }}>Shipment #{c.shipment_id}</span>
                        <span className="pill pill-grey">{c.direction}</span>
                        <span className={`pill ${cs.pill}`}>{cs.label}</span>
                      </div>
                      {c.border_point && <div style={{ fontSize: 11, color: 'var(--txt3)', marginBottom: 4 }}>📍 {c.border_point}</div>}
                      {c.declaration_ref && <div style={{ fontSize: 11, color: 'var(--txt3)' }}>Decl: {c.declaration_ref}</div>}
                      <div style={{ fontSize: 11, color: 'var(--txt3)', marginTop: 4 }}>
                        Duty: {fmt.usd(c.duty_amount_usd)} · VAT: {fmt.usd(c.vat_amount_usd)} · Other: {fmt.usd(c.other_fees_usd)}
                      </div>
                      {c.hold_reason && (
                        <div style={{ marginTop: 6, fontSize: 11, color: 'var(--red)', background: 'var(--red-l)', padding: '5px 8px', borderRadius: 3 }}>
                          ⚠ {c.hold_reason}
                        </div>
                      )}
                      <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {c.status !== 'cleared' && c.status !== 'rejected' && (
                          <>
                            {c.status === 'not_started' && <button className="btn btn-sm btn-secondary" onClick={() => updateStatus(c.id, 'submitted')}>Mark Submitted</button>}
                            {c.status === 'submitted' && <button className="btn btn-sm btn-secondary" onClick={() => updateStatus(c.id, 'processing')}>Mark Processing</button>}
                            {c.status === 'processing' && <button className="btn btn-sm btn-primary" onClick={() => updateStatus(c.id, 'cleared')}>Mark Cleared ✓</button>}
                            {c.status !== 'hold' && <button className="btn btn-sm btn-danger" onClick={() => updateStatus(c.id, 'hold')}>Place on Hold</button>}
                            {c.status === 'hold' && <button className="btn btn-sm btn-primary" onClick={() => updateStatus(c.id, 'cleared')}>Resolve & Clear</button>}
                          </>
                        )}
                      </div>
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--txt3)', textAlign: 'right', flexShrink: 0 }}>
                      {c.submitted_at && <div>Submitted {fmt.relativeDate(c.submitted_at)}</div>}
                      {c.cleared_at && <div style={{ color: 'var(--grn)' }}>Cleared {fmt.date(c.cleared_at)}</div>}
                    </div>
                  </div>
                </div>
              )
            })
          }
        </div>

        <div className="panel">
          <div className="section-title">Document Checklist</div>
          <div style={{ fontSize: 11, color: 'var(--txt3)', marginBottom: 12 }}>
            Required documents for standard fresh produce import — verify against each customs record.
          </div>
          {REQUIRED_DOCS.map((doc, i) => {
            const isUploaded = i < 4  // mock: first 4 uploaded
            const isMissing = i === 4 || i === 5
            return (
              <div key={doc} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 10px', borderRadius: 3, marginBottom: 5,
                background: isMissing ? 'var(--red-l)' : isUploaded ? 'var(--grn-l)' : 'var(--surface2)',
                border: `1px solid ${isMissing ? '#fca5a5' : isUploaded ? 'var(--grn-t)' : 'var(--border)'}`,
              }}>
                <span style={{ color: isMissing ? 'var(--red)' : isUploaded ? 'var(--grn)' : 'var(--txt3)', fontWeight: 600 }}>
                  {isMissing ? '✗' : isUploaded ? '✓' : '○'}
                </span>
                <span style={{ fontSize: 12, color: isMissing ? 'var(--red)' : isUploaded ? 'var(--grn)' : 'var(--txt2)', fontWeight: isMissing ? 500 : 400 }}>
                  {doc}
                </span>
                <span style={{ marginLeft: 'auto', fontSize: 10, color: isMissing ? 'var(--red)' : isUploaded ? 'var(--grn)' : 'var(--txt3)' }}>
                  {isMissing ? 'MISSING' : isUploaded ? 'Uploaded' : '—'}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ─── Transactions Page ────────────────────────────────────────────────────────
export function TransactionsPage() {
  const [txns, setTxns] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState('')
  const [showNew, setShowNew] = useState(false)
  const { push } = useNotifyStore()

  const [form, setForm] = useState({ transaction_type: 'revenue', description: '', amount_usd: '', counterparty: '', due_date: '', invoice_ref: '', notes: '' })
  const [saving, setSaving] = useState(false)

  const load = () => {
    const p = {}; if (filterType) p.txn_type = filterType
    transactionsApi.list(p).then((r) => setTxns(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filterType])

  const save = async (e) => {
    e.preventDefault(); setSaving(true)
    try {
      const p = { ...form, amount_usd: parseFloat(form.amount_usd) }
      if (!p.due_date) delete p.due_date
      await transactionsApi.create(p)
      push('success', 'Transaction recorded')
      setShowNew(false)
      setForm({ transaction_type: 'revenue', description: '', amount_usd: '', counterparty: '', due_date: '', invoice_ref: '', notes: '' })
      load()
    } catch { push('error', 'Failed to save transaction') }
    finally { setSaving(false) }
  }

  const revenue = txns.filter((t) => t.amount_usd > 0).reduce((s, t) => s + t.amount_usd, 0)
  const costs = txns.filter((t) => t.amount_usd < 0).reduce((s, t) => s + Math.abs(t.amount_usd), 0)

  return (
    <div>
      <div className="page-header">
        <h1>Transactions</h1>
        <div className="page-actions">
          <select className="form-select" style={{ width: 160 }} value={filterType} onChange={(e) => setFilterType(e.target.value)}>
            <option value="">All Types</option>
            {Object.entries(TXN_TYPE).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
          <button className="btn btn-secondary" onClick={() => exportCSV(
            txns.map((t) => ({ ref: t.ref, date: fmt.date(t.created_at), type: t.transaction_type, description: t.description, amount_usd: t.amount_usd, counterparty: t.counterparty || '', status: t.status })),
            `transactions-${new Date().toISOString().slice(0,10)}.csv`
          )}>↓ CSV</button>
          <button className="btn btn-primary" onClick={() => setShowNew(!showNew)}>+ Record Transaction</button>
        </div>
      </div>

      {/* Summary bar */}
      <div className="kpi-grid kpi-grid-3" style={{ marginBottom: 16 }}>
        <div className="kpi-card"><div className="kpi-label">Revenue (shown)</div><div className="kpi-value txt-green">{fmt.usd(revenue)}</div></div>
        <div className="kpi-card"><div className="kpi-label">Costs (shown)</div><div className="kpi-value" style={{ color: 'var(--red)' }}>{fmt.usd(costs)}</div></div>
        <div className="kpi-card"><div className="kpi-label">Net</div><div className="kpi-value" style={{ color: (revenue - costs) >= 0 ? 'var(--grn)' : 'var(--red)' }}>{fmt.usd(revenue - costs)}</div></div>
      </div>

      {/* New transaction form */}
      {showNew && (
        <div className="panel" style={{ marginBottom: 16 }}>
          <div className="section-title">Record New Transaction</div>
          <form onSubmit={save} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="form-row">
              <div className="form-group"><label className="form-label">Type</label>
                <select className="form-select" value={form.transaction_type} onChange={(e) => setForm((f) => ({ ...f, transaction_type: e.target.value }))}>
                  {Object.entries(TXN_TYPE).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                </select></div>
              <div className="form-group"><label className="form-label">Amount (USD) — use negative for costs</label>
                <input className="form-input" type="number" step="0.01" required value={form.amount_usd} onChange={(e) => setForm((f) => ({ ...f, amount_usd: e.target.value }))} /></div>
            </div>
            <div className="form-row">
              <div className="form-group"><label className="form-label">Description</label>
                <input className="form-input" required value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} /></div>
              <div className="form-group"><label className="form-label">Counterparty</label>
                <input className="form-input" value={form.counterparty} onChange={(e) => setForm((f) => ({ ...f, counterparty: e.target.value }))} /></div>
            </div>
            <div className="form-row">
              <div className="form-group"><label className="form-label">Invoice Ref</label>
                <input className="form-input" value={form.invoice_ref} onChange={(e) => setForm((f) => ({ ...f, invoice_ref: e.target.value }))} /></div>
              <div className="form-group"><label className="form-label">Due Date</label>
                <input className="form-input" type="date" value={form.due_date} onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))} /></div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving...' : 'Save Transaction'}</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowNew(false)}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div className="panel">
        {loading ? <div style={{ textAlign: 'center', padding: 30 }}><span className="spinner" /></div>
          : (
          <div className="scrollable-x">
            <table className="data-table">
              <thead><tr><th>Date</th><th>Ref</th><th>Description</th><th>Type</th><th>Amount</th><th>Counterparty</th><th>Status</th></tr></thead>
              <tbody>
                {txns.map((t) => {
                  const st = TXN_STATUS[t.status] || { label: t.status, pill: 'pill-grey' }
                  return (
                    <tr key={t.id}>
                      <td className="mono txt-small">{fmt.date(t.created_at)}</td>
                      <td className="mono">{t.ref}</td>
                      <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.description}</td>
                      <td><span className="pill pill-grey" style={{ fontSize: 10 }}>{t.transaction_type?.replace(/_/g, ' ')}</span></td>
                      <td style={{ color: t.amount_usd > 0 ? 'var(--grn)' : 'var(--red)', fontFamily: 'var(--font-mono)' }}>
                        {t.amount_usd > 0 ? '+' : ''}{fmt.usd(t.amount_usd)}
                      </td>
                      <td>{t.counterparty || '—'}</td>
                      <td><span className={`pill ${st.pill}`}>{st.label}</span></td>
                    </tr>
                  )
                })}
                {txns.length === 0 && <tr><td colSpan={7} style={{ textAlign: 'center', padding: 30, color: 'var(--txt3)' }}>No transactions</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Reports Page ─────────────────────────────────────────────────────────────
export function ReportsPage() {
  const [period, setPeriod] = useState('monthly')
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    analyticsApi.report(period).then((r) => setReport(r.data)).finally(() => setLoading(false))
  }, [period])

  const periods = ['daily', 'weekly', 'monthly', 'quarterly', 'annual']

  return (
    <div>
      <div className="page-header"><h1>Reports & Archive</h1></div>
      <div className="tab-bar">
        {periods.map((p) => (
          <div key={p} className={`tab-item ${period === p ? 'active' : ''}`} onClick={() => setPeriod(p)}>
            {p.charAt(0).toUpperCase() + p.slice(1)}
          </div>
        ))}
      </div>

      {loading ? <div style={{ textAlign: 'center', padding: 40 }}><span className="spinner" /></div>
        : report && (
        <div>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 22, fontWeight: 300, marginBottom: 4 }}>{report.label}</div>
            <div style={{ fontSize: 12, color: 'var(--txt3)' }}>Chronological archive · Auto-generated</div>
          </div>
          <div className="kpi-grid kpi-grid-4" style={{ marginBottom: 20 }}>
            <div className="kpi-card"><div className="kpi-label">Shipments</div><div className="kpi-value">{report.shipments_count}</div></div>
            <div className="kpi-card"><div className="kpi-label">Revenue</div><div className="kpi-value txt-green">{fmt.usd(report.revenue)}</div></div>
            <div className="kpi-card"><div className="kpi-label">Costs</div><div className="kpi-value" style={{ color: 'var(--red)' }}>{fmt.usd(report.costs)}</div></div>
            <div className="kpi-card">
              <div className="kpi-label">Net</div>
              <div className="kpi-value" style={{ color: report.net >= 0 ? 'var(--grn)' : 'var(--red)' }}>{fmt.usd(report.net)}</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 16 }}>
            <button className="btn btn-secondary" onClick={() => exportCSV([{
              period: report.period, label: report.label,
              shipments: report.shipments_count, revenue_usd: report.revenue,
              costs_usd: report.costs, net_usd: report.net,
              customs_clearances: report.customs_clearances,
              qc_inspections: report.qc_inspections, alerts: report.alerts_count,
            }], `report-${report.period}-${new Date().toISOString().slice(0,10)}.csv`)}>
              ↓ Export CSV
            </button>
          </div>
          <div className="grid-2">
            <div className="panel">
              <div className="section-title">Operations Summary</div>
              {[
                ['Customs clearances', report.customs_clearances],
                ['QC inspections run', report.qc_inspections],
                ['Active alerts', report.alerts_count],
                ['Net margin', report.revenue > 0 ? fmt.pct((report.net / report.revenue) * 100) : '—'],
              ].map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--surface2)', fontSize: 12 }}>
                  <span style={{ color: 'var(--txt3)' }}>{k}</span>
                  <span style={{ fontWeight: 500 }}>{v}</span>
                </div>
              ))}
            </div>
            <div className="panel">
              <div className="section-title">Cost Breakdown (Estimated)</div>
              {[
                { label: 'Procurement', pct: 61, color: 'var(--txt2)' },
                { label: 'Freight', pct: 13, color: 'var(--red-t)' },
                { label: 'Tax', pct: 10, color: 'var(--prp-t)' },
                { label: 'Customs', pct: 5, color: 'var(--amb-t)' },
                { label: 'Storage', pct: 2, color: 'var(--blu-t)' },
                { label: 'Packaging', pct: 2, color: 'var(--grn-t)' },
              ].map((r) => (
                <div key={r.label} className="bar-row">
                  <div className="bar-label">{r.label}</div>
                  <div className="bar-track"><div className="bar-fill" style={{ width: `${r.pct}%`, background: r.color }} /></div>
                  <div className="bar-val">{r.pct}%</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Analytics Page ───────────────────────────────────────────────────────────
export function AnalyticsPage() {
  const [kpi, setKpi] = useState(null)
  const [corridors, setCorridors] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([analyticsApi.dashboard(), analyticsApi.corridors()])
      .then(([k, c]) => { setKpi(k.data); setCorridors(c.data) })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}><span className="spinner" /></div>

  const maxCorrVal = Math.max(...corridors.map((c) => c.total_value_usd), 1)

  return (
    <div>
      <div className="page-header"><h1>Analytics</h1></div>
      <div className="kpi-grid kpi-grid-4" style={{ marginBottom: 20 }}>
        <div className="kpi-card"><div className="kpi-label">Active Shipments</div><div className="kpi-value">{kpi?.active_shipments}</div></div>
        <div className="kpi-card"><div className="kpi-label">Revenue MTD</div><div className="kpi-value txt-green">{fmt.usd(kpi?.revenue_mtd)}</div></div>
        <div className="kpi-card"><div className="kpi-label">Net Profit MTD</div><div className="kpi-value" style={{ color: (kpi?.net_profit_mtd || 0) >= 0 ? 'var(--grn)' : 'var(--red)' }}>{fmt.usd(kpi?.net_profit_mtd)}</div></div>
        <div className="kpi-card"><div className="kpi-label">Storage Capacity</div><div className="kpi-value">{fmt.pct(kpi?.storage_capacity_pct)}</div></div>
      </div>
      <div className="grid-2">
        <div className="panel">
          <div className="section-title">Trade Corridors — by Value</div>
          {corridors.map((c, i) => (
            <div key={i} className="bar-row">
              <div className="bar-label" style={{ width: 120, fontSize: 11 }}>{c.corridor.replace(' → ', '→')}</div>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${(c.total_value_usd / maxCorrVal) * 100}%`, background: ['var(--grn-t)', 'var(--grn-t)', 'var(--blu-t)', 'var(--amb-t)', 'var(--prp-t)'][i % 5] }} />
              </div>
              <div className="bar-val">{fmt.usd(c.total_value_usd)}</div>
            </div>
          ))}
        </div>
        <div className="panel">
          <div className="section-title">Corridor Volume (kg)</div>
          {corridors.map((c, i) => {
            const maxW = Math.max(...corridors.map((x) => x.total_weight_kg), 1)
            return (
              <div key={i} className="bar-row">
                <div className="bar-label" style={{ width: 120, fontSize: 11 }}>{c.corridor.replace(' → ', '→')}</div>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${(c.total_weight_kg / maxW) * 100}%`, background: 'var(--grn-t)' }} />
                </div>
                <div className="bar-val">{(c.total_weight_kg / 1000).toFixed(1)}t</div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ─── QC Page (standalone) ─────────────────────────────────────────────────────
export function QualityPage() {
  const [shipments, setShipments] = useState([])

  useEffect(() => {
    shipmentsApi.list({ status: 'qc_sorting', limit: 20 }).then((r) => setShipments(r.data))
  }, [])

  return (
    <div>
      <div className="page-header"><h1>QC / Sorting Queue</h1></div>
      <div className="panel">
        {shipments.length === 0
          ? <div className="empty-state"><div className="empty-state-icon">✓</div><div className="empty-state-text">No shipments in QC queue</div></div>
          : (
          <table className="data-table">
            <thead><tr><th>Ref</th><th>Product</th><th>Weight</th><th>Origin</th><th>Storage Bay</th><th>Action</th></tr></thead>
            <tbody>
              {shipments.map((s) => (
                <tr key={s.id}>
                  <td className="mono" style={{ color: 'var(--blu-t)' }}>{s.shipment_ref}</td>
                  <td>{s.product_name}</td>
                  <td className="mono">{fmt.kg(s.weight_kg)}</td>
                  <td>{s.origin_country}</td>
                  <td>{s.storage_bay || '—'}</td>
                  <td><a href={`/shipments/${s.id}?tab=qc`} style={{ color: 'var(--grn-t)', fontSize: 12 }}>Log QC →</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ─── Storage Bays Page ────────────────────────────────────────────────────────
export function StorageBaysPage() {
  const [bays, setBays] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    storageApi.bays().then((r) => setBays(r.data)).finally(() => setLoading(false))
  }, [])

  const maxCap = Math.max(...bays.map((b) => b.capacity_kg), 1)

  return (
    <div>
      <div className="page-header"><h1>Storage Bays — Live Status</h1></div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}><span className="spinner" /></div>
      ) : (
        <>
          <div className="kpi-grid kpi-grid-3" style={{ marginBottom: 20 }}>
            <div className="kpi-card">
              <div className="kpi-label">Total Bays</div>
              <div className="kpi-value">{bays.length}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Bays Near Capacity</div>
              <div className="kpi-value" style={{ color: bays.filter(b => b.alert).length ? 'var(--red)' : 'var(--grn)' }}>
                {bays.filter(b => b.alert).length}
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Total Available</div>
              <div className="kpi-value">{(bays.reduce((s, b) => s + b.available_kg, 0) / 1000).toFixed(0)}t</div>
            </div>
          </div>

          <div className="panel">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Bay</th><th>Type</th><th>Temp Range</th>
                  <th>Capacity</th><th>In Use</th><th>Available</th>
                  <th>Utilisation</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {bays.map((b) => (
                  <tr key={b.bay_code}>
                    <td style={{ fontWeight: 500 }}>{b.bay_code}</td>
                    <td><span className={`pill ${b.bay_type === 'cold' ? 'pill-blu' : 'pill-grey'}`}>{b.bay_type}</span></td>
                    <td className="mono">{b.temp_range}</td>
                    <td className="mono">{(b.capacity_kg / 1000).toFixed(0)}t</td>
                    <td className="mono">{(b.current_load_kg / 1000).toFixed(1)}t</td>
                    <td className="mono" style={{ color: 'var(--grn)' }}>{(b.available_kg / 1000).toFixed(1)}t</td>
                    <td style={{ minWidth: 140 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="bar-track" style={{ flex: 1 }}>
                          <div className="bar-fill" style={{
                            width: `${b.utilisation_pct}%`,
                            background: b.utilisation_pct >= 90 ? 'var(--red-t)' : b.utilisation_pct >= 70 ? 'var(--amb-t)' : 'var(--grn-t)'
                          }} />
                        </div>
                        <span className="mono txt-small">{b.utilisation_pct}%</span>
                      </div>
                    </td>
                    <td>
                      {b.alert
                        ? <span className="pill pill-red">⚠ Near full</span>
                        : <span className="pill pill-grn">Available</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
