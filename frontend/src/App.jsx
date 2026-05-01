import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/store'
import AppShell from './components/layout/AppShell'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import { ShipmentsPage, NewShipmentPage } from './pages/ShipmentsPage'
import ShipmentDetailPage from './pages/ShipmentDetailPage'
import { CustomsPage, TransactionsPage, ReportsPage, AnalyticsPage, QualityPage, StorageBaysPage } from './pages/OtherPages'

function ProtectedRoute({ children }) {
  const { token } = useAuthStore()
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="shipments" element={<ShipmentsPage />} />
          <Route path="shipments/new" element={<NewShipmentPage />} />
          <Route path="shipments/:id" element={<ShipmentDetailPage />} />
          <Route path="customs" element={<CustomsPage />} />
          <Route path="quality" element={<QualityPage />} />
          <Route path="transactions" element={<TransactionsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="storage" element={<StorageBaysPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
