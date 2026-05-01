import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { shipmentsApi } from '../utils/api'
import { fmt, SHIPMENT_STATUS, COUNTRIES, PRODUCTS } from '../utils/helpers'
import { useNotifyStore } from '../store/store'

// ─── Shipments List ───────────────────────────────────────────────────────────
export function ShipmentsPage() {
  const [shipments, setShipments] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ status: '', product: '', origin: '', destination: '' })
  const [searchInput, setSearchInput] = useState('')
  const navigate = useNavigate()

  const load = () => {
    setLoading(true)
    const params = {}
    if (filters.status) params.status = filters.status
    if (filters.product) params.product = filters.product
    if (filters.origin) params.origin = filters.origin
    if (filters.destination) params.destination = filters.destination
    shipmentsApi.list(params).then((r) => setShipments(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filters])

  // Debounce the text search field
  useEffect(() => {
    const t = setTimeout(() => setFilters((f) => ({ ...f, product: searchInput })), 350)
    return () => clearTimeout(t)
  }, [searchInput])

  return (
    <div>
      <div className="page-header">
        <h1>All Shipments</h1>
        <div className="page-actions" style={{ flexWrap: 'wrap', gap: 8 }}>
          <input
            className="form-input"
            style={{ width: 160 }}
            placeholder="Search product..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <select className="form-select" style={{ width: 150 }} value={filters.status} onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}>
            <option value="">All Statuses</option>
            {Object.entries(SHIPMENT_STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
          <select className="form-select" style={{ width: 130 }} value={filters.origin} onChange={(e) => setFilters((f) => ({ ...f, origin: e.target.value }))}>
            <option value="">All Origins</option>
            {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
          </select>
          <select className="form-select" style={{ width: 140 }} value={filters.destination} onChange={(e) => setFilters((f) => ({ ...f, destination: e.target.value }))}>
            <option value="">All Destinations</option>
            {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
          </select>
          {(filters.status || filters.origin || filters.destination || searchInput) && (
            <button className="btn btn-secondary btn-sm" onClick={() => { setFilters({ status: '', product: '', origin: '', destination: '' }); setSearchInput('') }}>
              Clear ×
            </button>
          )}
          <button className="btn btn-primary" onClick={() => navigate('/shipments/new')}>+ New Shipment</button>
        </div>
      </div>

      <div className="panel">
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><span className="spinner" /></div>
        ) : (
          <div className="scrollable-x">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Ref</th><th>Type</th><th>Product</th><th>Weight</th>
                  <th>Route</th><th>Supplier / Buyer</th><th>Status</th>
                  <th>Value</th><th>ETA</th>
                </tr>
              </thead>
              <tbody>
                {shipments.map((s) => {
                  const st = SHIPMENT_STATUS[s.status] || { label: s.status, pill: 'pill-grey' }
                  return (
                    <tr key={s.id} onClick={() => navigate(`/shipments/${s.id}`)} style={{ cursor: 'pointer' }}>
                      <td><span style={{ color: 'var(--blu-t)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>{s.shipment_ref}</span></td>
                      <td><span className={`pill ${s.shipment_type === 'import' ? 'pill-blu' : 'pill-grn'}`}>{s.shipment_type}</span></td>
                      <td>{s.product_name}</td>
                      <td className="mono">{fmt.kg(s.weight_kg)}</td>
                      <td className="mono" style={{ whiteSpace: 'nowrap' }}>{s.origin_country} → {s.destination_country}</td>
                      <td style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.buyer_name || s.supplier_name || '—'}</td>
                      <td><span className={`pill ${st.pill}`}>{st.label}</span></td>
                      <td className="mono">{fmt.usd(s.declared_value_usd)}</td>
                      <td className="mono txt-small">{fmt.date(s.expected_arrival)}</td>
                    </tr>
                  )
                })}
                {shipments.length === 0 && (
                  <tr><td colSpan={9} style={{ textAlign: 'center', padding: 30, color: 'var(--txt3)' }}>No shipments found</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── New Shipment Form ────────────────────────────────────────────────────────
export function NewShipmentPage() {
  const navigate = useNavigate()
  const { push } = useNotifyStore()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    shipment_type: 'import', product_name: 'Tomatoes',
    product_variety: '', hs_code: '', weight_kg: '',
    declared_value_usd: '', origin_country: 'Turkey',
    origin_city: '', destination_country: 'Azerbaijan',
    destination_city: '', supplier_name: '', buyer_name: '',
    transport_mode: 'truck_refrigerated', carrier_name: '',
    tracking_number: '', storage_bay: '', departure_date: '',
    expected_arrival: '', notes: '',
  })

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const payload = { ...form }
      if (!payload.weight_kg || isNaN(payload.weight_kg)) { push('error', 'Weight is required'); setLoading(false); return }
      payload.weight_kg = parseFloat(payload.weight_kg)
      payload.declared_value_usd = parseFloat(payload.declared_value_usd) || 0
      if (!payload.departure_date) delete payload.departure_date
      if (!payload.expected_arrival) delete payload.expected_arrival
      Object.keys(payload).forEach((k) => { if (payload[k] === '') delete payload[k] })
      const res = await shipmentsApi.create(payload)
      push('success', `Shipment ${res.data.shipment_ref} created`)
      navigate(`/shipments/${res.data.id}`)
    } catch (err) {
      push('error', err.response?.data?.detail || 'Failed to create shipment')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>New Trade Entry</h1>
        <button className="btn btn-secondary" onClick={() => navigate('/shipments')}>← Back</button>
      </div>
      <div className="panel">
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Shipment Type</label>
              <select className="form-select" value={form.shipment_type} onChange={(e) => set('shipment_type', e.target.value)}>
                <option value="import">Import</option><option value="export">Export</option>
                <option value="transit">Transit</option><option value="internal">Internal</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Product</label>
              <select className="form-select" value={form.product_name} onChange={(e) => set('product_name', e.target.value)}>
                {PRODUCTS.map((p) => <option key={p}>{p}</option>)}
              </select>
            </div>
          </div>

          <div className="form-row-3">
            <div className="form-group">
              <label className="form-label">Weight (kg) *</label>
              <input className="form-input" type="number" min="1" value={form.weight_kg} onChange={(e) => set('weight_kg', e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">Declared Value (USD)</label>
              <input className="form-input" type="number" min="0" step="0.01" value={form.declared_value_usd} onChange={(e) => set('declared_value_usd', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">HS Code</label>
              <input className="form-input" placeholder="e.g. 0702 00 00" value={form.hs_code} onChange={(e) => set('hs_code', e.target.value)} />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Origin Country</label>
              <select className="form-select" value={form.origin_country} onChange={(e) => set('origin_country', e.target.value)}>
                {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Destination Country</label>
              <select className="form-select" value={form.destination_country} onChange={(e) => set('destination_country', e.target.value)}>
                {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Supplier Name</label>
              <input className="form-input" value={form.supplier_name} onChange={(e) => set('supplier_name', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Buyer Name</label>
              <input className="form-input" value={form.buyer_name} onChange={(e) => set('buyer_name', e.target.value)} />
            </div>
          </div>

          <div className="form-row-3">
            <div className="form-group">
              <label className="form-label">Transport Mode</label>
              <select className="form-select" value={form.transport_mode} onChange={(e) => set('transport_mode', e.target.value)}>
                <option value="truck_refrigerated">Refrigerated Truck</option>
                <option value="air_freight">Air Freight</option>
                <option value="sea_container">Sea Container</option>
                <option value="rail_reefer">Rail (Reefer)</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Departure Date</label>
              <input className="form-input" type="date" value={form.departure_date} onChange={(e) => set('departure_date', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Expected Arrival</label>
              <input className="form-input" type="date" value={form.expected_arrival} onChange={(e) => set('expected_arrival', e.target.value)} />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Storage Bay</label>
              <select className="form-select" value={form.storage_bay} onChange={(e) => set('storage_bay', e.target.value)}>
                <option value="">— Assign later —</option>
                <option>A-01 (Cold, 0–4°C)</option><option>A-02 (Cold, 0–4°C)</option>
                <option>A-03 (Cold, 2–6°C)</option><option>B-01 (Ambient)</option>
                <option>B-02 (Ambient)</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Carrier Name</label>
              <input className="form-input" value={form.carrier_name} onChange={(e) => set('carrier_name', e.target.value)} />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Notes / Special Handling</label>
            <textarea className="form-textarea" rows={2} value={form.notes} onChange={(e) => set('notes', e.target.value)} style={{ resize: 'vertical' }} />
          </div>

          <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : 'Create Shipment & Generate Ref'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/shipments')}>Cancel</button>
          </div>
        </form>
      </div>
    </div>
  )
}
