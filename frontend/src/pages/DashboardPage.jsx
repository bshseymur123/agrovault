import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyticsApi, shipmentsApi, transactionsApi, customsApi } from '../utils/api'
import { fmt, SHIPMENT_STATUS, TXN_STATUS, CUSTOMS_STATUS } from '../utils/helpers'

function KpiCard({ label, value, delta, deltaType }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {delta && <div className={`kpi-delta delta-${deltaType || 'up'}`}>{delta}</div>}
    </div>
  )
}

function BarChart({ rows }) {
  const max = Math.max(...rows.map((r) => r.val), 1)
  return (
    <div>
      {rows.map((r) => (
        <div key={r.label} className="bar-row">
          <div className="bar-label">{r.label}</div>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(r.val / max) * 100}%`, background: r.color || 'var(--grn-t)' }} />
          </div>
          <div className="bar-val">{r.display}</div>
        </div>
      ))}
    </div>
  )
}

export default function DashboardPage() {
  const [kpi, setKpi] = useState(null)
  const [shipments, setShipments] = useState([])
  const [transactions, setTransactions] = useState([])
  const [customs, setCustoms] = useState([])
  const [corridors, setCorridors] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([
      analyticsApi.dashboard(),
      shipmentsApi.list({ limit: 8 }),
      transactionsApi.list({ limit: 6 }),
      customsApi.list({ status: 'hold' }),
      analyticsApi.corridors(),
    ]).then(([kpiRes, shRes, txRes, cusRes, corRes]) => {
      setKpi(kpiRes.data)
      setShipments(shRes.data)
      setTransactions(txRes.data)
      setCustoms(cusRes.data)
      setCorridors(corRes.data)
    }).finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300 }}>
      <span className="spinner" style={{ width: 28, height: 28 }} />
    </div>
  )

  const alerts = [
    ...customs.map((c) => ({ type: 'red', msg: `Customs hold — ${c.shipment_id}: ${c.hold_reason || 'Review required'}` })),
    ...transactions.filter((t) => t.status === 'overdue').map((t) => ({ type: 'amber', msg: `Invoice overdue — ${t.ref}: ${fmt.usd(t.amount_usd)} from ${t.counterparty}` })),
  ]

  return (
    <div>
      {/* KPI Row */}
      <div className="kpi-grid kpi-grid-4" style={{ marginBottom: 20 }}>
        <KpiCard label="Active Shipments" value={kpi?.active_shipments ?? '—'} delta={`${kpi?.total_weight_in_transit_kg?.toFixed(0)} kg in transit`} />
        <KpiCard label="Revenue MTD" value={fmt.usd(kpi?.revenue_mtd)} delta={`Net: ${fmt.usd(kpi?.net_profit_mtd)}`} />
        <KpiCard label="Pending Customs" value={kpi?.pending_customs ?? '—'} delta={customs.length ? `${customs.length} on hold` : 'All clear'} deltaType={customs.length ? 'dn' : 'up'} />
        <KpiCard label="Storage Capacity" value={fmt.pct(kpi?.storage_capacity_pct)} delta={kpi?.storage_capacity_pct > 80 ? 'Near limit' : 'Available'} deltaType={kpi?.storage_capacity_pct > 80 ? 'dn' : 'up'} />
      </div>

      <div className="grid-2" style={{ marginBottom: 16 }}>
        {/* Shipment pipeline */}
        <div className="panel">
          <div className="panel-hd">
            <div className="panel-title">Live Shipment Pipeline</div>
            <button className="btn btn-sm btn-secondary" onClick={() => navigate('/shipments')}>View all →</button>
          </div>
          <div className="scrollable" style={{ maxHeight: 280 }}>
            <table className="data-table">
              <thead>
                <tr><th>Ref</th><th>Product</th><th>Route</th><th>Status</th><th>ETA</th></tr>
              </thead>
              <tbody>
                {shipments.map((s) => {
                  const st = SHIPMENT_STATUS[s.status] || { label: s.status, pill: 'pill-grey' }
                  return (
                    <tr key={s.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/shipments/${s.id}`)}>
                      <td><span style={{ color: 'var(--blu-t)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>{s.shipment_ref}</span></td>
                      <td>{s.product_name} <span className="txt-muted txt-small">{fmt.kg(s.weight_kg)}</span></td>
                      <td className="mono">{s.origin_country} → {s.destination_country}</td>
                      <td><span className={`pill ${st.pill}`}>{st.label}</span></td>
                      <td className="mono txt-small">{fmt.date(s.expected_arrival)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Alerts */}
        <div className="panel">
          <div className="panel-hd">
            <div className="panel-title">Alerts & Actions</div>
            {alerts.length > 0 && <span className="pill pill-red">{alerts.length} urgent</span>}
          </div>
          {alerts.length === 0 ? (
            <div className="empty-state" style={{ padding: '20px 0' }}>
              <div className="empty-state-icon">✓</div>
              <div className="empty-state-text">No active alerts</div>
            </div>
          ) : (
            alerts.map((a, i) => (
              <div key={i} className={`alert-block alert-${a.type === 'red' ? 'red' : 'amber'}`}>
                <div className="alert-icon" style={{ background: a.type === 'red' ? 'var(--red-t)' : 'var(--amb-t)' }}>
                  {a.type === 'red' ? '!' : '~'}
                </div>
                <div style={{ fontSize: 12, color: a.type === 'red' ? 'var(--red)' : 'var(--amb)' }}>{a.msg}</div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="grid-3">
        {/* Trade corridors */}
        <div className="panel">
          <div className="panel-hd"><div className="panel-title">Top Trade Corridors</div></div>
          <BarChart rows={corridors.slice(0, 5).map((c, i) => ({
            label: c.corridor.replace(' → ', '→').substring(0, 12),
            val: c.total_value_usd,
            display: fmt.usd(c.total_value_usd),
            color: ['var(--grn-t)', 'var(--grn-t)', 'var(--grn-t)', 'var(--amb-t)', 'var(--blu-t)'][i],
          }))} />
        </div>

        {/* Recent transactions */}
        <div className="panel">
          <div className="panel-hd">
            <div className="panel-title">Recent Transactions</div>
            <button className="btn btn-sm btn-secondary" onClick={() => navigate('/transactions')}>All →</button>
          </div>
          {transactions.map((t) => {
            const st = TXN_STATUS[t.status] || { label: t.status, pill: 'pill-grey' }
            const isCredit = t.amount_usd > 0
            return (
              <div key={t.id} className="activity-item">
                <div className="activity-dot" style={{ background: isCredit ? 'var(--grn-t)' : 'var(--red-t)' }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="activity-text" style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.description}</span>
                    <span style={{ color: isCredit ? 'var(--grn)' : 'var(--red)', flexShrink: 0 }}>
                      {isCredit ? '+' : ''}{fmt.usd(t.amount_usd)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 6, marginTop: 3, alignItems: 'center' }}>
                    <span className={`pill ${st.pill}`} style={{ fontSize: 10 }}>{st.label}</span>
                    <span className="activity-time">{fmt.relativeDate(t.created_at)}</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Financial snapshot */}
        <div className="panel">
          <div className="panel-hd"><div className="panel-title">Financial Snapshot — MTD</div></div>
          <div style={{ marginBottom: 14 }}>
            {[
              { label: 'Revenue', val: kpi?.revenue_mtd || 0, positive: true },
              { label: 'Net Operating', val: kpi?.net_profit_mtd || 0, positive: (kpi?.net_profit_mtd || 0) > 0 },
            ].map((row) => (
              <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--surface2)', alignItems: 'center' }}>
                <span style={{ fontSize: 12, color: 'var(--txt2)' }}>{row.label}</span>
                <span style={{ fontFamily: 'var(--font-serif)', fontSize: 16, fontWeight: 300, color: row.positive ? 'var(--grn)' : 'var(--red)' }}>
                  {row.positive ? '+' : ''}{fmt.usd(row.val)}
                </span>
              </div>
            ))}
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/reports')} style={{ width: '100%', justifyContent: 'center' }}>
            Full Reports →
          </button>
        </div>
      </div>
    </div>
  )
}
