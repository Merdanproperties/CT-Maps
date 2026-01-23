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
    // Check backend health on app startup
    const initializeHealthCheck = async () => {
      console.log('🔍 Checking backend connection on startup...')
      const isHealthy = await healthCheckService.waitForHealthy(10000) // Wait up to 10 seconds
      
      if (isHealthy) {
        console.log('✅ Backend is healthy and ready')
      } else {
        console.warn('⚠️ Backend health check failed or timed out. Continuing anyway...')
      }
      
      // Start continuous monitoring
      healthCheckService.startMonitoring()
    }

    initializeHealthCheck()

    // Cleanup on unmount
    return () => {
      healthCheckService.stopMonitoring()
    }
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
