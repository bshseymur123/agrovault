// ─── Number / currency formatting ─────────────────────────────────────────
export const fmt = {
  usd: (n) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n || 0),
  usdFull: (n) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n || 0),
  kg: (n) => `${new Intl.NumberFormat('en-US').format(n || 0)} kg`,
  pct: (n) => `${(n || 0).toFixed(1)}%`,
  date: (d) => d ? new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—',
  datetime: (d) => d ? new Date(d).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—',
  relativeDate: (d) => {
    if (!d) return '—'
    const diff = Math.floor((new Date() - new Date(d)) / 86400000)
    if (diff === 0) return 'Today'
    if (diff === 1) return 'Yesterday'
    if (diff < 0) return `In ${Math.abs(diff)}d`
    return `${diff}d ago`
  },
}

// ─── Status display maps ──────────────────────────────────────────────────

export const SHIPMENT_STATUS = {
  draft:            { label: 'Draft',           pill: 'pill-grey' },
  confirmed:        { label: 'Confirmed',        pill: 'pill-blu'  },
  qc_sorting:       { label: 'QC / Sorting',     pill: 'pill-prp'  },
  packaging:        { label: 'Packaging',        pill: 'pill-prp'  },
  export_customs:   { label: 'Export Customs',   pill: 'pill-amb'  },
  in_transit:       { label: 'In Transit',       pill: 'pill-amb'  },
  import_customs:   { label: 'Import Customs',   pill: 'pill-amb'  },
  in_storage:       { label: 'In Storage',       pill: 'pill-blu'  },
  delivered:        { label: 'Delivered',        pill: 'pill-grn'  },
  invoiced:         { label: 'Invoiced',         pill: 'pill-grn'  },
  payment_received: { label: 'Payment Received', pill: 'pill-grn'  },
  cancelled:        { label: 'Cancelled',        pill: 'pill-red'  },
}

export const CUSTOMS_STATUS = {
  not_started: { label: 'Not Started', pill: 'pill-grey' },
  submitted:   { label: 'Submitted',   pill: 'pill-blu'  },
  processing:  { label: 'Processing',  pill: 'pill-amb'  },
  hold:        { label: 'Hold',        pill: 'pill-red'  },
  cleared:     { label: 'Cleared',     pill: 'pill-grn'  },
  rejected:    { label: 'Rejected',    pill: 'pill-red'  },
}

export const TXN_STATUS = {
  pending:   { label: 'Pending',   pill: 'pill-amb'  },
  paid:      { label: 'Paid',      pill: 'pill-grn'  },
  overdue:   { label: 'Overdue',   pill: 'pill-red'  },
  cancelled: { label: 'Cancelled', pill: 'pill-grey' },
}

export const TXN_TYPE = {
  revenue:      { label: 'Revenue',      color: 'var(--grn-t)' },
  freight:      { label: 'Freight',      color: 'var(--red-t)' },
  customs_duty: { label: 'Customs Duty', color: 'var(--amb-t)' },
  storage:      { label: 'Storage',      color: 'var(--blu-t)' },
  packaging:    { label: 'Packaging',    color: 'var(--prp-t)' },
  procurement:  { label: 'Procurement',  color: 'var(--txt2)'  },
  tax:          { label: 'Tax',          color: 'var(--red-t)' },
  other_opex:   { label: 'Other OpEx',   color: 'var(--txt3)'  },
}

// Ordered pipeline steps for timeline rendering
export const PIPELINE_STEPS = [
  { key: 'draft',            label: 'Order Created'   },
  { key: 'confirmed',        label: 'Confirmed'       },
  { key: 'qc_sorting',       label: 'QC / Sorting'    },
  { key: 'packaging',        label: 'Packaging'       },
  { key: 'export_customs',   label: 'Export Customs'  },
  { key: 'in_transit',       label: 'In Transit'      },
  { key: 'import_customs',   label: 'Import Customs'  },
  { key: 'in_storage',       label: 'Cold Storage'    },
  { key: 'delivered',        label: 'Delivered'       },
  { key: 'invoiced',         label: 'Invoiced'        },
  { key: 'payment_received', label: 'Payment Rec.'    },
]

export const PIPELINE_ORDER = PIPELINE_STEPS.map((s) => s.key)

export const COUNTRIES = [
  'Azerbaijan', 'Turkey', 'Russia', 'Iran', 'Georgia',
  'Egypt', 'UAE', 'Germany', 'France', 'Poland', 'Ukraine', 'Uzbekistan', 'Other',
]

export const PRODUCTS = [
  'Tomatoes', 'Apples', 'Grapes', 'Citrus Mix', 'Pomegranate',
  'Peaches', 'Pears', 'Plums', 'Cherries', 'Watermelon',
  'Onions', 'Potatoes', 'Peppers', 'Cucumbers', 'Other',
]

export const DOC_TYPES = [
  'Commercial Invoice', 'Bill of Lading', 'Packing List',
  'Certificate of Origin', 'Phytosanitary Certificate',
  'Pesticide Residue Report', 'Customs Declaration',
  'Insurance Certificate', 'Quality Certificate', 'Other',
]

export const REQUIRED_DOCS = [
  'Commercial Invoice', 'Bill of Lading', 'Packing List',
  'Certificate of Origin', 'Phytosanitary Certificate',
  'Customs Declaration',
]
