import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import MapView from './pages/MapView'
import PropertyDetail from './pages/PropertyDetail'
import SearchView from './pages/SearchView'

function App() {
  return (
    <Router>
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
