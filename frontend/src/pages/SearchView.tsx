import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { propertyApi, analyticsApi } from '../api/client'
import PropertyCard from '../components/PropertyCard'
import ExportButton from '../components/ExportButton'
import { useNavigate } from 'react-router-dom'
import './SearchView.css'

export default function SearchView() {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [municipality, setMunicipality] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading, error } = useQuery({
    queryKey: ['search', searchQuery, municipality, page],
    queryFn: async () => {
      const result = await propertyApi.search({
        q: searchQuery || undefined,
        municipality: municipality || undefined,
        page,
        page_size: 50,
      })
      
      // Track search analytics
      try {
        await analyticsApi.trackSearch({
          query: searchQuery || undefined,
          municipality: municipality || undefined,
          result_count: result.total || 0,
        })
      } catch (error) {
        console.error('Analytics tracking failed:', error)
      }
      
      return result
    },
    enabled: searchQuery.length > 0 || municipality.length > 0,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
  }

  return (
    <div className="search-view">
      <div className="search-container">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            placeholder="Search by address, owner, or parcel ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          <input
            type="text"
            placeholder="Municipality (optional)"
            value={municipality}
            onChange={(e) => setMunicipality(e.target.value)}
            className="search-input"
          />
          <button type="submit" className="search-button">
            Search
          </button>
        </form>

        {isLoading && (
          <div className="loading">
            <div className="spinner" />
            <p>Searching...</p>
          </div>
        )}

        {error && (
          <div className="error">
            <p>Error searching properties. Please try again.</p>
          </div>
        )}

        {data && (
          <>
            <div className="results-header">
              <h2>
                {data.total.toLocaleString()} {data.total === 1 ? 'property' : 'properties'} found
              </h2>
              {data.total > 0 && (
                <ExportButton
                  filterParams={{
                    q: searchQuery || undefined,
                    municipality: municipality || undefined,
                  }}
                  resultCount={data.total}
                />
              )}
            </div>

            <div className="results-grid">
              {data.properties.map((property) => (
                <PropertyCard
                  key={property.id}
                  property={property}
                  onClick={() => navigate(`/property/${property.id}`)}
                />
              ))}
            </div>

            {data.total > data.page_size && (
              <div className="pagination">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="page-button"
                >
                  Previous
                </button>
                <span className="page-info">
                  Page {data.page} of {Math.ceil(data.total / data.page_size)}
                </span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page >= Math.ceil(data.total / data.page_size)}
                  className="page-button"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}

        {!data && !isLoading && (
          <div className="empty-state">
            <p>Enter a search query to find properties</p>
          </div>
        )}
      </div>
    </div>
  )
}
