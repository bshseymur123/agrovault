import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// Attach JWT on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('agrovault_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('agrovault_token')
      localStorage.removeItem('agrovault_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
  register: (data) => api.post('/auth/register', data),
}

// ─── Shipments ────────────────────────────────────────────────────────────────
export const shipmentsApi = {
  list: (params) => api.get('/shipments', { params }),
  get: (id) => api.get(`/shipments/${id}`),
  create: (data) => api.post('/shipments', data),
  update: (id, data) => api.patch(`/shipments/${id}`, data),
  updateStatus: (id, status, note) => api.post(`/shipments/${id}/status`, { status, note }),
  timeline: (id) => api.get(`/shipments/${id}/timeline`),
  createQC: (id, data) => api.post(`/shipments/${id}/qc`, data),
  getQC: (id) => api.get(`/shipments/${id}/qc`),
}

// ─── Customs ──────────────────────────────────────────────────────────────────
export const customsApi = {
  list: (params) => api.get('/customs', { params }),
  create: (shipmentId, data) => api.post(`/customs/shipment/${shipmentId}`, data),
  updateStatus: (id, data) => api.patch(`/customs/${id}/status`, data),
}

// ─── Transactions ─────────────────────────────────────────────────────────────
export const transactionsApi = {
  list: (params) => api.get('/transactions', { params }),
  create: (data) => api.post('/transactions', data),
  updateStatus: (id, data) => api.patch(`/transactions/${id}/status`, data),
}

// ─── Analytics ────────────────────────────────────────────────────────────────
export const analyticsApi = {
  dashboard: () => api.get('/analytics/dashboard'),
  corridors: () => api.get('/analytics/corridors'),
  report: (period) => api.get(`/analytics/report/${period}`),
}

export default api

// ─── Documents ────────────────────────────────────────────────────────────────
export const documentsApi = {
  list: (shipmentId) => api.get(`/shipments/${shipmentId}/documents`),
  upload: (shipmentId, docType, file, customsRecordId = null) => {
    const form = new FormData()
    form.append('doc_type', docType)
    form.append('file', file)
    if (customsRecordId) form.append('customs_record_id', customsRecordId)
    return api.post(`/shipments/${shipmentId}/documents`, form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  download: (shipmentId, docId) =>
    api.get(`/shipments/${shipmentId}/documents/${docId}/download`, { responseType: 'blob' }),
  delete: (shipmentId, docId) =>
    api.delete(`/shipments/${shipmentId}/documents/${docId}`),
}

// ─── Storage ──────────────────────────────────────────────────────────────────
export const storageApi = {
  bays: () => api.get('/storage/bays'),
}
