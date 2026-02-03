import { useEffect, useRef, useCallback } from 'react'
import { MapContainer, TileLayer, GeoJSON, Marker, useMap, LayerGroup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { MapBoundsUpdater } from '../../pages/MapBoundsUpdater'
import { MapComponentProps } from './MapComponentProps'
import { analyticsApi } from '../../api/client'

// Fix for default marker icons in React-Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

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
    
    // Track map load for analytics
    const center = map.getCenter()
    analyticsApi.trackMapLoad({
      map_type: 'leaflet',
      viewport: {
        center: [center.lat, center.lng],
        zoom: map.getZoom(),
        bounds: {
          north: initialBounds.getNorth(),
          south: initialBounds.getSouth(),
          east: initialBounds.getEast(),
          west: initialBounds.getWest(),
        }
      }
    })
    
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

// When container or window size changes (sidebar, header, F12 DevTools), tell Leaflet to recalc so the map doesn't white out
function MapResizeHandler() {
  const map = useMap()
  useEffect(() => {
    const invalidate = () => setTimeout(() => map.invalidateSize(), 0)
    const container = map.getContainer()
    if (container) {
      const ro = new ResizeObserver(invalidate)
      ro.observe(container)
      const onWindowResize = () => invalidate()
      window.addEventListener('resize', onWindowResize)
      return () => {
        ro.disconnect()
        window.removeEventListener('resize', onWindowResize)
      }
    }
  }, [map])
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

export function LeafletMap(props: MapComponentProps) {
  const {
    center,
    zoom,
    geoJsonData,
    selectedProperty,
    addressNumberMarkers,
    onBoundsChange,
    setCenter,
    setZoom,
    setIsMapReady,
    setMapBounds,
    mapRef,
    mapUpdatingRef,
    geoJsonStyle,
    getCentroid,
    navigate
  } = props

  // Handle GeoJSON click and add labels - popup disabled, only update sidebar
  const onEachFeature = useCallback((feature: any, layer: L.Layer) => {
    const featureId = feature.properties?.id
    if (!featureId) {
      console.warn('Feature missing id:', feature)
      return
    }
    
    // Find property by ID
    const property = props.properties.find(p => p.id === featureId)
    
    if (property) {
      layer.on({
        click: (e: L.LeafletMouseEvent) => {
          e.originalEvent.stopPropagation()
          console.log('Map click - Feature ID:', featureId, 'Property found:', property.id, property.address)
          // Update sidebar but don't show popup on map
          props.onPropertyClick(property)
          
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
      console.warn('Property not found for feature ID:', featureId, 'Available IDs:', props.properties.map(p => p.id).slice(0, 10))
    }
  }, [props.properties, props.onPropertyClick, geoJsonStyle, setCenter, setZoom])

  // Render viewport centroids (Point) as circles; Polygon/MultiPolygon use default path rendering (selected property)
  const pointToLayer = useCallback((feature: GeoJSON.Feature, latlng: L.LatLng) => {
    const style = geoJsonStyle()
    return L.circleMarker(latlng, {
      radius: 8,
      fillColor: style.fillColor,
      fillOpacity: style.fillOpacity,
      color: style.color,
      weight: style.weight,
    })
  }, [geoJsonStyle])

  // Popup functionality disabled - property details shown in sidebar only
  const selectedPropertyMarker = null

  return (
    <div className="map-container-wrapper">
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ width: '100%', height: '100%' }}
        whenReady={() => {
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
        <MapResizeHandler />
        <MapUpdater 
          center={center} 
          zoom={zoom} 
          skipUpdate={false}
          onUpdate={() => { mapUpdatingRef.current = true }}
        />
        <MapBoundsUpdater 
          onBoundsChange={onBoundsChange}
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
              pointToLayer={pointToLayer}
            />
            <LayerGroup>
              {addressNumberMarkers}
            </LayerGroup>
          </>
        )}

        {selectedPropertyMarker}
      </MapContainer>
    </div>
  )
}
