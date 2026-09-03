import { NavLink } from 'react-router-dom'
import { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
  onLogout: () => void
}

export default function Layout({ children, onLogout }: LayoutProps) {
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">📺 Peblo TV</div>
        <div className="sidebar-subtitle">Content Management</div>
        <nav>
          <ul className="sidebar-nav">
            <li>
              <NavLink to="/shows" className={({ isActive }) => isActive ? 'active' : ''}>
                🎬 Shows
              </NavLink>
            </li>
            <li>
              <NavLink to="/episodes" className={({ isActive }) => isActive ? 'active' : ''}>
                📋 Episodes
              </NavLink>
            </li>
            <li>
              <NavLink to="/publish" className={({ isActive }) => isActive ? 'active' : ''}>
                🚀 Publish
              </NavLink>
            </li>
          </ul>
        </nav>
        <div className="sidebar-user">
          <div style={{ marginBottom: 4 }}>
            <strong>{user.username}</strong>{' '}
            <span className={`role-badge ${user.role}`}>{user.role}</span>
          </div>
          <button
            className="btn btn-sm btn-secondary"
            onClick={onLogout}
            style={{ width: '100%', marginTop: 8 }}
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  )
}
