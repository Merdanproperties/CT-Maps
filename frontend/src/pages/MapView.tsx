import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, useMap, useMapEvents, LayerGroup } from 'react-leaflet'
import { MapBoundsUpdater } from './MapBoundsUpdater'
import { useQuery } from '@tanstack/react-query'
import { propertyApi, Property, analyticsApi } from '../api/client'
import PropertyCard from '../components/PropertyCard'
import TopFilterBar from '../components/TopFilterBar'
import ExportButton from '../components/ExportButton'
import { useNavigate, useLocation } from 'react-router-dom'
import { X, ChevronRight, ChevronLeft, PanelRight } from 'lucide-react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './MapView.css'

// Fix for default marker icons in React-Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

// MapBoundsUpdater removed - not needed for basic functionality

// Component to update map view when center/zoom changes
function MapUpdater({ center, zoom, skipUpdate, onUpdate }: { 
  center: [number, number], 
  zoom: number, 
  skipUpdate?: boolean,
  onUpdate?: () => void
}) {
  const map = useMap()
  const isUpdatingRef = useRef(false)
  const lastCenterRef = useRef<string | null>(null)
  const lastZoomRef = useRef<number | null>(null)
  
  useEffect(() => {
    if (skipUpdate) {
      return
    }
    
    // Create a stable string key for center to detect changes
    const centerKey = `${center[0].toFixed(5)},${center[1].toFixed(5)}`
    const centerChanged = lastCenterRef.current !== centerKey
    const zoomChanged = lastZoomRef.current === null || 
      Math.abs(lastZoomRef.current - zoom) > 0.01
    
    if (centerChanged || zoomChanged) {
      // Don't update if already updating to prevent loops
      if (isUpdatingRef.current) {
        return
      }
      
      console.log('🗺️ MapUpdater: Updating map view', { 
        center, 
        zoom, 
        centerChanged, 
        zoomChanged
      })
      
      isUpdatingRef.current = true
      if (onUpdate) onUpdate()
      
      // Use flyTo for smoother animation
      map.flyTo(center, zoom, {
        animate: true,
        duration: 0.5
      })
      
      // Update refs immediately to prevent duplicate updates
      lastCenterRef.current = centerKey
      lastZoomRef.current = zoom
      
      // Reset flag after animation
      setTimeout(() => {
        isUpdatingRef.current = false
      }, 600)
    }
  }, [center, zoom, map, skipUpdate, onUpdate])
  
  return null
}

export default function MapView() {
  const navigate = useNavigate()
  const location = useLocation()
  const [center, setCenter] = useState<[number, number]>([41.6, -72.7])
  const [zoom, setZoom] = useState(9)
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null)
  const [filterType, setFilterType] = useState<string | null>(null)
  const [filterParams, setFilterParams] = useState<any>({})
  const [showPropertyList, setShowPropertyList] = useState(false)
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [mapBounds, setMapBounds] = useState<{ north: number; south: number; east: number; west: number } | null>(null)
  const [isMapReady, setIsMapReady] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const mapUpdatingRef = useRef(false)
  const labelMarkersRef = useRef<L.Marker[]>([])
  const mapRef = useRef<L.Map | null>(null)
  const lastQueryTimeRef = useRef<number>(0)
  
  // Memoize the bounds change handler
  const handleBoundsChange = useCallback((bounds: { north: number; south: number; east: number; west: number }) => {
    setMapBounds(bounds)
  }, [])
  
  // Handle navigation from search bar
  useEffect(() => {
    if (location.state) {
      const { center: newCenter, zoom: newZoom, address, municipality } = location.state
      
      console.log('📍 Navigation state received:', { address, municipality, newCenter, newZoom })
      
      // If municipality provided, filter by it and show property list
      if (municipality) {
        console.log('📍 Setting municipality from location.state:', municipality)
        if (newCenter && Array.isArray(newCenter) && newCenter.length === 2) {
          setCenter([newCenter[0], newCenter[1]])
          setZoom(newZoom || 11)
        }
        setFilterParams({ municipality: municipality })
        setSearchQuery('') // Clear search query when using municipality
        setShowPropertyList(true)
        setFilterType(null) // Clear any filter type when searching by municipality
        setSelectedProperty(null) // Clear selected property when showing list
        
        // Clear location state after processing
        window.history.replaceState({}, document.title)
      }
      // If address provided, search for the property and center on its geometry
      else if (address) {
        // #region agent log
        fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:146',message:'Address path triggered',data:{address,newCenter,newZoom},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
        // #endregion
        console.log('🔍 Searching for address from dropdown:', address)
        // Clear search query and filters first
        setSearchQuery('')
        setFilterParams({})
        setFilterType(null)
        setShowPropertyList(false)
        // Don't clear selectedProperty here - wait until we find the new one
        
        propertyApi.search({ q: address, page_size: 20 }).then(result => {
          console.log('📦 Address search result:', result.total, 'properties found')
          if (result.properties && result.properties.length > 0) {
            // Find exact match first, or use first result
            const exactMatch = result.properties.find(p => 
              p.address?.toLowerCase() === address.toLowerCase() ||
              p.address?.toLowerCase().includes(address.toLowerCase())
            ) || result.properties[0]
            
            console.log('✅ Found property:', exactMatch.id, exactMatch.address)
            // Set the selected property - this will show it in the sidebar
            setSelectedProperty(exactMatch)
            console.log('📋 Selected property set, sidebar should show')
            
            // Center map on the property's actual geometry
            const geom = exactMatch.geometry?.geometry
            if (geom) {
              const centroid = getCentroid(geom)
              if (centroid) {
                console.log('📍 Centering map on property geometry:', centroid)
                // Force map update by using a new array reference
                const newCenter: [number, number] = [centroid[0], centroid[1]]
                setCenter(newCenter)
                setZoom(18)
                
                // Update map bounds to trigger bbox query for this area
                const bounds = {
                  north: centroid[0] + 0.005,  // ~500m radius
                  south: centroid[0] - 0.005,
                  east: centroid[1] + 0.005,
                  west: centroid[1] - 0.005
                }
                
                // Wait for map to update, then set bounds
                setTimeout(() => {
                  setMapBounds(bounds)
                  console.log('🗺️ Updated map bounds to load properties:', bounds)
                }, 500)
              } else if (newCenter && Array.isArray(newCenter) && newCenter.length === 2) {
                // Fallback to autocomplete center if geometry centroid fails
                console.log('⚠️ No centroid, using autocomplete center')
                setCenter([newCenter[0], newCenter[1]])
                setZoom(newZoom || 18)
              }
            } else if (newCenter && Array.isArray(newCenter) && newCenter.length === 2) {
              // Fallback to autocomplete center if no geometry
              console.log('⚠️ No geometry, using autocomplete center')
              setCenter([newCenter[0], newCenter[1]])
              setZoom(newZoom || 18)
            }
          } else if (newCenter && Array.isArray(newCenter) && newCenter.length === 2) {
            // No property found, use autocomplete center
            console.log('⚠️ No property found, using autocomplete center')
            setCenter([newCenter[0], newCenter[1]])
            setZoom(newZoom || 18)
          }
        }).catch(error => {
          console.error('❌ Error searching for address:', error)
          // Fallback to autocomplete center on error
          if (newCenter && Array.isArray(newCenter) && newCenter.length === 2) {
            setCenter([newCenter[0], newCenter[1]])
            setZoom(newZoom || 18)
          }
        })
        
        // Clear location state after processing
        window.history.replaceState({}, document.title)
      }
      // If municipality provided, filter by it and show property list
      else if (municipality) {
        console.log('📍 Setting municipality from location.state:', municipality)
        if (newCenter && Array.isArray(newCenter) && newCenter.length === 2) {
          setCenter([newCenter[0], newCenter[1]])
          setZoom(newZoom || 11)
        }
        setFilterParams({ municipality: municipality })
        setSearchQuery('') // Clear search query when using municipality
        setShowPropertyList(true)
        setFilterType(null) // Clear any filter type when searching by municipality
      }
      // If just center/zoom provided (e.g., state selection)
      else if (newCenter && Array.isArray(newCenter) && newCenter.length === 2) {
        setCenter([newCenter[0], newCenter[1]])
        setZoom(newZoom || 8)
        // Clear location state after processing
        window.history.replaceState({}, document.title)
      }
    }
  }, [location.state])

  // Get bounding box for current viewport - use actual map bounds if available
  const bbox = useMemo(() => {
    if (mapBounds) {
      // Use actual map bounds: minLng, minLat, maxLng, maxLat
      return `${mapBounds.west},${mapBounds.south},${mapBounds.east},${mapBounds.north}`
    }
    // Fallback to approximate bbox based on center and zoom
    const latRange = 180 / Math.pow(2, zoom)
    const lngRange = 360 / Math.pow(2, zoom)
    return `${center[1] - lngRange},${center[0] - latRange},${center[1] + lngRange},${center[0] + latRange}`
  }, [mapBounds, center, zoom])

  // Fetch properties based on filter or search
  // Only use bbox when NOT searching by municipality or query
  const useBbox = !filterParams.municipality && (!searchQuery || searchQuery.trim().length === 0) && !filterType
  
  // Create a stable bbox string for the query key
  const bboxKey = useMemo(() => {
    if (!useBbox || !mapBounds) return null
    return `${mapBounds.west.toFixed(2)},${mapBounds.south.toFixed(2)},${mapBounds.east.toFixed(2)},${mapBounds.north.toFixed(2)}`
  }, [useBbox, mapBounds])
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['properties', filterType, filterParams, bboxKey, searchQuery],
    enabled: true,
    staleTime: 10000,
    refetchOnWindowFocus: false,
      queryFn: async () => {
        let result
        
        // Priority 1: Municipality filter
        if (filterParams.municipality) {
          result = await propertyApi.search({ municipality: filterParams.municipality, page_size: 100 })
          setShowPropertyList(true)
        } 
        // Priority 2: Search query
        else if (searchQuery && searchQuery.trim().length > 0) {
          result = await propertyApi.search({ q: searchQuery.trim(), page_size: 100 })
          setShowPropertyList(true)
        } 
        // Priority 3: Filter type
        else if (filterType) {
          switch (filterType) {
            case 'high-equity':
              result = await propertyApi.getHighEquity({ ...filterParams, page_size: 500 })
              break
            case 'vacant':
              result = await propertyApi.getVacant({ ...filterParams, page_size: 500 })
              break
            case 'absentee-owners':
              result = await propertyApi.getAbsenteeOwners({ ...filterParams, page_size: 500 })
              break
            case 'recently-sold':
              result = await propertyApi.getRecentlySold({ ...filterParams, page_size: 500 })
              break
            case 'low-equity':
              result = await propertyApi.getLowEquity({ ...filterParams, page_size: 500 })
              break
            default:
              result = await propertyApi.search({ bbox, page_size: 500 })
          }
        } else {
          // Use bbox to show properties in current viewport
          result = await propertyApi.search({ bbox, page_size: 500 })
        }
        
        // Ensure result structure
        if (!result) {
          return { properties: [], total: 0, page: 1, page_size: 500 }
        }
        if (!result.properties) {
          result.properties = []
        }
        if (result.total === undefined) {
          result.total = result.properties.length
        }
        
        // Track analytics (non-blocking)
        analyticsApi.trackSearch({
          filter_type: filterType || undefined,
          result_count: result.total || 0,
        }).catch(() => {})
        
        return result
    },
  })

  // Ensure selected property is included in properties array
  const properties = useMemo(() => {
    const baseProperties = data?.properties || []
    
    // If we have a selected property, make sure it's in the list
    if (selectedProperty) {
      const isInList = baseProperties.some(p => p.id === selectedProperty.id)
      if (!isInList) {
        // Add selected property to the list so it shows on the map
        return [selectedProperty, ...baseProperties]
      }
    }
    
    return baseProperties
  }, [data?.properties, selectedProperty])

  // Extract street number from address
  const getStreetNumber = (address: string | null | undefined): string | null => {
    if (!address) return null
    // Match numbers at the start of the address (e.g., "768 MAPLE ST" -> "768")
    const match = address.trim().match(/^(\d+)/)
    return match ? match[1] : null
  }

  // Create GeoJSON from properties
  const geoJsonData = useMemo(() => {
    if (!properties || properties.length === 0) {
      return { type: 'FeatureCollection' as const, features: [] }
    }
    
    const features = properties.map((prop) => {
      if (!prop.geometry?.geometry) {
        return null
      }
      return {
        type: 'Feature' as const,
        geometry: prop.geometry.geometry,
        properties: {
          id: prop.id,
          parcel_id: prop.parcel_id,
          address: prop.address,
          street_number: getStreetNumber(prop.address),
          assessed_value: prop.assessed_value,
          owner_name: prop.owner_name,
        },
      }
    }).filter((f): f is NonNullable<typeof f> => f !== null)
    
    return {
      type: 'FeatureCollection' as const,
      features,
    }
  }, [properties])

  // Calculate popup center for selected property
  const selectedPropertyMarker = useMemo(() => {
    if (!selectedProperty) return null
    
    const geom = selectedProperty.geometry?.geometry
    let popupCenter: [number, number] = center
    
    if (geom?.type === 'Polygon' && geom.coordinates?.[0]?.[0]) {
      const coords = geom.coordinates[0]
      const [lng, lat] = coords.reduce(
        (acc: [number, number], coord: number[]) => [acc[0] + coord[0], acc[1] + coord[1]],
        [0, 0]
      )
      popupCenter = [lat / coords.length, lng / coords.length]
    } else if (geom?.type === 'Point' && geom.coordinates) {
      popupCenter = [geom.coordinates[1], geom.coordinates[0]]
    }
    
    return (
      <Marker key={`selected-${selectedProperty.id}`} position={popupCenter}>
        <Popup>
          <PropertyCard
            property={selectedProperty}
            onClick={() => navigate(`/property/${selectedProperty.id}`)}
          />
        </Popup>
      </Marker>
    )
  }, [selectedProperty, center, navigate])

  const handlePropertyClick = useCallback((property: Property) => {
    console.log('🖱️ Property clicked:', property.id, property.address)
    setSelectedProperty(property)
    // Hide property list when clicking on a specific property
    setShowPropertyList(false)
    setSearchQuery('')
    
    // Center map on clicked property
    const geom = property.geometry?.geometry
    if (geom) {
      const centroid = getCentroid(geom)
      if (centroid) {
        console.log('📍 Centering on clicked property:', centroid)
        setCenter(centroid)
        setZoom(18)
      } else if (geom.type === 'Polygon' && geom.coordinates?.[0]?.[0]) {
        const coords = geom.coordinates[0]
        const [lng, lat] = coords.reduce(
          (acc: [number, number], coord: number[]) => [acc[0] + coord[0], acc[1] + coord[1]],
          [0, 0]
        )
        setCenter([lat / coords.length, lng / coords.length])
        setZoom(18)
      } else if (geom.type === 'MultiPolygon' && geom.coordinates?.[0]?.[0]?.[0]) {
        const coords = geom.coordinates[0][0]
        const [lng, lat] = coords.reduce(
          (acc: [number, number], coord: number[]) => [acc[0] + coord[0], acc[1] + coord[1]],
          [0, 0]
        )
        setCenter([lat / coords.length, lng / coords.length])
        setZoom(18)
      }
    }
  }, [setCenter, setZoom])

  const handleFilterChange = useCallback((filter: string, value: any) => {
    // Handle filter changes from TopFilterBar
    if (filter === 'leadTypes') {
      // Map lead types to filter types
      const leadTypeMap: Record<string, string> = {
        'High Equity': 'high-equity',
        'Vacant Properties': 'vacant',
        'Absentee Owners': 'absentee-owners',
        'Recently Sold': 'recently-sold',
        'Low Equity': 'low-equity'
      }
      const filterType = leadTypeMap[value]
      if (filterType) {
        setFilterType(filterType)
        const defaultParams = filterType === 'high-equity' ? { min_equity: 50000 } :
                             filterType === 'recently-sold' ? { days: 365 } :
                             filterType === 'low-equity' ? { max_equity: 10000 } : {}
        setFilterParams(defaultParams)
      }
    } else {
      // Handle other filters
      setFilterParams((prev: any) => ({ ...prev, [filter]: value }))
    }
  }, [])

  // Style for GeoJSON features
  const geoJsonStyle = useCallback(() => {
    return {
      fillColor: '#3b82f6',
      fillOpacity: 0.3,
      color: '#1e40af',
      weight: 1,
    }
  }, [])

  // Calculate centroid of a geometry
  const getCentroid = (geometry: any): [number, number] | null => {
    if (!geometry) return null
    
    if (geometry.type === 'Polygon' && geometry.coordinates?.[0]?.[0]) {
      const coords = geometry.coordinates[0]
      const [lng, lat] = coords.reduce(
        (acc: [number, number], coord: number[]) => [acc[0] + coord[0], acc[1] + coord[1]],
        [0, 0]
      )
      return [lat / coords.length, lng / coords.length]
    } else if (geometry.type === 'MultiPolygon' && geometry.coordinates?.[0]?.[0]?.[0]) {
      const coords = geometry.coordinates[0][0]
      const [lng, lat] = coords.reduce(
        (acc: [number, number], coord: number[]) => [acc[0] + coord[0], acc[1] + coord[1]],
        [0, 0]
      )
      return [lat / coords.length, lng / coords.length]
    }
    return null
  }

  // Handle GeoJSON click and add labels
  const onEachFeature = useCallback((feature: any, layer: L.Layer) => {
    const featureId = feature.properties?.id
    if (!featureId) {
      console.warn('Feature missing id:', feature)
      return
    }
    
    // Find property by ID - use current properties from data
    const property = (data?.properties || []).find(p => p.id === featureId)
    
    if (property) {
      // Address number labels are now handled separately via addressNumberMarkers
      
      layer.on({
        click: (e: L.LeafletMouseEvent) => {
          e.originalEvent.stopPropagation()
          console.log('Map click - Feature ID:', featureId, 'Property found:', property.id, property.address)
          handlePropertyClick(property)
          
          // Center map on clicked property
          const geom = property.geometry?.geometry
          if (geom) {
            const centroid = getCentroid(geom)
            if (centroid) {
              setCenter(centroid)
              setZoom(18)
            }
          }
        },
      })
      
      // Add hover effect
      layer.on({
        mouseover: (e: L.LeafletMouseEvent) => {
          const layer = e.target
          layer.setStyle({
            fillColor: '#667eea',
            fillOpacity: 0.5,
            color: '#667eea',
            weight: 2,
          })
        },
        mouseout: (e: L.LeafletMouseEvent) => {
          const layer = e.target
          layer.setStyle(geoJsonStyle())
        },
      })
    } else {
      console.warn('Property not found for feature ID:', featureId, 'Available IDs:', (data?.properties || []).map(p => p.id).slice(0, 10))
    }
  }, [data?.properties, handlePropertyClick, geoJsonStyle, setCenter, setZoom])

  // Create markers for address numbers - only show at street level zoom (15+)
  const addressNumberMarkers = useMemo(() => {
    // Only show address numbers when zoomed in to street level
    if (zoom < 15 || !properties || properties.length === 0) return []
    
    const markers: JSX.Element[] = []
    
    properties.forEach((property) => {
      const streetNumber = getStreetNumber(property.address)
      if (streetNumber && property.geometry?.geometry) {
        const centroid = getCentroid(property.geometry.geometry)
        if (centroid) {
          markers.push(
            <Marker
              key={`label-${property.id}`}
              position={centroid}
              icon={L.divIcon({
                className: 'property-number-label',
                html: `<div class="address-number">${streetNumber}</div>`,
                iconSize: [50, 25],
                iconAnchor: [25, 12],
              })}
              interactive={false}
              zIndexOffset={1000}
            />
          )
        }
      }
    })
    
    return markers
  }, [properties, zoom])

  // Determine if we should show property list or selected property sidebar
  const shouldShowList = showPropertyList && (filterParams.municipality || searchQuery || filterType || data?.properties?.length > 0)
  const shouldShowSelectedProperty = selectedProperty !== null && !shouldShowList
  const propertiesToShow = data?.properties || []
  const hasSidebarContent = shouldShowList || shouldShowSelectedProperty
  const isSidebarVisible = hasSidebarContent && !sidebarCollapsed
  const hasProperties = propertiesToShow.length > 0

  // Debug: Log when data changes
  useEffect(() => {
    console.log('MapView state:', {
      filterParams,
      searchQuery,
      filterType,
      showPropertyList,
      shouldShowList,
      dataTotal: data?.total,
      propertiesCount: propertiesToShow.length,
      isLoading
    })
  }, [filterParams, searchQuery, filterType, showPropertyList, shouldShowList, data?.total, propertiesToShow.length, isLoading])

  return (
    <div className={`map-view ${isSidebarVisible ? 'with-sidebar' : ''}`}>
      <TopFilterBar 
        onFilterChange={handleFilterChange}
        onSearchChange={(query) => {
          console.log('🔍 SearchBar query changed:', query)
          // When user types in search bar, update searchQuery
          if (query && query.trim().length > 0) {
            console.log('✅ Setting searchQuery to:', query.trim())
            setSearchQuery(query.trim())
            setShowPropertyList(true)
            // Clear municipality filter when typing
            setFilterParams({})
            setFilterType(null)
          } else {
            console.log('❌ Clearing searchQuery')
            setSearchQuery('')
            setShowPropertyList(false)
          }
        }}
      />
      
      {/* Selected Property Sidebar (shown when clicking on map) */}
      {shouldShowSelectedProperty && !shouldShowList && (
        <div className={`property-list-sidebar ${sidebarCollapsed ? 'collapsed' : ''}`} style={sidebarCollapsed ? { display: 'none' } : undefined}>
          <div className="property-list-header">
            <div className="property-list-title">
              <h2>Property Details</h2>
            </div>
            <div className="property-list-actions">
              <button
                className="toggle-sidebar-btn"
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                {sidebarCollapsed ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
              </button>
              <button
                className="close-sidebar-btn"
                onClick={() => {
                  setSelectedProperty(null)
                  setSidebarCollapsed(false)
                }}
                aria-label="Close sidebar"
              >
                <X size={20} />
              </button>
            </div>
          </div>
          
          <div className="property-list-content">
            <div className="property-list-scroll">
              <div className="property-list-item selected">
                <PropertyCard
                  property={selectedProperty}
                  onClick={() => navigate(`/property/${selectedProperty.id}`)}
                />
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Property List Sidebar (shown when searching/filtering or when there are properties) */}
      {shouldShowList && (
        <div className={`property-list-sidebar ${sidebarCollapsed ? 'collapsed' : ''}`} style={sidebarCollapsed ? { display: 'none' } : undefined}>
          <div className="property-list-header">
            <div className="property-list-title">
              <h2>
                {data?.total ? `Show 1 - ${Math.min((data as any).page_size || data.properties?.length || 100, data.total).toLocaleString()} of ${data.total.toLocaleString()} Results` : 'Properties'}
                {filterParams.municipality && (
                  <span className="location-badge">{filterParams.municipality}</span>
                )}
              </h2>
            </div>
            <div className="property-list-actions">
              {!sidebarCollapsed && data && data.total > 0 && (
                <ExportButton
                  filterType={filterType || undefined}
                  filterParams={filterParams}
                  resultCount={data.total}
                />
              )}
              <button
                className="toggle-sidebar-btn"
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                {sidebarCollapsed ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
              </button>
              <button
                className="close-sidebar-btn"
                onClick={() => {
                  setShowPropertyList(false)
                  setSearchQuery('')
                  setFilterParams({})
                  setSidebarCollapsed(false)
                }}
                aria-label="Close sidebar"
              >
                <X size={20} />
              </button>
            </div>
          </div>
          
          <div className="property-list-content">
            {error ? (
              <div className="property-list-error">
                <p>Error loading properties. Please try again.</p>
                <p style={{ fontSize: '0.9rem', color: '#666', marginTop: '0.5rem' }}>
                  {error instanceof Error ? error.message : 'Unknown error'}
                </p>
              </div>
            ) : isLoading ? (
              <div className="property-list-loading">
                <div className="spinner" />
                <p>Loading properties...</p>
              </div>
            ) : propertiesToShow.length === 0 ? (
              <div className="property-list-empty">
                <p>No properties found</p>
              </div>
            ) : (
              <div className="property-list-scroll">
                {propertiesToShow.map((property) => (
                  <div
                    key={property.id}
                    className={`property-list-item ${
                      selectedProperty?.id === property.id ? 'selected' : ''
                    }`}
                    onClick={() => {
                      setSelectedProperty(property)
                      // Center map on property
                      const geom = property.geometry?.geometry
                      if (geom?.type === 'Polygon' && geom.coordinates?.[0]?.[0]) {
                        const coords = geom.coordinates[0]
                        const [lng, lat] = coords.reduce(
                          (acc: [number, number], coord: number[]) => [acc[0] + coord[0], acc[1] + coord[1]],
                          [0, 0]
                        )
                        setCenter([lat / coords.length, lng / coords.length])
                        setZoom(18)
                      } else if (geom?.type === 'MultiPolygon' && geom.coordinates?.[0]?.[0]?.[0]) {
                        const coords = geom.coordinates[0][0]
                        const [lng, lat] = coords.reduce(
                          (acc: [number, number], coord: number[]) => [acc[0] + coord[0], acc[1] + coord[1]],
                          [0, 0]
                        )
                        setCenter([lat / coords.length, lng / coords.length])
                        setZoom(18)
                      }
                    }}
                  >
                    <PropertyCard
                      property={property}
                      onClick={() => navigate(`/property/${property.id}`)}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="map-container-wrapper">
        <MapContainer
          center={center}
          zoom={zoom}
          style={{ width: '100%', height: '100%' }}
          whenReady={(map) => {
            const leafletMap = map.target
            mapRef.current = leafletMap // Store map reference
            
            // Mark map as ready immediately so bbox queries can work
            // Also set initial bounds
            const initialBounds = leafletMap.getBounds()
            setMapBounds({
              north: initialBounds.getNorth(),
              south: initialBounds.getSouth(),
              east: initialBounds.getEast(),
              west: initialBounds.getWest(),
            })
            setIsMapReady(true)
            
            // Only listen to user-initiated moves, not programmatic ones
            let isUserMove = true
            
            leafletMap.on('movestart', () => {
              isUserMove = !mapUpdatingRef.current
            })
            
            leafletMap.on('moveend', () => {
              if (isUserMove && !mapUpdatingRef.current) {
                const center = leafletMap.getCenter()
                setCenter([center.lat, center.lng])
                setZoom(leafletMap.getZoom())
              }
              mapUpdatingRef.current = false
              isUserMove = true
            })
            
            leafletMap.on('zoomend', () => {
              if (isUserMove && !mapUpdatingRef.current) {
                const zoom = leafletMap.getZoom()
                setZoom(zoom)
                // Bounds will be updated by MapBoundsUpdater component
              }
            })
          }}
        >
        <MapUpdater 
          center={center} 
          zoom={zoom} 
          skipUpdate={false}
          onUpdate={() => { mapUpdatingRef.current = true }}
        />
        <MapBoundsUpdater 
          onBoundsChange={handleBoundsChange}
        />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        
        {geoJsonData.features.length > 0 && (
          <>
            <GeoJSON
              key={`geojson-${geoJsonData.features.length}`}
              data={geoJsonData as any}
              style={geoJsonStyle}
              onEachFeature={onEachFeature}
            />
            <LayerGroup>
              {addressNumberMarkers}
            </LayerGroup>
          </>
        )}

        {selectedPropertyMarker}
        </MapContainer>
      </div>

      {isLoading && !error && (
        <div className="loading-overlay">
          <div className="spinner" />
          <p>Loading properties...</p>
        </div>
      )}

      {error && (
        <div className="loading-overlay" style={{ background: '#fee2e2', color: '#dc2626' }}>
          <p>⚠️ Error loading properties. Check console for details.</p>
        </div>
      )}

      {/* Sidebar toggle button - show when collapsed or when there are properties but sidebar is hidden */}
      {((hasSidebarContent && sidebarCollapsed) || (hasProperties && !hasSidebarContent)) && (
        <button
          className="sidebar-toggle-button"
          onClick={() => {
            if (hasSidebarContent && sidebarCollapsed) {
              // Expand collapsed sidebar
              setSidebarCollapsed(false)
            } else if (hasProperties && !hasSidebarContent) {
              // Open sidebar to show properties from map view
              setShowPropertyList(true)
            }
          }}
          aria-label="Open sidebar"
          title="Open sidebar to view properties"
        >
          <PanelRight size={20} />
          {hasProperties && !hasSidebarContent && (
            <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem' }}>
              {data?.total?.toLocaleString() || propertiesToShow.length} properties
            </span>
          )}
        </button>
      )}

      <div className="map-controls-bottom">
        {data && !error && (
          <div className="results-count">
            {data.total.toLocaleString()} properties found
          </div>
        )}
        {data && data.total > 0 && (
          <ExportButton
            filterType={filterType}
            filterParams={filterParams}
            resultCount={data.total}
          />
        )}
      </div>
    </div>
  )
}
