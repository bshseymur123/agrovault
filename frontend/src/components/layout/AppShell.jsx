import { useState } from 'react'
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore, useNotifyStore } from '../../store/store'
import '../../styles/layout.css'

const NAV = [
  { section: 'Operations', items: [
    { to: '/dashboard', label: 'Dashboard',     badge: null },
    { to: '/shipments', label: 'Shipments',     badge: null },
    { to: '/shipments/new', label: 'New Entry', badge: null },
  ]},
  { section: 'Compliance', items: [
    { to: '/customs', label: 'Customs',         badge: null },
    { to: '/quality', label: 'QC / Sorting',    badge: null },
  ]},
  { section: 'Finance', items: [
    { to: '/transactions', label: 'Transactions', badge: null },
    { to: '/reports',      label: 'Reports',      badge: null },
  ]},
  { section: 'Intelligence', items: [
    { to: '/analytics', label: 'Analytics', badge: null },
  ]},
  { section: 'Logistics', items: [
    { to: '/storage', label: 'Storage Bays', badge: null },
  ]},
]

export default function AppShell() {
  const { user, logout } = useAuthStore()
  const { notifications, dismiss } = useNotifyStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const isMobile = () => window.innerWidth <= 768

  const handleLogout = () => { logout(); navigate('/login') }

  // Close sidebar on mobile after navigation
  const handleNavClick = () => { if (isMobile()) setSidebarOpen(false) }

  const pageTitle = location.pathname.split('/').filter(Boolean).map((s) =>
    s.charAt(0).toUpperCase() + s.slice(1).replace(/-/g, ' ')
  ).join(' › ') || 'Dashboard'

  const shellClass = [
    'shell',
    !sidebarOpen ? 'sidebar-collapsed' : '',
    sidebarOpen && isMobile() ? 'sidebar-open' : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={shellClass}>
      {/* Mobile backdrop — click to close */}
      <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-mark">AgroVault</div>
          <div className="logo-sub">Trade OS</div>
        </div>

        <nav className="sidebar-nav">
          {NAV.map((group) => (
            <div key={group.section}>
              <div className="nav-section">{group.section}</div>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                  onClick={handleNavClick}
                >
                  <span className="nav-dot" />
                  <span>{item.label}</span>
                  {item.badge && <span className="nav-badge">{item.badge}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-role-label">Viewing as</div>
          <div className="user-role-badge">{user?.role?.toUpperCase()}</div>
          <div className="user-info">
            <div className="user-avatar">
              {user?.full_name?.split(' ').map((n) => n[0]).join('').slice(0, 2)}
            </div>
            <div>
              <div className="user-name">{user?.full_name}</div>
              <div className="user-email">{user?.email}</div>
            </div>
          </div>
          <button className="logout-btn" onClick={handleLogout}>Sign Out</button>
        </div>
      </aside>

      {/* Main */}
      <div className="main-area">
        <header className="topbar">
          <button className="menu-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>☰</button>
          <div className="topbar-title">{pageTitle}</div>
          <div className="topbar-meta">
            <span className="pill pill-grn" style={{ fontSize: 10 }}>● Live</span>
            <span style={{ color: 'var(--txt3)', fontSize: 11, marginLeft: 8 }}>
              {new Date().toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })}
            </span>
          </div>
        </header>

        <main className="page-content">
          <Outlet />
        </main>
      </div>

      {/* Toast notifications */}
      <div className="toast-stack">
        {notifications.map((n) => (
          <div key={n.id} className={`toast toast-${n.type}`}>
            <span>{n.message}</span>
            <button onClick={() => dismiss(n.id)}>×</button>
          </div>
        ))}
      </div>
    </div>
  )
}
