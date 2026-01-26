import { useEffect, useRef, useCallback } from 'react'
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, useMap, LayerGroup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { MapBoundsUpdater } from '../../pages/MapBoundsUpdater'
import { MapComponentProps } from './MapComponentProps'
import { analyticsApi } from '../../api/client'
import PropertyCard from '../PropertyCard'

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

  // Handle GeoJSON click and add labels
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

  // Calculate popup center for selected property
  const selectedPropertyMarker = selectedProperty ? (() => {
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
  })() : null

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
