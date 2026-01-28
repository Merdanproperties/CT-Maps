import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from './components/Layout'
import MapView from './pages/MapView'
import PropertyDetail from './pages/PropertyDetail'
import SearchView from './pages/SearchView'
import ConnectionStatus from './components/ConnectionStatus'
import { healthCheckService } from './services/healthCheck'

function App() {
  useEffect(() => {
    // One initial /health check on load only; no periodic monitoring (status from real API success/failure)
    const init = async () => {
      const status = await healthCheckService.checkHealth(false)
      if (status.isHealthy) {
        if (status.database === 'connected') console.log('✅ Backend is healthy')
        else if (status.database === 'disconnected') console.warn('⚠️ Database temporarily unavailable; backend is reachable')
      } else {
        const err = status.error ?? 'Backend unreachable'
        if (err === 'Connection check in progress') return
        if (err.includes('timeout') || err.toLowerCase().includes('not responding')) console.warn('⚠️ Backend unavailable; check it is running on port 8000')
        else console.warn('⚠️ Backend check failed:', err)
      }
    }
    init()
  }, [])

  return (
    <Router
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <ConnectionStatus />
      <Layout>
        <Routes>
          <Route path="/" element={<MapView />} />
          <Route path="/search" element={<SearchView />} />
          <Route path="/property/:id" element={<PropertyDetail />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
