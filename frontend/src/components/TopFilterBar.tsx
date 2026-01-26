import { useState, useEffect, useRef } from 'react'
import { Search, ChevronDown, Save, X } from 'lucide-react'
import SearchBar from './SearchBar'
import { propertyApi } from '../api/client'
import './TopFilterBar.css'

interface TopFilterBarProps {
  onFilterChange?: (filter: string, value: any) => void
  onSearchChange?: (query: string) => void
  municipality?: string | null
}

export default function TopFilterBar({ onFilterChange, onSearchChange, municipality }: TopFilterBarProps) {
  const [selectedFilters, setSelectedFilters] = useState<Record<string, any>>({})
  const [towns, setTowns] = useState<string[]>([])
  const [unitTypeOptions, setUnitTypeOptions] = useState<Array<{property_type: string, land_use: string | null}>>([])
  const [zoningOptions, setZoningOptions] = useState<string[]>([])
  const [ownerCities, setOwnerCities] = useState<string[]>([])
  const [ownerStates, setOwnerStates] = useState<string[]>([])
  const [loadingTowns, setLoadingTowns] = useState(false)
  const [loadingUnitTypes, setLoadingUnitTypes] = useState(false)
  const [loadingZoning, setLoadingZoning] = useState(false)
  const [loadingOwnerCities, setLoadingOwnerCities] = useState(false)
  const [loadingOwnerStates, setLoadingOwnerStates] = useState(false)

  // Sync selectedFilters with municipality prop
  useEffect(() => {
    if (municipality !== selectedFilters.municipality) {
      setSelectedFilters((prev) => {
        const newFilters = { ...prev }
        if (municipality) {
          newFilters.municipality = municipality
        } else {
          delete newFilters.municipality
        }
        return newFilters
      })
    }
  }, [municipality])

  // Fetch towns on mount
  useEffect(() => {
    const fetchTowns = async () => {
      setLoadingTowns(true)
      try {
        const townsList = await propertyApi.getTowns()
        setTowns(townsList)
      } catch (error) {
        console.error('Error fetching towns:', error)
      } finally {
        setLoadingTowns(false)
      }
    }
    fetchTowns()
  }, [])

  // Helper to get first value from array or single value
  const getFirstValue = (value: any): string | undefined => {
    if (!value) return undefined
    return Array.isArray(value) ? value[0] : value
  }

  // Fetch unit type options when any filter changes
  useEffect(() => {
    const fetchUnitTypes = async () => {
      setLoadingUnitTypes(true)
      try {
        const filters = {
          municipality: municipality || undefined,
          zoning: getFirstValue(selectedFilters.zoning),
          propertyAge: getFirstValue(selectedFilters.propertyAge),
          timeSinceSale: getFirstValue(selectedFilters.timeSinceSale),
          annualTax: getFirstValue(selectedFilters.annualTax),
          ownerCity: getFirstValue(selectedFilters.ownerCity),
          ownerState: getFirstValue(selectedFilters.ownerState)
        }
        const result = await propertyApi.getUnitTypeOptions(filters)
        setUnitTypeOptions(result.unit_types)
      } catch (error) {
        console.error('Error fetching unit types:', error)
      } finally {
        setLoadingUnitTypes(false)
      }
    }
    fetchUnitTypes()
  }, [municipality, selectedFilters.zoning, selectedFilters.propertyAge, selectedFilters.timeSinceSale, selectedFilters.annualTax, selectedFilters.ownerCity, selectedFilters.ownerState])

  // Fetch zoning options when any filter changes
  useEffect(() => {
    const fetchZoning = async () => {
      setLoadingZoning(true)
      try {
        const filters = {
          municipality: municipality || undefined,
          unitType: getFirstValue(selectedFilters.unitType),
          propertyAge: getFirstValue(selectedFilters.propertyAge),
          timeSinceSale: getFirstValue(selectedFilters.timeSinceSale),
          annualTax: getFirstValue(selectedFilters.annualTax),
          ownerCity: getFirstValue(selectedFilters.ownerCity),
          ownerState: getFirstValue(selectedFilters.ownerState)
        }
        const result = await propertyApi.getZoningOptions(filters)
        setZoningOptions(result.zoning_codes)
      } catch (error) {
        console.error('Error fetching zoning options:', error)
      } finally {
        setLoadingZoning(false)
      }
    }
    fetchZoning()
  }, [municipality, selectedFilters.unitType, selectedFilters.propertyAge, selectedFilters.timeSinceSale, selectedFilters.annualTax, selectedFilters.ownerCity, selectedFilters.ownerState])

  // Fetch owner cities when any filter changes
  useEffect(() => {
    const fetchOwnerCities = async () => {
      setLoadingOwnerCities(true)
      try {
        const filters = {
          municipality: municipality || undefined,
          unitType: getFirstValue(selectedFilters.unitType),
          zoning: getFirstValue(selectedFilters.zoning),
          propertyAge: getFirstValue(selectedFilters.propertyAge),
          timeSinceSale: getFirstValue(selectedFilters.timeSinceSale),
          annualTax: getFirstValue(selectedFilters.annualTax),
          ownerState: getFirstValue(selectedFilters.ownerState)
        }
        const citiesList = await propertyApi.getOwnerCities(filters)
        setOwnerCities(citiesList)
      } catch (error) {
        console.error('Error fetching owner cities:', error)
      } finally {
        setLoadingOwnerCities(false)
      }
    }
    fetchOwnerCities()
  }, [municipality, selectedFilters.unitType, selectedFilters.zoning, selectedFilters.propertyAge, selectedFilters.timeSinceSale, selectedFilters.annualTax, selectedFilters.ownerState])

  // Fetch owner states when any filter changes
  useEffect(() => {
    const fetchOwnerStates = async () => {
      setLoadingOwnerStates(true)
      try {
        const filters = {
          municipality: municipality || undefined,
          unitType: getFirstValue(selectedFilters.unitType),
          zoning: getFirstValue(selectedFilters.zoning),
          propertyAge: getFirstValue(selectedFilters.propertyAge),
          timeSinceSale: getFirstValue(selectedFilters.timeSinceSale),
          annualTax: getFirstValue(selectedFilters.annualTax),
          ownerCity: getFirstValue(selectedFilters.ownerCity)
        }
        const statesList = await propertyApi.getOwnerStates(filters)
        setOwnerStates(statesList)
      } catch (error) {
        console.error('Error fetching owner states:', error)
      } finally {
        setLoadingOwnerStates(false)
      }
    }
    fetchOwnerStates()
  }, [municipality, selectedFilters.unitType, selectedFilters.zoning, selectedFilters.propertyAge, selectedFilters.timeSinceSale, selectedFilters.annualTax, selectedFilters.ownerCity])

  const handleFilterSelect = (filterName: string, value: any, updateState: boolean = true) => {
    // Special handling for text inputs (like ownerAddress)
    // Don't clear on empty string - let the MapView handler decide
    if (filterName === 'ownerAddress') {
      if (value === 'Clear' || value === null || value === undefined) {
        // Only clear if explicitly 'Clear' or null/undefined
        const newFilters = { ...selectedFilters }
        delete newFilters[filterName]
        if (updateState) {
          setSelectedFilters(newFilters)
        }
        if (onFilterChange) {
          onFilterChange(filterName, null)
        }
      } else {
        // Update filter with the actual value (even if it's a single character)
        const newFilters = { ...selectedFilters }
        newFilters[filterName] = value
        if (updateState) {
          setSelectedFilters(newFilters)
        }
        if (onFilterChange) {
          onFilterChange(filterName, value)
        }
      }
      return
    }
    
    // If "Clear" is selected, clear the filter
    if (value === 'Clear' || value === '') {
      const newFilters = { ...selectedFilters }
      delete newFilters[filterName]
      if (updateState) {
        setSelectedFilters(newFilters)
      }
      if (onFilterChange) {
        onFilterChange(filterName, null)
      }
    } else {
      // Handle multi-select: toggle value in array
      const currentValue = selectedFilters[filterName]
      let newValue: any
      
      if (Array.isArray(currentValue)) {
        // Toggle: remove if exists, add if not
        if (currentValue.includes(value)) {
          newValue = currentValue.filter((v: any) => v !== value)
          if (newValue.length === 0) {
            // Remove filter if empty
            const newFilters = { ...selectedFilters }
            delete newFilters[filterName]
            if (updateState) {
              setSelectedFilters(newFilters)
            }
            if (onFilterChange) {
              onFilterChange(filterName, null)
            }
            return
          }
        } else {
          newValue = [...currentValue, value]
        }
      } else {
        // First selection: create array
        newValue = [value]
      }
      
      const newFilters = { ...selectedFilters, [filterName]: newValue }
      if (updateState) {
        setSelectedFilters(newFilters)
      }
      if (onFilterChange) {
        onFilterChange(filterName, newValue)
      }
    }
  }

  // Format unit type for display
  const formatUnitType = (unitType: {property_type: string, land_use: string | null}): string => {
    if (unitType.land_use) {
      return `${unitType.property_type} - ${unitType.land_use}`
    }
    return unitType.property_type
  }

  return (
    <div className="top-filter-bar">
      <div className="filter-bar-content">
        {/* Merdan Logo */}
        <div className="merdan-logo">
          <div className="logo-main">MERDAN</div>
          <div className="logo-subtitle">PROPERTY GROUP</div>
        </div>
        
        {/* Search integrated into filter bar */}
        <div className="filter-search-section">
          <div className="search-with-chip">
            <SearchBar 
              placeholder="Address, city, owner name, owner address..." 
              onQueryChange={onSearchChange}
            />
          </div>
        </div>

        {/* Filter Dropdowns */}
        <div className="filter-dropdowns">
          {/* Town Filter */}
          <FilterDropdown
            label="Town"
            options={loadingTowns ? ['Loading...'] : ['Clear', ...towns]}
            onSelect={(value) => handleFilterSelect('municipality', value)}
            selected={selectedFilters.municipality}
            disabled={loadingTowns}
            multiSelect={true}
          />
          
          {/* Unit Type Filter - Dynamic */}
          <FilterDropdown
            label="Unit Type"
            options={loadingUnitTypes 
              ? ['Loading...'] 
              : ['Clear', ...unitTypeOptions.map(formatUnitType)]
            }
            onSelect={(value) => {
              if (value === 'Clear' || value === '') {
                handleFilterSelect('unitType', null)
              } else {
                // Find the unit type object that matches the formatted string
                const unitType = unitTypeOptions.find(ut => formatUnitType(ut) === value)
                if (unitType) {
                  handleFilterSelect('unitType', formatUnitType(unitType))
                }
              }
            }}
            selected={selectedFilters.unitType}
            disabled={loadingUnitTypes}
            multiSelect={true}
          />
          
          {/* Zoning Filter - Dynamic */}
          <FilterDropdown
            label="Zoning"
            options={loadingZoning ? ['Loading...'] : ['Clear', ...zoningOptions]}
            onSelect={(value) => handleFilterSelect('zoning', value)}
            selected={selectedFilters.zoning}
            disabled={loadingZoning}
            multiSelect={true}
          />
          
          {/* Property Age Filter - Updated options */}
          <FilterDropdown
            label="Property Age"
            options={[
              'Clear',
              'Built 2020+',
              'Built 2010-2019',
              'Built 2000-2009',
              'Built 1990-1999',
              'Built 1980-1989',
              'Built 1970-1979',
              'Built 1960-1969',
              'Built 1950-1959',
              'Built 1940-1949',
              'Built 1930-1939',
              'Built 1920-1929',
              'Built 1900-1919',
              'Built Before 1900',
              'Unknown'
            ]}
            onSelect={(value) => handleFilterSelect('propertyAge', value)}
            selected={selectedFilters.propertyAge}
            multiSelect={true}
          />
          
          {/* Time Since Sale Filter */}
          <FilterDropdown
            label="Time Since Sale"
            options={[
              'Clear',
              'Last 2 Years',
              '2-5 Years Ago',
              '5-10 Years Ago',
              '10-20 Years Ago',
              '20+ Years Ago',
              'Never Sold'
            ]}
            onSelect={(value) => handleFilterSelect('timeSinceSale', value)}
            selected={selectedFilters.timeSinceSale}
            multiSelect={true}
          />
          
          {/* Annual Tax Filter */}
          <FilterDropdown
            label="Annual Tax"
            options={[
              'Clear',
              'Under $2,000',
              '$2,000 - $5,000',
              '$5,000 - $10,000',
              '$10,000 - $20,000',
              '$20,000+'
            ]}
            onSelect={(value) => handleFilterSelect('annualTax', value)}
            selected={selectedFilters.annualTax}
            multiSelect={true}
          />
          
          {/* Lead Types Filter */}
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
            multiSelect={true}
          />
          
          {/* Owner Mailing Address Filter */}
          <FilterDropdown
            label="Mailing Address"
            options={['Clear']}
            onSelect={(value) => handleFilterSelect('ownerAddress', value)}
            selected={selectedFilters.ownerAddress}
            multiSelect={false}
            isTextInput={true}
            placeholder="Enter mailing address..."
            selectedFilters={selectedFilters}
            municipality={municipality}
          />
          
          {/* Owner Mailing City Filter */}
          <FilterDropdown
            label="Owner Mailing City"
            options={loadingOwnerCities ? ['Loading...'] : ['Clear', ...ownerCities]}
            onSelect={(value) => handleFilterSelect('ownerCity', value)}
            selected={selectedFilters.ownerCity}
            disabled={loadingOwnerCities}
            multiSelect={true}
          />
          
          {/* Owner Mailing State Filter */}
          <FilterDropdown
            label="Owner Mailing State"
            options={loadingOwnerStates ? ['Loading...'] : ['Clear', ...ownerStates]}
            onSelect={(value) => handleFilterSelect('ownerState', value)}
            selected={selectedFilters.ownerState}
            disabled={loadingOwnerStates}
            multiSelect={true}
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
  selected?: string | string[]
  disabled?: boolean
  multiSelect?: boolean
  isTextInput?: boolean
  placeholder?: string
  selectedFilters?: Record<string, any>
  municipality?: string | null
}

function FilterDropdown({ label, options, onSelect, selected, disabled, multiSelect = false, isTextInput = false, placeholder, selectedFilters = {}, municipality }: FilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [textInputValue, setTextInputValue] = useState('')
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState<string[]>([])
  const [showAutocomplete, setShowAutocomplete] = useState(false)
  const [isLoadingAutocomplete, setIsLoadingAutocomplete] = useState(false)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const autocompleteRef = useRef<HTMLDivElement>(null)
  
  // Determine if option is selected (handle both single and multi-select)
  const isSelected = (option: string) => {
    if (option === 'Clear') return false
    if (multiSelect && Array.isArray(selected)) {
      return selected.includes(option)
    }
    return selected === option
  }
  
  // Get selected count for display
  const selectedCount = multiSelect && Array.isArray(selected) ? selected.length : (selected && selected !== 'Clear' ? 1 : 0)
  
  // Display value: show count or selected value(s)
  const displayValue = selectedCount > 0 
    ? (multiSelect && Array.isArray(selected) 
        ? `${label} (${selectedCount})` 
        : (typeof selected === 'string' ? selected : label))
    : label

  // Filter options based on search query
  const filteredOptions = options.filter(option => {
    if (option === 'Clear' || option === 'Loading...') return true
    return option.toLowerCase().includes(searchQuery.toLowerCase())
  })

  // Sync textInputValue with selected value
  useEffect(() => {
    if (isTextInput && typeof selected === 'string' && selected !== 'Clear' && selected) {
      setTextInputValue(selected)
    } else if (isTextInput && (!selected || selected === 'Clear')) {
      setTextInputValue('')
    }
  }, [selected, isTextInput])

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && searchInputRef.current && !isTextInput) {
      searchInputRef.current.focus()
    } else if (!isOpen) {
      setSearchQuery('') // Clear search when dropdown closes
    }
  }, [isOpen, isTextInput])

  const handleOptionClick = (option: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (option === 'Clear') {
      onSelect(option)
      if (!multiSelect) {
        setIsOpen(false)
        setSearchQuery('')
        setTextInputValue('')
      }
    } else {
      onSelect(option)
      // Don't close dropdown for multi-select, only for single select
      if (!multiSelect) {
        setIsOpen(false)
        setSearchQuery('')
      }
    }
  }

  // Helper to get first value from array or single value
  const getFirstValue = (value: any): string | undefined => {
    if (!value) return undefined
    return Array.isArray(value) ? value[0] : value
  }

  // Fetch autocomplete suggestions for owner address
  useEffect(() => {
    if (!isTextInput || label !== 'Mailing Address') return
    
    const fetchSuggestions = async () => {
      if (textInputValue.length < 1) {
        setAutocompleteSuggestions([])
        setShowAutocomplete(false)
        return
      }

      setIsLoadingAutocomplete(true)
      try {
        const filters = {
          municipality: municipality || undefined,
          unitType: getFirstValue(selectedFilters.unitType),
          zoning: getFirstValue(selectedFilters.zoning),
          propertyAge: getFirstValue(selectedFilters.propertyAge),
          timeSinceSale: getFirstValue(selectedFilters.timeSinceSale),
          annualTax: getFirstValue(selectedFilters.annualTax),
          ownerCity: getFirstValue(selectedFilters.ownerCity),
          ownerState: getFirstValue(selectedFilters.ownerState)
        }
        const suggestions = await propertyApi.getOwnerAddressSuggestions(textInputValue, filters)
        setAutocompleteSuggestions(suggestions)
        setShowAutocomplete(suggestions.length > 0 && textInputValue.length > 0)
      } catch (error) {
        console.error('Error fetching address suggestions:', error)
        setAutocompleteSuggestions([])
        setShowAutocomplete(false)
      } finally {
        setIsLoadingAutocomplete(false)
      }
    }

    const timer = setTimeout(() => {
      fetchSuggestions()
    }, 300) // Debounce

    return () => clearTimeout(timer)
  }, [textInputValue, isTextInput, label, selectedFilters, municipality])

  // Close autocomplete when clicking outside
  useEffect(() => {
    if (!isTextInput) return
    
    const handleClickOutside = (event: MouseEvent) => {
      if (autocompleteRef.current && !autocompleteRef.current.contains(event.target as Node)) {
        setShowAutocomplete(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isTextInput])

  const handleTextInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setTextInputValue(value)
    // Always call onSelect with the actual value, even if empty
    // This allows real-time search as user types
    onSelect(value)
  }

  const handleTextInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      setShowAutocomplete(false)
    }
  }

  const handleSuggestionSelect = (suggestion: string) => {
    setTextInputValue(suggestion)
    onSelect(suggestion)
    setShowAutocomplete(false)
  }

  return (
    <div className="filter-dropdown">
      {isTextInput ? (
        <div className="filter-text-input-wrapper" ref={autocompleteRef}>
          <input
            type="text"
            className="filter-text-input"
            placeholder={placeholder || label}
            value={typeof selected === 'string' && selected !== 'Clear' ? selected : textInputValue}
            onChange={handleTextInputChange}
            onKeyDown={handleTextInputKeyDown}
            onFocus={() => {
              setIsOpen(true)
              if (autocompleteSuggestions.length > 0 && textInputValue.length > 0) {
                setShowAutocomplete(true)
              }
            }}
            disabled={disabled}
          />
          {typeof selected === 'string' && selected !== 'Clear' && selected && (
            <button
              className="clear-text-input-btn"
              onClick={(e) => {
                e.stopPropagation()
                setTextInputValue('')
                onSelect('Clear')
                setShowAutocomplete(false)
              }}
              title="Clear"
            >
              <X size={14} />
            </button>
          )}
          {showAutocomplete && (
            <div className="filter-autocomplete-dropdown">
              {isLoadingAutocomplete ? (
                <div className="filter-autocomplete-loading">Loading...</div>
              ) : autocompleteSuggestions.length === 0 ? (
                <div className="filter-autocomplete-no-results">No results found</div>
              ) : (
                autocompleteSuggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    type="button"
                    className="filter-autocomplete-item"
                    onClick={() => handleSuggestionSelect(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      ) : (
        <button
          className={`filter-dropdown-btn ${selectedCount > 0 ? 'has-selection' : ''}`}
          onClick={() => setIsOpen(!isOpen)}
          disabled={disabled}
        >
          <span>{displayValue}</span>
          {selectedCount > 0 && multiSelect && (
            <button
              className="clear-selection-btn"
              onClick={(e) => {
                e.stopPropagation()
                onSelect('Clear')
              }}
              title="Clear selection"
            >
              <X size={12} />
            </button>
          )}
          <ChevronDown size={16} className={isOpen ? 'open' : ''} />
        </button>
      )}
      {isOpen && !isTextInput && (
        <>
          <div className="dropdown-overlay" onClick={() => setIsOpen(false)} />
          <div className="dropdown-menu">
            {/* Search input */}
            <div className="dropdown-search">
              <Search size={14} className="search-icon" />
              <input
                ref={searchInputRef}
                type="text"
                placeholder={`Search ${label.toLowerCase()}...`}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onClick={(e) => e.stopPropagation()}
                className="dropdown-search-input"
              />
            </div>
            {/* Options list */}
            <div className="dropdown-options">
              {filteredOptions.length > 0 ? (
                filteredOptions.map((option) => (
                  <button
                    key={option}
                    className={`dropdown-item ${isSelected(option) ? 'selected' : ''}`}
                    onClick={(e) => handleOptionClick(option, e)}
                  >
                    {multiSelect && option !== 'Clear' && (
                      <input
                        type="checkbox"
                        checked={isSelected(option)}
                        readOnly
                        className="dropdown-checkbox"
                      />
                    )}
                    <span>{option}</span>
                  </button>
                ))
              ) : (
                <div className="dropdown-no-results">No results found</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
