import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Search } from 'lucide-react'

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <nav className={`navbar ${scrolled ? 'scrolled' : ''}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '40px' }}>
        <Link to="/" className="nav-brand">
          <span style={{ fontSize: '28px' }}>Peblo</span> TV
        </Link>
        
        <div className="nav-links">
          <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}>
            Home
          </Link>
          <Link to="/#series" className="nav-link">Series</Link>
          <Link to="/#songs" className="nav-link">Songs</Link>
        </div>
      </div>

      <div className="nav-actions">
        <Link to="/search" style={{ color: 'white' }}>
          <Search size={24} />
        </Link>
        <div style={{ width: '32px', height: '32px', borderRadius: '4px', backgroundColor: 'var(--brand-primary)' }}></div>
      </div>
    </nav>
  )
}
