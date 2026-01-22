import { useState, useRef, useEffect, useCallback } from 'react'
import { Search, MapPin, Building2, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../api/client'
import './SearchBar.css'

interface AutocompleteSuggestion {
  type: 'address' | 'town'
  value: string
  display: string
  count?: number
  center_lat?: number
  center_lng?: number
}

interface SearchBarProps {
  onSelect?: (suggestion: AutocompleteSuggestion) => void
  onQueryChange?: (query: string) => void
  placeholder?: string
}

export default function SearchBar({ onSelect, onQueryChange, placeholder = "Search address or town..." }: SearchBarProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<AutocompleteSuggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [isLoading, setIsLoading] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Fetch autocomplete suggestions
  const fetchSuggestions = useCallback(async (searchQuery: string) => {
    if (searchQuery.length < 2) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }

    setIsLoading(true)
    try {
      const response = await apiClient.get('/api/autocomplete/', {
        params: { q: searchQuery, limit: 10 }
      })
      setSuggestions(response.data.suggestions || [])
      setShowSuggestions(response.data.suggestions?.length > 0)
      setSelectedIndex(-1)
    } catch (error) {
      console.error('Autocomplete error:', error)
      setSuggestions([])
      setShowSuggestions(false)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (query) {
        fetchSuggestions(query)
      } else {
        setSuggestions([])
        setShowSuggestions(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [query, fetchSuggestions])

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (suggestion: AutocompleteSuggestion) => {
    console.log('🔘 Selection made:', suggestion)
    setQuery(suggestion.display)
    setShowSuggestions(false)
    
    if (onSelect) {
      onSelect(suggestion)
    } else {
      // Default behavior: navigate to map with location
      // This will trigger the property list to show
      const navState: any = {}
      
      if (suggestion.type === 'state') {
        navState.center = suggestion.center_lat && suggestion.center_lng 
          ? [suggestion.center_lat, suggestion.center_lng] 
          : null
        navState.zoom = 8
      } else if (suggestion.type === 'town') {
        navState.center = suggestion.center_lat && suggestion.center_lng 
          ? [suggestion.center_lat, suggestion.center_lng] 
          : null
        navState.zoom = 11
        navState.municipality = suggestion.value
      } else if (suggestion.type === 'address') {
        navState.center = suggestion.center_lat && suggestion.center_lng 
          ? [suggestion.center_lat, suggestion.center_lng] 
          : null
        navState.zoom = 18
        navState.address = suggestion.value
      }
      
      console.log('🧭 Navigating with state:', navState)
      navigate('/', { 
        state: navState,
        replace: false
      })
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        if (showSuggestions && suggestions.length > 0) {
          e.preventDefault()
          setSelectedIndex(prev => 
            prev < suggestions.length - 1 ? prev + 1 : prev
          )
        }
        break
      case 'ArrowUp':
        if (showSuggestions && suggestions.length > 0) {
          e.preventDefault()
          setSelectedIndex(prev => prev > 0 ? prev - 1 : -1)
        }
        break
      case 'Enter':
        e.preventDefault()
        console.log('⌨️ Enter pressed', { showSuggestions, suggestionsCount: suggestions.length, selectedIndex, query, isLoading })
        
        if (isLoading) {
          // Wait for suggestions to load
          console.log('⏳ Waiting for suggestions to load...')
          const checkInterval = setInterval(() => {
            if (!isLoading && suggestions.length > 0) {
              clearInterval(checkInterval)
              console.log('✅ Suggestions loaded, selecting first:', suggestions[0])
              handleSelect(suggestions[0])
            } else if (!isLoading) {
              clearInterval(checkInterval)
              console.log('⚠️ No suggestions found after loading')
            }
          }, 100)
          // Timeout after 2 seconds
          setTimeout(() => clearInterval(checkInterval), 2000)
        } else if (showSuggestions && suggestions.length > 0) {
          // If a suggestion is selected, use it
          if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
            console.log('✅ Selecting suggestion at index:', selectedIndex, suggestions[selectedIndex])
            handleSelect(suggestions[selectedIndex])
          } else {
            // If no suggestion selected but suggestions exist, select the first one
            console.log('✅ Selecting first suggestion:', suggestions[0])
            handleSelect(suggestions[0])
          }
        } else if (query.trim().length > 0) {
          // If no suggestions but query exists, try to search for it
          // This handles cases where user types and presses Enter before suggestions load
          console.log('🔍 No suggestions, creating search for:', query.trim())
          const searchSuggestion: AutocompleteSuggestion = {
            type: 'address',
            value: query.trim(),
            display: query.trim()
          }
          handleSelect(searchSuggestion)
        }
        break
      case 'Escape':
        setShowSuggestions(false)
        break
    }
  }

  const handleClear = () => {
    setQuery('')
    setSuggestions([])
    setShowSuggestions(false)
    if (onQueryChange) {
      onQueryChange('')
    }
    inputRef.current?.focus()
  }

  return (
    <div className="search-bar" ref={searchRef}>
      <div className="search-bar-input-wrapper">
        <Search className="search-icon" size={20} />
        <input
          ref={inputRef}
          type="text"
          className="search-bar-input"
          placeholder={placeholder}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            if (onQueryChange) {
              onQueryChange(e.target.value)
            }
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (suggestions.length > 0) {
              setShowSuggestions(true)
            }
          }}
        />
        {query && (
          <button
            type="button"
            className="search-bar-clear"
            onClick={handleClear}
            aria-label="Clear search"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {showSuggestions && (
        <div className="search-bar-suggestions">
          {isLoading ? (
            <div className="search-bar-loading">Loading...</div>
          ) : suggestions.length === 0 ? (
            <div className="search-bar-no-results">No results found</div>
          ) : (
            suggestions.map((suggestion, index) => (
              <button
                key={`${suggestion.type}-${suggestion.value}-${index}`}
                type="button"
                className={`search-bar-suggestion ${
                  index === selectedIndex ? 'selected' : ''
                }`}
                onClick={() => handleSelect(suggestion)}
              >
                <div className="search-bar-suggestion-icon">
                  {suggestion.type === 'town' ? (
                    <Building2 size={16} />
                  ) : (
                    <MapPin size={16} />
                  )}
                </div>
                <div className="search-bar-suggestion-content">
                  <div className="search-bar-suggestion-text">
                    {suggestion.display}
                  </div>
                  {suggestion.count && (
                    <div className="search-bar-suggestion-count">
                      {suggestion.count.toLocaleString()} {suggestion.count === 1 ? 'property' : 'properties'}
                    </div>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
