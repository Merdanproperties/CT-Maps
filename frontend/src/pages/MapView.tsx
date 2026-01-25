import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, useMap, useMapEvents, LayerGroup } from 'react-leaflet'
import { MapBoundsUpdater } from './MapBoundsUpdater'
import { propertyApi, Property, analyticsApi } from '../api/client'
import { usePropertyQuery } from '../hooks/usePropertyQuery'
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

// Component to initialize map reference and set up event listeners
function MapInitializer({ 
  mapRef, 
  setMapBounds, 
  setIsMapReady, 
  setCenter, 
  setZoom, 
  mapUpdatingRef 
}: { 
  mapRef: React.MutableRefObject<L.Map | null>,
  setMapBounds: (bounds: { north: number; south: number; east: number; west: number }) => void,
  setIsMapReady: (ready: boolean) => void,
  setCenter: (center: [number, number]) => void,
  setZoom: (zoom: number) => void,
  mapUpdatingRef: React.MutableRefObject<boolean>
}) {
  const map = useMap()
  
  useEffect(() => {
    mapRef.current = map
    
    // Mark map as ready immediately so bbox queries can work
    // Also set initial bounds
    const initialBounds = map.getBounds()
    setMapBounds({
      north: initialBounds.getNorth(),
      south: initialBounds.getSouth(),
      east: initialBounds.getEast(),
      west: initialBounds.getWest(),
    })
    setIsMapReady(true)
    
    // Only listen to user-initiated moves, not programmatic ones
    let isUserMove = true
    
    map.on('movestart', () => {
      isUserMove = !mapUpdatingRef.current
    })
    
    map.on('moveend', () => {
      if (isUserMove && !mapUpdatingRef.current) {
        const center = map.getCenter()
        setCenter([center.lat, center.lng])
        setZoom(map.getZoom())
      }
      mapUpdatingRef.current = false
      isUserMove = true
    })
    
    map.on('zoomend', () => {
      if (isUserMove && !mapUpdatingRef.current) {
        const zoom = map.getZoom()
        setZoom(zoom)
      }
    })
  }, [map, mapRef, setMapBounds, setIsMapReady, setCenter, setZoom, mapUpdatingRef])
  
  return null
}

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
        fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:191',message:'Address path triggered',data:{address,newCenter,newZoom,centerType:typeof newCenter,centerIsArray:Array.isArray(newCenter)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
        // #endregion
        console.log('🔍 Searching for address from dropdown:', address)
        // Clear search query and filters first
        setSearchQuery('')
        setFilterParams({})
        setFilterType(null)
        setShowPropertyList(false)
        // Don't clear selectedProperty here - wait until we find the new one
        
        // #region agent log
        fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:203',message:'Search API call started',data:{searchAddress:address,autocompleteCenter:newCenter},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
        // #endregion
        propertyApi.search({ q: address, page_size: 50 }).then(result => {
          // #region agent log
          fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:203',message:'Search API result',data:{total:result.total,propertiesCount:result.properties?.length,firstPropertyId:result.properties?.[0]?.id,firstPropertyAddress:result.properties?.[0]?.address,firstPropertyMunicipality:result.properties?.[0]?.municipality,allAddresses:result.properties?.map(p=>p.address),allMunicipalities:result.properties?.map(p=>p.municipality)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
          // #endregion
          console.log('📦 Address search result:', result.total, 'properties found')
            if (result.properties && result.properties.length > 0) {
            // Normalize address for better matching (remove common suffixes, case-insensitive)
            const normalizeForMatch = (addr: string) => {
              if (!addr) return ''
              return addr.toLowerCase()
                .replace(/\s+/g, ' ')
                .replace(/\b(street|st|avenue|ave|road|rd|drive|dr|lane|ln|court|ct|place|pl|boulevard|blvd|parkway|pkwy)\b/gi, '')
                .trim()
            }
            
            const searchNormalized = normalizeForMatch(address)
            
            // Find exact match first, then partial match, then use first result
            const exactMatch = result.properties.find(p => {
              const propNormalized = normalizeForMatch(p.address || '')
              return propNormalized === searchNormalized || 
                     p.address?.toLowerCase() === address.toLowerCase() ||
                     p.address?.toLowerCase().includes(address.toLowerCase()) ||
                     address.toLowerCase().includes(p.address?.toLowerCase() || '')
            }) || result.properties[0]
            
            // #region agent log
            fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:207',message:'Property match selected',data:{exactMatchId:exactMatch.id,exactMatchAddress:exactMatch.address,searchAddress:address,isExactMatch:exactMatch.address?.toLowerCase()===address.toLowerCase(),hasGeometry:!!exactMatch.geometry?.geometry,geometryType:exactMatch.geometry?.geometry?.type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
            // #endregion
            console.log('✅ Found property:', exactMatch.id, exactMatch.address)
            // Set the selected property - this will show it in the sidebar
            setSelectedProperty(exactMatch)
            console.log('📋 Selected property set, sidebar should show')
            
            // Center map on the property's actual geometry
            const geom = exactMatch.geometry?.geometry
            // #region agent log
            fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:218',message:'Before getCentroid',data:{hasGeom:!!geom,geomType:geom?.type,firstCoord:geom?.coordinates?.[0]?.[0],autocompleteCenter:newCenter},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
            // #endregion
            if (geom) {
              const centroid = getCentroid(geom)
              // #region agent log
              fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:220',message:'After getCentroid',data:{centroid,autocompleteCenter:newCenter,centroidLat:centroid?.[0],centroidLng:centroid?.[1],autocompleteLat:newCenter?.[0],autocompleteLng:newCenter?.[1]},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
              // #endregion
              if (centroid) {
                console.log('📍 Centering map on property geometry:', centroid)
                // Force map update by using a new array reference
                const newCenter: [number, number] = [centroid[0], centroid[1]]
                // #region agent log
                fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:224',message:'Setting map center from centroid',data:{newCenter,centroid,zoom:18},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
                // #endregion
                setCenter(newCenter)
                setZoom(18)
                
                // Update map bounds to trigger bbox query for this area
                const bounds = {
                  north: centroid[0] + 0.005,  // ~500m radius
                  south: centroid[0] - 0.005,
                  east: centroid[1] + 0.005,
                  west: centroid[1] - 0.005
                }
                // #region agent log
                fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:229',message:'Map bounds calculated',data:{bounds,centroid},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
                // #endregion
                
                // Wait for map to update, then set bounds
                setTimeout(() => {
                  setMapBounds(bounds)
                  console.log('🗺️ Updated map bounds to load properties:', bounds)
                }, 500)
              } else if (newCenter && Array.isArray(newCenter) && newCenter.length === 2) {
                // Fallback to autocomplete center if geometry centroid fails
                // #region agent log
                fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:241',message:'Fallback to autocomplete center (no centroid)',data:{newCenter,newZoom},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
                // #endregion
                console.log('⚠️ No centroid, using autocomplete center')
                setCenter([newCenter[0], newCenter[1]])
                setZoom(newZoom || 18)
              }
            } else if (newCenter && Array.isArray(newCenter) && newCenter.length === 2) {
              // Fallback to autocomplete center if no geometry
              // #region agent log
              fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:247',message:'Fallback to autocomplete center (no geometry)',data:{newCenter,newZoom},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
              // #endregion
              console.log('⚠️ No geometry, using autocomplete center')
              setCenter([newCenter[0], newCenter[1]])
              setZoom(newZoom || 18)
            }
          } else if (newCenter && Array.isArray(newCenter) && newCenter.length === 2) {
            // No property found, use autocomplete center but log warning
            // #region agent log
            fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:253',message:'Fallback to autocomplete center (no property found)',data:{newCenter,newZoom,searchAddress:address},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
            // #endregion
            console.warn('⚠️ No property found for address:', address, 'using autocomplete center:', newCenter)
            // Verify autocomplete center is valid (within CT bounds approximately)
            if (newCenter[0] >= 40.5 && newCenter[0] <= 42.0 && newCenter[1] >= -74.0 && newCenter[1] <= -71.5) {
              setCenter([newCenter[0], newCenter[1]])
              setZoom(newZoom || 18)
            } else {
              console.error('❌ Invalid autocomplete center coordinates:', newCenter)
              // Fallback to CT center if autocomplete center is invalid
              setCenter([41.6, -72.7])
              setZoom(9)
            }
          }
        }).catch(error => {
          console.error('❌ Error searching for address:', error)
          // #region agent log
          fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:259',message:'Search API error',data:{error:error?.message,searchAddress:address,newCenter},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
          // #endregion
          // Fallback to autocomplete center on error, but validate it
          if (newCenter && Array.isArray(newCenter) && newCenter.length === 2) {
            if (newCenter[0] >= 40.5 && newCenter[0] <= 42.0 && newCenter[1] >= -74.0 && newCenter[1] <= -71.5) {
              setCenter([newCenter[0], newCenter[1]])
              setZoom(newZoom || 18)
            } else {
              console.error('❌ Invalid autocomplete center, using CT center')
              setCenter([41.6, -72.7])
              setZoom(9)
            }
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
      const bboxVal = `${mapBounds.west},${mapBounds.south},${mapBounds.east},${mapBounds.north}`
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:237',message:'bbox calculated from mapBounds',data:{bbox:bboxVal,mapBounds},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      return bboxVal
    }
    // Fallback to approximate bbox based on center and zoom
    const latRange = 180 / Math.pow(2, zoom)
    const lngRange = 360 / Math.pow(2, zoom)
    const bboxVal = `${center[1] - lngRange},${center[0] - latRange},${center[1] + lngRange},${center[0] + latRange}`
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:242',message:'bbox calculated from fallback',data:{bbox:bboxVal,center,zoom,mapBounds},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
    // #endregion
    return bboxVal
  }, [mapBounds, center, zoom])

  // Use the new simplified property query hook
  const { data, isLoading, error, status, fetchStatus } = usePropertyQuery({
    filterType,
    filterParams,
    searchQuery,
    bbox,
    mapBounds,
    center,
    zoom,
  })

  // Show property list when we have search criteria
  useEffect(() => {
    if (filterParams.municipality || (searchQuery && searchQuery.trim().length > 0) || filterType) {
        setShowPropertyList(true)
      } 
  }, [filterParams.municipality, searchQuery, filterType])

  // Track analytics when data changes
  useEffect(() => {
    if (data && data.total > 0) {
           analyticsApi.trackSearch({
             filter_type: filterType || undefined,
        result_count: data.total || 0,
           }).catch(() => {})
    }
  }, [data, filterType])

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
    // If value is null, clear the filter
    if (value === null || value === 'All' || value === '') {
      if (filter === 'leadTypes') {
        setFilterType(null)
        setFilterParams((prev: any) => {
          const newParams = { ...prev }
          delete newParams.min_equity
          delete newParams.max_equity
          delete newParams.days
          return newParams
        })
      } else if (filter === 'price') {
        setFilterParams((prev: any) => {
          const newParams = { ...prev }
          delete newParams.min_value
          delete newParams.max_value
          return newParams
        })
      } else if (filter === 'lotSize') {
        setFilterParams((prev: any) => {
          const newParams = { ...prev }
          delete newParams.min_lot_size
          delete newParams.max_lot_size
          return newParams
        })
      } else if (filter === 'saleDate') {
        setFilterType(null)
        setFilterParams((prev: any) => {
          const newParams = { ...prev }
          delete newParams.days
          return newParams
        })
      } else if (filter === 'propertyTypes') {
        setFilterParams((prev: any) => {
          const newParams = { ...prev }
          delete newParams.property_type
          return newParams
        })
      }
      return
    }

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
    } else if (filter === 'price') {
      // Map price ranges to assessed value ranges
      const priceMap: Record<string, { min_value?: number; max_value?: number }> = {
        'Under $50K': { max_value: 50000 },
        '$50K - $100K': { min_value: 50000, max_value: 100000 },
        '$100K - $200K': { min_value: 100000, max_value: 200000 },
        '$200K - $500K': { min_value: 200000, max_value: 500000 },
        '$500K - $1M': { min_value: 500000, max_value: 1000000 },
        '$1M+': { min_value: 1000000 }
      }
      const priceParams = priceMap[value] || {}
      if (Object.keys(priceParams).length > 0) {
        setFilterParams((prev: any) => {
          const newParams = { ...prev }
          // Clear other price-related filters
          delete newParams.min_value
          delete newParams.max_value
          return { ...newParams, ...priceParams }
        })
        setFilterType(null) // Clear lead type filter when using price
      }
    } else if (filter === 'lotSize') {
      // Map lot size ranges to lot_size_sqft ranges
      const lotSizeMap: Record<string, { min_lot_size?: number; max_lot_size?: number }> = {
        'Under 5,000 sqft': { max_lot_size: 5000 },
        '5,000 - 10,000 sqft': { min_lot_size: 5000, max_lot_size: 10000 },
        '10,000 - 20,000 sqft': { min_lot_size: 10000, max_lot_size: 20000 },
        '20,000 - 43,560 sqft (1 acre)': { min_lot_size: 20000, max_lot_size: 43560 },
        '1+ acres': { min_lot_size: 43560 }
      }
      const lotSizeParams = lotSizeMap[value] || {}
      if (Object.keys(lotSizeParams).length > 0) {
        setFilterParams((prev: any) => {
          const newParams = { ...prev }
          // Clear other lot size filters
          delete newParams.min_lot_size
          delete newParams.max_lot_size
          return { ...newParams, ...lotSizeParams }
        })
        setFilterType(null) // Clear lead type filter when using lot size
      }
    } else if (filter === 'saleDate') {
      // Map sale date ranges to days since sale
      const saleDateMap: Record<string, { days?: number }> = {
        'Last 30 days': { days: 30 },
        'Last 90 days': { days: 90 },
        'Last 6 months': { days: 180 },
        'Last year': { days: 365 },
        'Last 2 years': { days: 730 },
        'Last 5 years': { days: 1825 }
      }
      const saleDateParams = saleDateMap[value] || {}
      if (saleDateParams.days) {
        setFilterType('recently-sold')
        setFilterParams((prev: any) => {
          const newParams = { ...prev }
          delete newParams.days
          return { ...newParams, days: saleDateParams.days }
        })
      }
    } else if (filter === 'propertyTypes') {
      // Map property type selections to property_type filter
      const propertyTypeMap: Record<string, string> = {
        'Residential': 'Residential',
        'Commercial': 'Commercial',
        'Industrial': 'Industrial',
        'Vacant Land': 'Vacant Land',
        'Mixed Use': 'Mixed Use'
      }
      const propertyType = propertyTypeMap[value]
      if (propertyType) {
        setFilterParams((prev: any) => {
          const newParams = { ...prev }
          delete newParams.property_type
          return { ...newParams, property_type: propertyType }
        })
        setFilterType(null) // Clear lead type filter when using property type
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
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:616',message:'getCentroid entry',data:{hasGeometry:!!geometry,geometryType:geometry?.type,hasCoordinates:!!geometry?.coordinates,firstCoord:geometry?.coordinates?.[0]?.[0]},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    if (!geometry) return null
    
    if (geometry.type === 'Polygon' && geometry.coordinates?.[0]?.[0]) {
      const coords = geometry.coordinates[0]
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:620',message:'Polygon centroid calc',data:{coordsLength:coords.length,firstCoord:coords[0],secondCoord:coords[1],coordStructure:Array.isArray(coords[0])?coords[0].length:'not array'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      const [lng, lat] = coords.reduce(
        (acc: [number, number], coord: number[]) => [acc[0] + coord[0], acc[1] + coord[1]],
        [0, 0]
      )
      const result: [number, number] = [lat / coords.length, lng / coords.length]
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:625',message:'Polygon centroid result',data:{result,sumLng:lng,sumLat:lat,coordsCount:coords.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      return result
    } else if (geometry.type === 'MultiPolygon' && geometry.coordinates?.[0]?.[0]?.[0]) {
      const coords = geometry.coordinates[0][0]
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:627',message:'MultiPolygon centroid calc',data:{coordsLength:coords.length,firstCoord:coords[0],secondCoord:coords[1]},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      const [lng, lat] = coords.reduce(
        (acc: [number, number], coord: number[]) => [acc[0] + coord[0], acc[1] + coord[1]],
        [0, 0]
      )
      const result: [number, number] = [lat / coords.length, lng / coords.length]
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:632',message:'MultiPolygon centroid result',data:{result,sumLng:lng,sumLat:lat,coordsCount:coords.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      return result
    }
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'MapView.tsx:634',message:'getCentroid returning null',data:{geometryType:geometry?.type,hasCoordinates:!!geometry?.coordinates},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
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
  const shouldShowList = showPropertyList && (filterParams.municipality || searchQuery || filterType || (data?.properties && data.properties.length > 0))
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
          whenReady={() => {
            // Map initialization handled by MapInitializer component
              setIsMapReady(true)
          }}
        >
        <MapInitializer
          mapRef={mapRef}
          setMapBounds={setMapBounds}
          setIsMapReady={setIsMapReady}
          setCenter={setCenter}
          setZoom={setZoom}
          mapUpdatingRef={mapUpdatingRef}
        />
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
        <div className="loading-overlay" style={{ background: '#fee2e2', color: '#dc2626', padding: '20px', maxWidth: '500px', margin: '20px auto', borderRadius: '8px' }}>
          <p style={{ fontWeight: 'bold', marginBottom: '10px' }}>⚠️ Error loading properties</p>
          <p style={{ fontSize: '14px', marginBottom: '10px' }}>
            {error instanceof Error ? error.message : 'Unknown error occurred'}
          </p>
          {error && (error as any)?.response && (
            <p style={{ fontSize: '12px', opacity: 0.8 }}>
              Status: {(error as any).response.status} - {(error as any).response.statusText}
            </p>
          )}
          <p style={{ fontSize: '12px', marginTop: '10px', opacity: 0.7 }}>
            Check browser console for more details. Make sure the backend is running on port 8000.
          </p>
          <button 
            onClick={() => window.location.reload()} 
            style={{ 
              marginTop: '15px', 
              padding: '8px 16px', 
              background: '#dc2626', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Retry
          </button>
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
