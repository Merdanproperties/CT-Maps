import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import Map, { Source, Layer, Marker, Popup } from 'react-map-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { MapComponentProps } from './MapComponentProps'
import { analyticsApi } from '../../api/client'
import PropertyCard from '../PropertyCard'
import './MapboxMap.css'

export function MapboxMap(props: MapComponentProps) {
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
    properties,
    navigate
  } = props

  const mapboxToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN
  // Default to satellite-streets-v12 (satellite imagery with street labels)
  // Can be overridden via VITE_MAPBOX_STYLE environment variable
  const mapboxStyle = import.meta.env.VITE_MAPBOX_STYLE || 'mapbox://styles/mapbox/satellite-streets-v12'
  const [mapInstance, setMapInstance] = useState<any>(null)
  const [showPopup, setShowPopup] = useState(false)
  const [popupProperty, setPopupProperty] = useState<typeof selectedProperty>(null)
  const [popupLngLat, setPopupLngLat] = useState<[number, number] | null>(null)
  const [hasError, setHasError] = useState(false)
  const lastBoundsRef = useRef<string | null>(null)
  const boundsTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Extract street number from address
  const getStreetNumber = (address: string | null | undefined): string | null => {
    if (!address) return null
    // Match numbers at the start of the address (e.g., "768 MAPLE ST" -> "768")
    const match = address.trim().match(/^(\d+)/)
    return match ? match[1] : null
  }

  // Create address number markers for Mapbox - only show at street level zoom (15+)
  const mapboxAddressMarkers = useMemo(() => {
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
              key={`mapbox-label-${property.id}`}
              longitude={centroid[1]}
              latitude={centroid[0]}
              anchor="center"
            >
              <div className="address-number">{streetNumber}</div>
            </Marker>
          )
        }
      }
    })
    
    return markers
  }, [properties, zoom, getCentroid])

  // Check for token at component level
  if (!mapboxToken) {
    throw new Error('Mapbox access token is required')
  }

  // If error occurred, don't render
  if (hasError) {
    throw new Error('Mapbox map initialization failed')
  }

  // Track map load
  useEffect(() => {
    if (mapInstance) {
      try {
        const bounds = mapInstance.getBounds()
        if (bounds) {
          setMapBounds({
            north: bounds.getNorth(),
            south: bounds.getSouth(),
            east: bounds.getEast(),
            west: bounds.getWest(),
          })
          setIsMapReady(true)

          // Track map load for analytics
          const center = mapInstance.getCenter()
          analyticsApi.trackMapLoad({
            map_type: 'mapbox',
            viewport: {
              center: [center.lat, center.lng],
              zoom: mapInstance.getZoom(),
              bounds: {
                north: bounds.getNorth(),
                south: bounds.getSouth(),
                east: bounds.getEast(),
                west: bounds.getWest(),
              }
            }
          })
        }
      } catch (error: any) {
        console.error('Error initializing Mapbox map:', error)
        setHasError(true)
        throw error // This will trigger fallback
      }
    }
  }, [mapInstance, setMapBounds, setIsMapReady])

  // Update bounds on map move
  useEffect(() => {
    if (!mapInstance) return

    const updateBounds = () => {
      if (boundsTimeoutRef.current) {
        clearTimeout(boundsTimeoutRef.current)
      }

      boundsTimeoutRef.current = setTimeout(() => {
        const bounds = mapInstance.getBounds()
        if (bounds) {
          const boundsString = `${bounds.getNorth().toFixed(2)},${bounds.getSouth().toFixed(2)},${bounds.getEast().toFixed(2)},${bounds.getWest().toFixed(2)}`
          
          if (lastBoundsRef.current !== boundsString) {
            lastBoundsRef.current = boundsString
            onBoundsChange({
              north: bounds.getNorth(),
              south: bounds.getSouth(),
              east: bounds.getEast(),
              west: bounds.getWest(),
            })
          }
        }
      }, 1000)
    }

    mapInstance.on('moveend', updateBounds)
    mapInstance.on('zoomend', updateBounds)

    return () => {
      if (boundsTimeoutRef.current) {
        clearTimeout(boundsTimeoutRef.current)
      }
      mapInstance.off('moveend', updateBounds)
      mapInstance.off('zoomend', updateBounds)
    }
  }, [mapInstance, onBoundsChange])

  // Update map view when center/zoom changes
  useEffect(() => {
    if (!mapInstance || mapUpdatingRef.current) return

    try {
      const centerKey = `${center[0].toFixed(5)},${center[1].toFixed(5)}`
      const currentCenter = mapInstance.getCenter()
      const centerChanged = Math.abs(currentCenter.lat - center[0]) > 0.0001 || 
                           Math.abs(currentCenter.lng - center[1]) > 0.0001
      const zoomChanged = Math.abs(mapInstance.getZoom() - zoom) > 0.01

      if (centerChanged || zoomChanged) {
        mapUpdatingRef.current = true
        mapInstance.flyTo({
          center: [center[1], center[0]], // Mapbox uses [lng, lat]
          zoom: zoom,
          duration: 500
        })

        setTimeout(() => {
          mapUpdatingRef.current = false
        }, 600)
      }
    } catch (error: any) {
      console.error('Error updating Mapbox map view:', error)
      // Don't throw here - just log, as this is not a fatal error
    }
  }, [center, zoom, mapInstance, mapUpdatingRef])

  // Handle map load
  const onMapLoad = useCallback((event: any) => {
    try {
      const map = event.target
      setMapInstance(map)
      mapRef.current = map
    } catch (error: any) {
      console.error('Error in onMapLoad:', error)
      setHasError(true)
      throw error
    }
  }, [mapRef])

  // Handle map errors
  const onError = useCallback((error: any) => {
    console.error('Mapbox map error:', error)
    setHasError(true)
    throw new Error(`Mapbox error: ${error.message || 'Unknown error'}`)
  }, [])

  // Handle feature click
  const onFeatureClick = useCallback((event: any) => {
    const feature = event.features?.[0]
    if (!feature) return

    const propertyId = feature.properties?.id
    const property = props.properties.find(p => p.id === propertyId)
    
    if (property) {
      props.onPropertyClick(property)
      
      // Show popup
      const [lng, lat] = event.lngLat
      setPopupLngLat([lat, lng])
      setPopupProperty(property)
      setShowPopup(true)

      // Center map on clicked property
      const geom = property.geometry?.geometry
      if (geom) {
        const centroid = getCentroid(geom)
        if (centroid) {
          setCenter(centroid)
          setZoom(18)
        }
      }
    }
  }, [props, getCentroid, setCenter, setZoom])

  // Update popup when selected property changes
  useEffect(() => {
    if (selectedProperty && mapInstance) {
      const geom = selectedProperty.geometry?.geometry
      let popupCenter: [number, number] | null = null
      
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

      if (popupCenter) {
        setPopupLngLat(popupCenter)
        setPopupProperty(selectedProperty)
        setShowPopup(true)
      }
    } else {
      setShowPopup(false)
      setPopupProperty(null)
    }
  }, [selectedProperty, mapInstance])

  const style = geoJsonStyle()

  return (
    <div className="map-container-wrapper">
      <Map
        mapboxAccessToken={mapboxToken}
        initialViewState={{
          longitude: center[1],
          latitude: center[0],
          zoom: zoom
        }}
        style={{ width: '100%', height: '100%' }}
        mapStyle={mapboxStyle}
        onLoad={onMapLoad}
        onError={onError}
        onMoveEnd={(e) => {
          if (!mapUpdatingRef.current && e.target) {
            const center = e.target.getCenter()
            setCenter([center.lat, center.lng])
            setZoom(e.target.getZoom())
          }
          mapUpdatingRef.current = false
        }}
        onZoomEnd={(e) => {
          if (!mapUpdatingRef.current && e.target) {
            setZoom(e.target.getZoom())
          }
        }}
        interactiveLayerIds={['properties-layer']}
        onClick={onFeatureClick}
      >
        {/* GeoJSON Source and Layer */}
        {geoJsonData.features.length > 0 && (
          <Source id="properties" type="geojson" data={geoJsonData}>
            <Layer
              id="properties-layer"
              type="fill"
              paint={{
                'fill-color': style.fillColor,
                'fill-opacity': style.fillOpacity,
                'fill-outline-color': style.color,
              }}
            />
            <Layer
              id="properties-outline"
              type="line"
              paint={{
                'line-color': style.color,
                'line-width': style.weight,
              }}
            />
          </Source>
        )}

        {/* Address number markers - shown when zoomed in (zoom >= 15) */}
        {mapboxAddressMarkers}

        {/* Selected property popup */}
        {showPopup && popupProperty && popupLngLat && (
          <Popup
            longitude={popupLngLat[1]}
            latitude={popupLngLat[0]}
            anchor="bottom"
            onClose={() => setShowPopup(false)}
            closeButton={true}
            closeOnClick={false}
          >
            <PropertyCard
              property={popupProperty}
              onClick={() => navigate(`/property/${popupProperty.id}`)}
            />
          </Popup>
        )}
      </Map>
    </div>
  )
}
