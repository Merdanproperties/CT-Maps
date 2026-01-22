import { useState } from 'react'
import { Search, ChevronDown, SlidersHorizontal, Save } from 'lucide-react'
import SearchBar from './SearchBar'
import './TopFilterBar.css'

interface TopFilterBarProps {
  onFilterChange?: (filter: string, value: any) => void
  onSearchChange?: (query: string) => void
}

export default function TopFilterBar({ onFilterChange, onSearchChange }: TopFilterBarProps) {
  const [selectedFilters, setSelectedFilters] = useState<Record<string, any>>({})

  const handleFilterSelect = (filterName: string, value: any) => {
    const newFilters = { ...selectedFilters, [filterName]: value }
    setSelectedFilters(newFilters)
    if (onFilterChange) {
      onFilterChange(filterName, value)
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
            label="Property Types"
            options={[
              'Single Family',
              'Two Family',
              'Multi Family',
              'Commercial',
              'Vacant Land'
            ]}
            onSelect={(value) => handleFilterSelect('propertyTypes', value)}
            selected={selectedFilters.propertyTypes}
          />
          
          <FilterDropdown
            label="Price"
            options={[
              'Under $100K',
              '$100K - $200K',
              '$200K - $300K',
              '$300K - $500K',
              '$500K+'
            ]}
            onSelect={(value) => handleFilterSelect('price', value)}
            selected={selectedFilters.price}
          />
          
          <FilterDropdown
            label="Beds / Baths"
            options={[
              '1+ Bed',
              '2+ Beds',
              '3+ Beds',
              '1+ Bath',
              '2+ Baths'
            ]}
            onSelect={(value) => handleFilterSelect('bedsBaths', value)}
            selected={selectedFilters.bedsBaths}
          />
          
          <button className="filter-more-btn">
            <SlidersHorizontal size={16} />
            <span>More</span>
          </button>
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

  return (
    <div className="filter-dropdown">
      <button
        className={`filter-dropdown-btn ${selected ? 'has-selection' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span>{selected || label}</span>
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
