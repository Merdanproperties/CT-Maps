import { useState } from 'react'
import { X, TrendingUp, Home, User, DollarSign, Calendar } from 'lucide-react'
import './FilterPanel.css'

interface FilterPanelProps {
  onFilterChange: (type: string | null, params: any) => void
}

export default function FilterPanel({ onFilterChange }: FilterPanelProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeFilter, setActiveFilter] = useState<string | null>(null)
  const [params, setParams] = useState<any>({})

  const filters = [
    {
      id: 'high-equity',
      label: 'High Equity',
      icon: TrendingUp,
      description: 'Properties with high equity',
    },
    {
      id: 'vacant',
      label: 'Vacant Properties',
      icon: Home,
      description: 'Vacant lots and structures',
    },
    {
      id: 'absentee-owners',
      label: 'Absentee Owners',
      icon: User,
      description: 'Properties with absentee owners',
    },
    {
      id: 'recently-sold',
      label: 'Recently Sold',
      icon: Calendar,
      description: 'Properties sold recently',
    },
    {
      id: 'low-equity',
      label: 'Low Equity',
      icon: DollarSign,
      description: 'Properties with low equity',
    },
  ]

  const handleFilterSelect = (filterId: string) => {
    if (activeFilter === filterId) {
      setActiveFilter(null)
      setParams({})
      onFilterChange(null, {})
    } else {
      setActiveFilter(filterId)
      const defaultParams = getDefaultParams(filterId)
      setParams(defaultParams)
      onFilterChange(filterId, defaultParams)
    }
  }

  const getDefaultParams = (filterId: string) => {
    switch (filterId) {
      case 'high-equity':
        return { min_equity: 50000 }
      case 'recently-sold':
        return { days: 365 }
      case 'low-equity':
        return { max_equity: 10000 }
      default:
        return {}
    }
  }

  const handleParamChange = (key: string, value: any) => {
    const newParams = { ...params, [key]: value }
    setParams(newParams)
    onFilterChange(activeFilter, newParams)
  }

  return (
    <div className={`filter-panel ${isOpen ? 'open' : ''}`}>
      <button
        className="filter-toggle"
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <X size={20} /> : 'Filters'}
      </button>

      {isOpen && (
        <div className="filter-content">
          <h3>Lead Generation Filters</h3>
          <div className="filter-list">
            {filters.map((filter) => {
              const Icon = filter.icon
              const isActive = activeFilter === filter.id

              return (
                <div key={filter.id} className="filter-item">
                  <button
                    className={`filter-button ${isActive ? 'active' : ''}`}
                    onClick={() => handleFilterSelect(filter.id)}
                  >
                    <Icon size={20} />
                    <div>
                      <div className="filter-label">{filter.label}</div>
                      <div className="filter-description">{filter.description}</div>
                    </div>
                  </button>

                  {isActive && filter.id === 'high-equity' && (
                    <div className="filter-params">
                      <label>
                        Min Equity ($)
                        <input
                          type="number"
                          value={params.min_equity || 50000}
                          onChange={(e) =>
                            handleParamChange('min_equity', parseFloat(e.target.value))
                          }
                        />
                      </label>
                    </div>
                  )}

                  {isActive && filter.id === 'recently-sold' && (
                    <div className="filter-params">
                      <label>
                        Days
                        <input
                          type="number"
                          value={params.days || 365}
                          onChange={(e) =>
                            handleParamChange('days', parseInt(e.target.value))
                          }
                        />
                      </label>
                    </div>
                  )}

                  {isActive && filter.id === 'low-equity' && (
                    <div className="filter-params">
                      <label>
                        Max Equity ($)
                        <input
                          type="number"
                          value={params.max_equity || 10000}
                          onChange={(e) =>
                            handleParamChange('max_equity', parseFloat(e.target.value))
                          }
                        />
                      </label>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
