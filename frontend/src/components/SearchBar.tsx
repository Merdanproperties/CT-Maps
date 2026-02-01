import { useState, useRef, useEffect, useCallback } from 'react'
import { Search, MapPin, Building2, X, User, ChevronDown } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../api/client'
import { normalizeSearchQuery } from '../utils/searchUtils'
import './SearchBar.css'

interface AutocompleteSuggestion {
  type: 'address' | 'town' | 'state' | 'owner' | 'owner_address'
  value: string
  display: string
  count?: number
  center_lat?: number
  center_lng?: number
}

/** When set, single bar only (no type dropdown). address_town = address + town; owner = owner only. */
export type SearchBarMode = 'address_town' | 'owner'

interface SearchBarProps {
  onSelect?: (suggestion: AutocompleteSuggestion) => void
  onQueryChange?: (query: string) => void
  placeholder?: string
  /** Single bar for address+town or owner only; no dropdown. */
  searchMode?: SearchBarMode
  /** Scope autocomplete to these town(s); comma-separated string or array. When set, dropdown shows only results in selected town(s). */
  municipality?: string | string[] | null
}

export type SearchBarType = 'address' | 'town' | 'owner'

const SEARCH_TYPE_LABELS: Record<SearchBarType, string> = {
  address: 'Address',
  town: 'Town',
  owner: 'Owner',
}

const SEARCH_TYPE_PLACEHOLDERS: Record<SearchBarType, string> = {
  address: 'Search by address...',
  town: 'Search by town or city...',
  owner: 'Search by owner name...',
}

const MODE_PLACEHOLDERS: Record<SearchBarMode, string> = {
  address_town: 'Address or town...',
  owner: 'Search by owner...',
}

/** API search_type for each mode */
const MODE_SEARCH_TYPE: Record<SearchBarMode, string> = {
  address_town: 'address_town',
  owner: 'owner',
}

export default function SearchBar({ onSelect, onQueryChange, placeholder, searchMode, municipality }: SearchBarProps) {
  const navigate = useNavigate()
  const [searchType, setSearchType] = useState<SearchBarType>('address')
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<AutocompleteSuggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [isLoading, setIsLoading] = useState(false)
  const [showTypeDropdown, setShowTypeDropdown] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const effectiveSearchType = searchMode != null ? MODE_SEARCH_TYPE[searchMode] : searchType
  const effectivePlaceholder = placeholder ?? (searchMode != null ? MODE_PLACEHOLDERS[searchMode] : SEARCH_TYPE_PLACEHOLDERS[searchType])

  // Scope autocomplete to selected town(s): normalize to comma-separated string for API
  const municipalityParam =
    municipality == null
      ? undefined
      : Array.isArray(municipality)
        ? municipality.filter(Boolean).join(',').trim() || undefined
        : String(municipality).trim() || undefined

  // Fetch autocomplete suggestions – show dropdown as user types (Loading then results or No results)
  const fetchSuggestions = useCallback(async (searchQuery: string, signal?: AbortSignal) => {
    const normalized = normalizeSearchQuery(searchQuery)
    if (normalized.length < 2) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }

    setShowSuggestions(true) // Open dropdown immediately so user sees "Loading..." then results
    if (typeof setIsLoading === 'function') setIsLoading(true);
    // #region agent log
    (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SearchBar.tsx:40',message:'Fetching suggestions started',data:{searchQuery,queryLength:searchQuery.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{}));
    // #endregion
    try {
      const apiSearchType = searchMode != null ? MODE_SEARCH_TYPE[searchMode] : searchType
      const params: Record<string, string | number> = { q: normalized, limit: 10, search_type: apiSearchType }
      if (municipalityParam) params.municipality = municipalityParam
      const response = await apiClient.get('/api/autocomplete/', {
        params,
        signal,
      });
      const suggestions = response.data.suggestions || [];
      // #region agent log
      (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SearchBar.tsx:47',message:'Suggestions received',data:{searchQuery,suggestionCount:suggestions.length,suggestions:suggestions.map((s: AutocompleteSuggestion)=>({type:s.type,value:s.value,display:s.display})),willShow: suggestions.length > 0},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{}));
      // #endregion
      setSuggestions(suggestions);
      setShowSuggestions(true) // Keep dropdown open to show results or "No results found"
      setSelectedIndex(-1)
    } catch (error: any) {
      if (error?.name === 'CanceledError' || error?.code === 'ERR_CANCELED') return
      console.error('Autocomplete error:', error);
      // #region agent log
      (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SearchBar.tsx:52',message:'Autocomplete error',data:{searchQuery,error:error instanceof Error ? error.message : String(error)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{}));
      // #endregion
      setSuggestions([])
      setShowSuggestions(false)
    } finally {
      if (typeof setIsLoading === 'function') setIsLoading(false);
    }
  }, [searchMode, searchType, municipalityParam])

  // Debounced search; cancel in-flight request when query changes
  useEffect(() => {
    const controller = new AbortController()
    const timer = setTimeout(() => {
      if (query) {
        fetchSuggestions(query, controller.signal)
      } else {
        setSuggestions([])
        setShowSuggestions(false)
      }
    }, 300)

    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [query, fetchSuggestions])

  // Close suggestions only when we're sure the click was outside the search bar (including dropdown)
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node
      const el = searchRef.current
      let clickWasOutside: boolean | null = null // null = unknown, don't close
      try {
        if (el != null && typeof (el as Node).contains === 'function') {
          clickWasOutside = !(el as Node).contains(target)
        }
      } catch {
        clickWasOutside = null
      }
      // Only close when we're confident the click was outside; if ref/contains is unreliable, don't close
      if (clickWasOutside === true) {
        setShowSuggestions(false)
        setShowTypeDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (suggestion: AutocompleteSuggestion) => {
    console.log('🔘 Selection made:', suggestion);
    // #region agent log
    (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SearchBar.tsx:86',message:'handleSelect called',data:{suggestionType:suggestion.type,suggestionValue:suggestion.value,suggestionDisplay:suggestion.display,currentShowSuggestions:showSuggestions},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{}));
    // #endregion
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
        navState.municipality = suggestion.value;
      } else if (suggestion.type === 'address') {
        navState.center = suggestion.center_lat && suggestion.center_lng 
          ? [suggestion.center_lat, suggestion.center_lng] 
          : null
        navState.zoom = 18
        navState.address = suggestion.value;
        // #region agent log
        (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SearchBar.tsx:106',message:'Address suggestion selected',data:{address:suggestion.value,suggestionType:suggestion.type,centerLat:suggestion.center_lat,centerLng:suggestion.center_lng,navCenter:navState.center,count:suggestion.count},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{}));
        // #endregion
      } else if (suggestion.type === 'owner') {
        // Owner name search - set query to owner name, center on average location
        navState.center = suggestion.center_lat && suggestion.center_lng 
          ? [suggestion.center_lat, suggestion.center_lng] 
          : null
        navState.zoom = 10
        navState.searchQuery = suggestion.value;  // Owner name
      } else if (suggestion.type === 'owner_address') {
        // Owner address search - set query to owner address, center on average location
        navState.center = suggestion.center_lat && suggestion.center_lng 
          ? [suggestion.center_lat, suggestion.center_lng] 
          : null
        navState.zoom = 10
        navState.searchQuery = suggestion.value;  // Owner mailing address
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

  const searchTypes: SearchBarType[] = ['address', 'town', 'owner']

  return (
    <div className="search-bar" ref={searchRef}>
      <div className="search-bar-row">
        {/* Type dropdown only when searchMode is not set (single combined bar) */}
        {searchMode == null && (
          <div className="search-bar-type-dropdown">
            <button
              type="button"
              className="search-bar-type-dropdown-btn"
              onClick={() => setShowTypeDropdown((open) => !open)}
              aria-expanded={showTypeDropdown}
              aria-haspopup="listbox"
              aria-label="Search by"
            >
              <span>{SEARCH_TYPE_LABELS[searchType]}</span>
              <ChevronDown size={16} className={showTypeDropdown ? 'open' : ''} />
            </button>
            {showTypeDropdown && (
              <>
                <div className="search-bar-type-overlay" onClick={() => setShowTypeDropdown(false)} aria-hidden="true" />
                <div className="search-bar-type-menu" role="listbox">
                  {searchTypes.map((type) => (
                    <button
                      key={type}
                      type="button"
                      role="option"
                      aria-selected={searchType === type}
                      className={`search-bar-type-option ${searchType === type ? 'selected' : ''}`}
                      onClick={() => {
                        setSearchType(type)
                        setSuggestions([])
                        setShowSuggestions(false)
                        setShowTypeDropdown(false)
                        inputRef.current?.focus()
                      }}
                    >
                      {SEARCH_TYPE_LABELS[type]}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
        <div className="search-bar-input-box">
          <Search className="search-icon" size={20} />
          <input
            ref={inputRef}
            type="text"
            className="search-bar-input"
            placeholder={effectivePlaceholder}
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
      </div>

      {showSuggestions && (
        <div 
          className="search-bar-suggestions"
          onMouseEnter={() => {
            // #region agent log
            (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SearchBar.tsx:250',message:'Dropdown mouse enter',data:{suggestionCount:suggestions.length,isLoading},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{}));
            // #endregion
          }}
          ref={(domEl) => {
            if (domEl && typeof domEl.getBoundingClientRect === 'function') {
              try {
                const rect = domEl.getBoundingClientRect();
                // #region agent log
                (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SearchBar.tsx:256',message:'Dropdown rendered/positioned',data:{top:rect?.top,left:rect?.left,width:rect?.width,height:rect?.height,isVisible:rect && rect.width > 0 && rect.height > 0},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{}));
                // #endregion
              } catch (_) {}
            }
          }}
        >
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
                data-type={suggestion.type}
                onMouseDown={(e) => {
                  // #region agent log
                  (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SearchBar.tsx:262',message:'Suggestion button mousedown',data:{index,suggestionType:suggestion.type,suggestionValue:suggestion.value,showSuggestions},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{}));
                  // #endregion
                }}
                onClick={(e) => {
                  // #region agent log
                  (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'SearchBar.tsx:268',message:'Suggestion button click',data:{index,suggestionType:suggestion.type,suggestionValue:suggestion.value,showSuggestions},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{}));
                  // #endregion
                  handleSelect(suggestion)
                }}
              >
                <div className="search-bar-suggestion-icon">
                  {suggestion.type === 'town' ? (
                    <Building2 size={16} />
                  ) : suggestion.type === 'owner' || suggestion.type === 'owner_address' ? (
                    <User size={16} />
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
