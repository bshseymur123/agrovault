import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../utils/api'
import { useAuthStore } from '../store/store'

export default function LoginPage() {
  const [email, setEmail] = useState('ceo@agrovault.com')
  const [password, setPassword] = useState('demo123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const DEMO_ACCOUNTS = [
    { label: 'CEO',        email: 'ceo@agrovault.com',        pw: 'demo123' },
    { label: 'Director',   email: 'director@agrovault.com',   pw: 'demo123' },
    { label: 'Manager',    email: 'manager@agrovault.com',    pw: 'demo123' },
    { label: 'Accountant', email: 'accountant@agrovault.com', pw: 'demo123' },
    { label: 'Operator',   email: 'operator@agrovault.com',   pw: 'demo123' },
  ]

  const handleSubmit = async (e) => {
    e?.preventDefault()
    setLoading(true); setError('')
    try {
      const res = await authApi.login(email, password)
      setAuth(res.data.access_token, res.data.user)
      navigate('/dashboard')
    } catch {
      setError('Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: 'var(--bg)', padding: 20
    }}>
      <div style={{ width: '100%', maxWidth: 380 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: 28, fontWeight: 300, color: 'var(--txt)' }}>
            AgroVault
          </div>
          <div style={{ fontSize: 10, letterSpacing: 3, textTransform: 'uppercase', color: 'var(--txt3)', marginTop: 4 }}>
            Trade Operations System
          </div>
        </div>

        <div className="panel" style={{ padding: 28 }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input
                className="form-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="username"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                className="form-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            {error && <div className="error-msg">{error}</div>}
            <button className="btn btn-primary" type="submit" disabled={loading} style={{ marginTop: 4, justifyContent: 'center' }}>
              {loading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : 'Sign In'}
            </button>
          </form>

          {/* Demo accounts */}
          <div style={{ marginTop: 20, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
            <div style={{ fontSize: 10, letterSpacing: 1.5, textTransform: 'uppercase', color: 'var(--txt3)', marginBottom: 8 }}>
              Demo accounts
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {DEMO_ACCOUNTS.map((a) => (
                <button
                  key={a.label}
                  onClick={() => { setEmail(a.email); setPassword(a.pw) }}
                  style={{
                    padding: '4px 10px', fontSize: 10, background: 'var(--surface2)',
                    border: '1px solid var(--border)', borderRadius: 3,
                    cursor: 'pointer', fontFamily: 'var(--font-mono)',
                    color: email === a.email ? 'var(--grn)' : 'var(--txt2)',
                    borderColor: email === a.email ? 'var(--grn-t)' : 'var(--border)',
                  }}
                >
                  {a.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div style={{ textAlign: 'center', marginTop: 16, fontSize: 11, color: 'var(--txt3)' }}>
          AgroVault v1.0 · Fresh Produce Trade OS
        </div>
      </div>
    </div>
  )
}
