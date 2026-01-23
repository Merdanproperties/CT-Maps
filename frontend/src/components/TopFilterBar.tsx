import { useState } from 'react'
import { Search, ChevronDown, Save } from 'lucide-react'
import SearchBar from './SearchBar'
import './TopFilterBar.css'

interface TopFilterBarProps {
  onFilterChange?: (filter: string, value: any) => void
  onSearchChange?: (query: string) => void
}

export default function TopFilterBar({ onFilterChange, onSearchChange }: TopFilterBarProps) {
  const [selectedFilters, setSelectedFilters] = useState<Record<string, any>>({})

  const handleFilterSelect = (filterName: string, value: any) => {
    // If "Clear" is selected, clear the filter
    if (value === 'Clear' || value === '') {
      const newFilters = { ...selectedFilters }
      delete newFilters[filterName]
      setSelectedFilters(newFilters)
      if (onFilterChange) {
        onFilterChange(filterName, null)
      }
    } else {
      const newFilters = { ...selectedFilters, [filterName]: value }
      setSelectedFilters(newFilters)
      if (onFilterChange) {
        onFilterChange(filterName, value)
      }
    }
  }

  return (
    <div className="top-filter-bar">
      <div className="filter-bar-content">
        {/* Search integrated into filter bar */}
        <div className="filter-search-section">
          <div className="search-with-chip">
            <SearchBar 
              placeholder="Address, city, county, state" 
              onQueryChange={onSearchChange}
            />
          </div>
        </div>

        {/* Filter Dropdowns */}
        <div className="filter-dropdowns">
          <FilterDropdown
            label="Lead Types"
            options={[
              'Clear',
              'High Equity',
              'Vacant Properties',
              'Absentee Owners',
              'Recently Sold',
              'Low Equity'
            ]}
            onSelect={(value) => handleFilterSelect('leadTypes', value)}
            selected={selectedFilters.leadTypes}
          />
          
          <FilterDropdown
            label="Property Type"
            options={[
              'Clear',
              'Residential',
              'Commercial',
              'Industrial',
              'Vacant Land',
              'Mixed Use'
            ]}
            onSelect={(value) => handleFilterSelect('propertyTypes', value)}
            selected={selectedFilters.propertyTypes}
          />
          
          <FilterDropdown
            label="Assessed Value"
            options={[
              'Clear',
              'Under $50K',
              '$50K - $100K',
              '$100K - $200K',
              '$200K - $500K',
              '$500K - $1M',
              '$1M+'
            ]}
            onSelect={(value) => handleFilterSelect('price', value)}
            selected={selectedFilters.price}
          />
          
          <FilterDropdown
            label="Lot Size"
            options={[
              'Clear',
              'Under 5,000 sqft',
              '5,000 - 10,000 sqft',
              '10,000 - 20,000 sqft',
              '20,000 - 43,560 sqft (1 acre)',
              '1+ acres'
            ]}
            onSelect={(value) => handleFilterSelect('lotSize', value)}
            selected={selectedFilters.lotSize}
          />
          
          <FilterDropdown
            label="Sale Date"
            options={[
              'Clear',
              'Last 30 days',
              'Last 90 days',
              'Last 6 months',
              'Last year',
              'Last 2 years',
              'Last 5 years'
            ]}
            onSelect={(value) => handleFilterSelect('saleDate', value)}
            selected={selectedFilters.saleDate}
          />
        </div>

        {/* Save Search Button */}
        <button className="save-search-btn">
          <Save size={16} />
          <span>Save Search</span>
        </button>
      </div>
    </div>
  )
}

interface FilterDropdownProps {
  label: string
  options: string[]
  onSelect: (value: string) => void
  selected?: string
}

function FilterDropdown({ label, options, onSelect, selected }: FilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  
  // Don't show "Clear" as selected - show label instead
  const displayValue = selected && selected !== 'Clear' ? selected : label

  return (
    <div className="filter-dropdown">
      <button
        className={`filter-dropdown-btn ${selected && selected !== 'Clear' ? 'has-selection' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span>{displayValue}</span>
        <ChevronDown size={16} className={isOpen ? 'open' : ''} />
      </button>
      {isOpen && (
        <>
          <div className="dropdown-overlay" onClick={() => setIsOpen(false)} />
          <div className="dropdown-menu">
            {options.map((option) => (
              <button
                key={option}
                className={`dropdown-item ${selected === option ? 'selected' : ''}`}
                onClick={() => {
                  onSelect(option)
                  setIsOpen(false)
                }}
              >
                {option}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
