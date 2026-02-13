import { useState, useEffect, useRef, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, ChevronDown, Save, X, XCircle, PanelRight, PanelLeft, User } from 'lucide-react'
import SearchBar from './SearchBar'
import { propertyApi } from '../api/client'
import './TopFilterBar.css'

const OPTIONS_STALE_MS = 5 * 60 * 1000 // Cache options for 5 min per filter combo

export interface FilterChangeOptions {
  center?: [number, number]
  zoom?: number
}

interface TopFilterBarProps {
  onFilterChange?: (filter: string, value: any, options?: FilterChangeOptions) => void
  onSearchChange?: (query: string, source?: 'address_town' | 'owner') => void
  onClearAllFilters?: () => void
  /** Selected town(s); string or array for multi-select. Used to scope search bar autocomplete. */
  municipality?: string | string[] | null
  filterParams?: Record<string, any>
  sidebarOpen?: boolean
  onSidebarToggle?: () => void
}

export default function TopFilterBar({ onFilterChange, onSearchChange, onClearAllFilters, municipality, filterParams, sidebarOpen, onSidebarToggle }: TopFilterBarProps) {
  const [selectedFilters, setSelectedFilters] = useState<Record<string, any>>({})
  // Lazy-load large option lists only when dropdown is opened (reduces startup cost)
  const [unitTypeDropdownOpen, setUnitTypeDropdownOpen] = useState(false)
  const [zoningDropdownOpen, setZoningDropdownOpen] = useState(false)
  const [ownerCityDropdownOpen, setOwnerCityDropdownOpen] = useState(false)
  const getFirstValue = (value: any): string | undefined => {
    if (!value) return undefined
    return Array.isArray(value) ? value[0] : value
  }
  const filtersForOptions = useMemo(() => {
    const municipalityStr =
      municipality == null
        ? undefined
        : Array.isArray(municipality)
          ? municipality.filter(Boolean).join(',').trim() || undefined
          : String(municipality).trim() || undefined
    return {
      municipality: municipalityStr,
      unitType: getFirstValue(selectedFilters.unitType),
      zoning: getFirstValue(selectedFilters.zoning),
      propertyAge: getFirstValue(selectedFilters.propertyAge),
      timeSinceSale: getFirstValue(selectedFilters.timeSinceSale),
      annualTax: getFirstValue(selectedFilters.annualTax),
      ownerCity: getFirstValue(selectedFilters.ownerCity),
      ownerState: getFirstValue(selectedFilters.ownerState),
    }
  }, [municipality, selectedFilters.unitType, selectedFilters.zoning, selectedFilters.propertyAge, selectedFilters.timeSinceSale, selectedFilters.annualTax, selectedFilters.ownerCity, selectedFilters.ownerState])

  const { data: towns = [], isLoading: loadingTowns, isError: townsError, error: townsErr } = useQuery({
    queryKey: ['towns'],
    queryFn: () => propertyApi.getTowns(),
    staleTime: OPTIONS_STALE_MS,
  })
  const { data: unitTypeOptions = [], isLoading: loadingUnitTypes } = useQuery({
    queryKey: ['unitTypes', filtersForOptions],
    queryFn: async () => {
      const r = await propertyApi.getUnitTypeOptions(filtersForOptions)
      return r?.unit_types ?? []
    },
    staleTime: OPTIONS_STALE_MS,
    enabled: unitTypeDropdownOpen,
  })
  const { data: zoningOptions = [], isLoading: loadingZoning } = useQuery({
    queryKey: ['zoning', filtersForOptions],
    queryFn: async () => {
      const r = await propertyApi.getZoningOptions(filtersForOptions)
      return r?.zoning_codes ?? []
    },
    staleTime: OPTIONS_STALE_MS,
    enabled: zoningDropdownOpen,
  })
  const { data: ownerCities = [], isLoading: loadingOwnerCities } = useQuery({
    queryKey: ['ownerCities', filtersForOptions],
    queryFn: () => propertyApi.getOwnerCities(filtersForOptions),
    staleTime: OPTIONS_STALE_MS,
    enabled: ownerCityDropdownOpen,
  })
  const { data: ownerStates = [], isLoading: loadingOwnerStates } = useQuery({
    queryKey: ['ownerStates', filtersForOptions],
    queryFn: () => propertyApi.getOwnerStates(filtersForOptions),
    staleTime: OPTIONS_STALE_MS,
  })
  // #region agent log
  useEffect(() => {
    if (townsError) console.error('❌ [API] getTowns failed:', townsErr)
  }, [townsError, townsErr])
  // #endregion

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

  // Sync selectedFilters with filterParams prop (for timeSinceSale and other filters)
  useEffect(() => {
    if (filterParams) {
      setSelectedFilters((prev) => {
        const newFilters = { ...prev }
        
        // Sync timeSinceSale (single-select)
        if (filterParams.time_since_sale) {
          newFilters.timeSinceSale = filterParams.time_since_sale
        } else if (filterParams.time_since_sale === undefined && prev.timeSinceSale) {
          // Only clear if it was explicitly removed (not just missing)
          delete newFilters.timeSinceSale
        }
        
        // Sync annualTax
        if (filterParams.annual_tax) {
          newFilters.annualTax = [filterParams.annual_tax]
        } else if (filterParams.annual_tax === undefined && prev.annualTax) {
          delete newFilters.annualTax
        }
        
        // Sync zoning (handle comma-separated string)
        if (filterParams.zoning) {
          newFilters.zoning = typeof filterParams.zoning === 'string' 
            ? filterParams.zoning.split(',').map((z: string) => z.trim())
            : filterParams.zoning
        } else if (filterParams.zoning === undefined && prev.zoning) {
          delete newFilters.zoning
        }
        
        // Sync unitType (handle comma-separated string)
        if (filterParams.unit_type) {
          newFilters.unitType = typeof filterParams.unit_type === 'string'
            ? filterParams.unit_type.split(',').map((u: string) => u.trim())
            : filterParams.unit_type
        } else if (filterParams.unit_type === undefined && prev.unitType) {
          delete newFilters.unitType
        }
        
        // Sync ownerCity (handle comma-separated string)
        if (filterParams.owner_city) {
          newFilters.ownerCity = typeof filterParams.owner_city === 'string'
            ? filterParams.owner_city.split(',').map((c: string) => c.trim())
            : filterParams.owner_city
        } else if (filterParams.owner_city === undefined && prev.ownerCity) {
          delete newFilters.ownerCity
        }
        
        // Sync ownerState (handle comma-separated string)
        if (filterParams.owner_state) {
          newFilters.ownerState = typeof filterParams.owner_state === 'string'
            ? filterParams.owner_state.split(',').map((s: string) => s.trim())
            : filterParams.owner_state
        } else if (filterParams.owner_state === undefined && prev.ownerState) {
          delete newFilters.ownerState
        }
        
        return newFilters
      })
    }
  }, [filterParams])


  const handleFilterSelect = (filterName: string, value: any, updateStateOrOptions: boolean | FilterChangeOptions = true) => {
    const updateState = typeof updateStateOrOptions === 'boolean' ? updateStateOrOptions : true
    const options = typeof updateStateOrOptions === 'object' && updateStateOrOptions !== null ? updateStateOrOptions : undefined
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
        // Update filter with the exact value from the suggestion (no over-normalization)
        const newFilters = { ...selectedFilters }
        newFilters[filterName] = value
        if (updateState) {
          setSelectedFilters(newFilters)
        }
        if (onFilterChange) {
          onFilterChange(filterName, value, options)
        }
      }
      return
    }
    
    // If "Clear" is selected (or null/undefined passed from clear-X), clear the filter
    if (value === 'Clear' || value === '' || value == null) {
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

  // Check if there are any active filters
  const hasActiveFilters = () => {
    if (!filterParams && !municipality) return false
    const hasParams = filterParams && Object.keys(filterParams).length > 0
    const hasSelectedFilters = Object.keys(selectedFilters).length > 0
    const hasMunicipality = municipality !== null && municipality !== undefined && municipality !== ''
    return hasParams || hasSelectedFilters || hasMunicipality
  }

  return (
    <div className="top-filter-bar">
      <div className="filter-bar-content">
        {/* Merdan Logo */}
        <div className="merdan-logo">
          <div className="logo-main">MERDAN</div>
          <div className="logo-subtitle">PROPERTY GROUP</div>
        </div>
        
        {/* Main search: address + town in one bar (scoped to selected town(s) when set) */}
        <div className="filter-search-section">
          <div className="search-with-chip">
            <SearchBar
              searchMode="address_town"
              placeholder="Address or town..."
              onQueryChange={onSearchChange}
              municipality={municipality ?? undefined}
            />
          </div>
        </div>
        {/* Owner search: separate bar for owner name (scoped to selected town(s) when set) */}
        <div className="filter-search-owner">
          <div className="search-with-chip">
            <SearchBar
              searchMode="owner"
              placeholder="Search by owner..."
              onQueryChange={onSearchChange}
              municipality={municipality ?? undefined}
            />
          </div>
        </div>

        {/* Mailing address search: same style as Address and Owner search bars */}
        <div className="filter-search-mailing">
          <div className="search-bar-input-box filter-search-mailing-input-box">
            <Search className="search-icon" size={20} />
            <FilterDropdown
              label="Mailing Address"
              options={['Clear']}
              onSelect={(value, options) => handleFilterSelect('ownerAddress', value, options)}
              selected={selectedFilters.ownerAddress}
              multiSelect={false}
              isTextInput={true}
              placeholder="Enter mailing address..."
              selectedFilters={selectedFilters}
              municipality={municipality}
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
          
          {/* Unit Type Filter - Dynamic (lazy-loaded when dropdown opens) */}
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
            onOpenChange={setUnitTypeDropdownOpen}
          />
          
          {/* Zoning Filter - Dynamic (lazy-loaded when dropdown opens) */}
          <FilterDropdown
            label="Zoning"
            options={loadingZoning ? ['Loading...'] : ['Clear', ...zoningOptions]}
            onSelect={(value) => handleFilterSelect('zoning', value)}
            selected={selectedFilters.zoning}
            disabled={loadingZoning}
            multiSelect={true}
            onOpenChange={setZoningDropdownOpen}
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
            multiSelect={false}
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
          
          {/* Owner Mailing City Filter (lazy-loaded when dropdown opens) */}
          <FilterDropdown
            label="Owner Mailing City"
            options={loadingOwnerCities ? ['Loading...'] : ['Clear', ...ownerCities]}
            onSelect={(value) => handleFilterSelect('ownerCity', value)}
            selected={selectedFilters.ownerCity}
            disabled={loadingOwnerCities}
            multiSelect={true}
            onOpenChange={setOwnerCityDropdownOpen}
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

        {/* Properties sidebar toggle - visible so user can open/close sidebar */}
        {onSidebarToggle && (
          <button
            type="button"
            className={`properties-sidebar-toggle ${sidebarOpen ? 'open' : ''}`}
            onClick={onSidebarToggle}
            aria-label={sidebarOpen ? 'Close properties sidebar' : 'Open properties sidebar'}
            title={sidebarOpen ? 'Close properties sidebar' : 'Open properties sidebar'}
          >
            {sidebarOpen ? <PanelLeft size={18} /> : <PanelRight size={18} />}
            <span>Properties</span>
          </button>
        )}

        {/* Clear All Filters Button */}
        {hasActiveFilters() && onClearAllFilters && (
          <button 
            className="clear-all-filters-btn-nav"
            onClick={onClearAllFilters}
            aria-label="Clear all filters"
            title="Clear all filters"
          >
            <XCircle size={16} />
            <span>Clear All</span>
          </button>
        )}

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
  onSelect: (value: string, options?: FilterChangeOptions) => void
  selected?: string | string[]
  disabled?: boolean
  multiSelect?: boolean
  isTextInput?: boolean
  placeholder?: string
  selectedFilters?: Record<string, any>
  /** Scope autocomplete to these town(s); string or array for multi-select. */
  municipality?: string | string[] | null
  /** Called when dropdown open state changes (for lazy-loading options) */
  onOpenChange?: (open: boolean) => void
}

function FilterDropdown({ label, options, onSelect, selected, disabled, multiSelect = false, isTextInput = false, placeholder, selectedFilters = {}, municipality, onOpenChange }: FilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [textInputValue, setTextInputValue] = useState('')
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState<string[]>([])
  const [richAutocompleteSuggestions, setRichAutocompleteSuggestions] = useState<Array<{ type: string; value: string; display: string; count?: number; center_lat?: number; center_lng?: number }>>([])
  const [showAutocomplete, setShowAutocomplete] = useState(false)
  const [isLoadingAutocomplete, setIsLoadingAutocomplete] = useState(false)
  const useRichAutocomplete = isTextInput && label === 'Mailing Address'
  const searchInputRef = useRef<HTMLInputElement>(null)
  const autocompleteRef = useRef<HTMLDivElement>(null)
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const MAILING_DEBOUNCE_MS = 400
  
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
  // For Town multi-select, show selected town names so user sees "Middletown, Danbury" not just "Town (2)"
  const displayValue = selectedCount > 0 
    ? (multiSelect && Array.isArray(selected) 
        ? (label === 'Town' ? selected.join(', ') : `${label} (${selectedCount})`)
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

  // Focus search input when dropdown opens; notify parent for lazy-loading
  useEffect(() => {
    onOpenChange?.(isOpen)
    if (isOpen && searchInputRef.current && !isTextInput) {
      searchInputRef.current.focus()
    } else if (!isOpen) {
      setSearchQuery('') // Clear search when dropdown closes
    }
  }, [isOpen, isTextInput, onOpenChange])

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

  // Fetch autocomplete suggestions for Mailing Address (rich format like other search bars) or other text inputs
  useEffect(() => {
    if (!isTextInput) return

    const fetchSuggestions = async () => {
      if (useRichAutocomplete) {
        if (textInputValue.length < 2) {
          setRichAutocompleteSuggestions([])
          setShowAutocomplete(false)
          return
        }
        setIsLoadingAutocomplete(true)
        try {
          const municipalityParam =
            municipality == null
              ? undefined
              : Array.isArray(municipality)
                ? municipality.filter(Boolean).join(',').trim() || undefined
                : String(municipality).trim() || undefined
          const { suggestions } = await propertyApi.getAutocompleteSuggestions(
            textInputValue,
            'owner_address',
            10,
            undefined,
            municipalityParam
          )
          setRichAutocompleteSuggestions(suggestions)
          setShowAutocomplete(suggestions.length > 0 && textInputValue.length > 0)
        } catch (error) {
          console.error('Error fetching mailing address suggestions:', error)
          setRichAutocompleteSuggestions([])
          setShowAutocomplete(false)
        } finally {
          setIsLoadingAutocomplete(false)
        }
      } else {
        if (textInputValue.length < 1) {
          setAutocompleteSuggestions([])
          setShowAutocomplete(false)
          return
        }
        setIsLoadingAutocomplete(true)
        try {
          const municipalityStr =
            municipality == null
              ? undefined
              : Array.isArray(municipality)
                ? municipality.filter(Boolean).join(',').trim() || undefined
                : String(municipality).trim() || undefined
          const filters = {
            municipality: municipalityStr,
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
    }

    const debounceMs = useRichAutocomplete ? 400 : 300
    const timer = setTimeout(() => {
      fetchSuggestions()
    }, debounceMs)

    return () => clearTimeout(timer)
  }, [textInputValue, isTextInput, label, selectedFilters, municipality, useRichAutocomplete])

  // Clear debounce timer on unmount (Mailing Address)
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
        debounceTimerRef.current = null
      }
    }
  }, [])

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
    if (useRichAutocomplete) {
      // Debounce search: only notify parent after user stops typing to avoid many /api/search/ calls
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current)
      debounceTimerRef.current = setTimeout(() => {
        debounceTimerRef.current = null
        onSelect(value)
      }, MAILING_DEBOUNCE_MS)
    } else {
      onSelect(value)
    }
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

  const handleRichSuggestionSelect = (suggestion: { type: string; value: string; display: string; count?: number; center_lat?: number; center_lng?: number }) => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
      debounceTimerRef.current = null
    }
    setTextInputValue(suggestion.value)
    const center: [number, number] | undefined =
      suggestion.center_lat != null && suggestion.center_lng != null
        ? [suggestion.center_lat, suggestion.center_lng]
        : undefined
    onSelect(suggestion.value, center ? { center, zoom: 10 } : undefined)
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
              const hasSuggestions = useRichAutocomplete
                ? richAutocompleteSuggestions.length > 0 && textInputValue.length >= 2
                : autocompleteSuggestions.length > 0 && textInputValue.length > 0
              if (hasSuggestions) {
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
                if (debounceTimerRef.current) {
                  clearTimeout(debounceTimerRef.current)
                  debounceTimerRef.current = null
                }
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
            useRichAutocomplete ? (
              <div className="search-bar-suggestions">
                {isLoadingAutocomplete ? (
                  <div className="search-bar-loading">Loading...</div>
                ) : richAutocompleteSuggestions.length === 0 ? (
                  <div className="search-bar-no-results">No results found</div>
                ) : (
                  richAutocompleteSuggestions.map((suggestion, index) => (
                    <button
                      key={`${suggestion.type}-${suggestion.value}-${index}`}
                      type="button"
                      className="search-bar-suggestion"
                      data-type="owner_address"
                      onClick={() => handleRichSuggestionSelect(suggestion)}
                    >
                      <div className="search-bar-suggestion-icon">
                        <User size={16} />
                      </div>
                      <div className="search-bar-suggestion-content">
                        <div className="search-bar-suggestion-text">
                          {suggestion.display}
                        </div>
                        {suggestion.count != null && (
                          <div className="search-bar-suggestion-count">
                            {suggestion.count.toLocaleString()} {suggestion.count === 1 ? 'property' : 'properties'}
                          </div>
                        )}
                      </div>
                    </button>
                  ))
                )}
              </div>
            ) : (
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
            )
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
            <span
              role="button"
              tabIndex={0}
              className="clear-selection-btn"
              title="Clear selection"
              onClick={(e) => {
                e.stopPropagation()
                onSelect('Clear')
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  e.stopPropagation()
                  onSelect('Clear')
                }
              }}
            >
              <X size={12} />
            </span>
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
