import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Home, Search, Map } from 'lucide-react'
import SearchBar from './SearchBar'
import './Layout.css'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  return (
    <div className="layout">
      <header className="header">
        <div className="header-content">
          <Link to="/" className="logo">
            <Map className="logo-icon" />
            <span>CT Property Search</span>
          </Link>
          <nav className="nav">
            <Link
              to="/"
              className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
            >
              <Map size={18} />
              Map
            </Link>
          </nav>
        </div>
      </header>
      <main className="main-content">{children}</main>
    </div>
  )
}
