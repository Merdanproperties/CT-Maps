import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import Map, { Source, Layer, Marker } from 'react-map-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { MapComponentProps } from './MapComponentProps'
import { analyticsApi } from '../../api/client'
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
    navigate,
    municipalityBoundaries = [],
  } = props

  const mapboxToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN
  // Default to satellite-streets-v12 (satellite imagery with street labels)
  // Can be overridden via VITE_MAPBOX_STYLE environment variable
  const mapboxStyle = import.meta.env.VITE_MAPBOX_STYLE || 'mapbox://styles/mapbox/satellite-streets-v12'
  const [mapInstance, setMapInstance] = useState<any>(null)
  const [hasError, setHasError] = useState(false)
  const lastBoundsRef = useRef<string | null>(null)
  const boundsTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wrapperRef = useRef<HTMLDivElement | null>(null)

  // Extract street number from address
  const getStreetNumber = (address: string | null | undefined): string | null => {
    if (!address) return null
    // Match numbers at the start of the address (e.g., "768 MAPLE ST" -> "768")
    const match = address.trim().match(/^(\d+)/)
    return match ? match[1] : null
  }

  // Create address markers for Mapbox - only show at street level zoom (15+)
  const mapboxAddressMarkers = useMemo(() => {
    // Only show addresses when zoomed in to street level
    if (zoom < 15 || !properties || properties.length === 0) {
      return []
    }
    
    const markers: JSX.Element[] = []
    
    properties.forEach((property) => {
      const address = property.address
      if (!address || !property.geometry?.geometry) {
        return
      }
      
      const centroid = getCentroid(property.geometry.geometry)
      if (!centroid) {
        return
      }
      
      // Extract street number for display (matching Torrington style)
      const streetNumber = getStreetNumber(address)
      const displayText = streetNumber || address
      
      markers.push(
        <Marker
          key={`mapbox-label-${property.id}`}
          longitude={centroid[1]}
          latitude={centroid[0]}
          anchor="center"
        >
          <div className="address-number">{displayText}</div>
        </Marker>
      )
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

  // When container or window size changes (sidebar, F12 DevTools), tell Mapbox to recalc so the map doesn't white out
  useEffect(() => {
    if (!mapInstance) return
    const resize = () => {
      try {
        mapInstance.resize()
      } catch (_) {}
    }
    const wrapper = wrapperRef.current
    if (wrapper) {
      const ro = new ResizeObserver(resize)
      ro.observe(wrapper)
      window.addEventListener('resize', resize)
      return () => {
        ro.disconnect()
        window.removeEventListener('resize', resize)
      }
    }
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [mapInstance])

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

  // Handle feature click - disabled popup, only update sidebar
  const onFeatureClick = useCallback((event: any) => {
    const feature = event.features?.[0]
    if (!feature) return

    const propertyId = feature.properties?.id
    const property = props.properties.find(p => p.id === propertyId)
    
    if (property) {
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
    }
  }, [props, getCentroid, setCenter, setZoom])

  // Popup functionality disabled - property details shown in sidebar only

  const style = geoJsonStyle()

  return (
    <div className="map-container-wrapper" ref={wrapperRef}>
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
        interactiveLayerIds={['properties-layer', 'properties-points-layer']}
        onClick={onFeatureClick}
      >
        {/* Municipality boundary outlines (when town(s) selected) */}
        {municipalityBoundaries.length > 0 && (
          <Source
            id="municipality-boundaries"
            type="geojson"
            data={{
              type: 'FeatureCollection',
              features: municipalityBoundaries.map((b) => ({
                type: 'Feature',
                properties: { name: b.name },
                geometry: {
                  type: 'Polygon',
                  coordinates: [[
                    [b.west, b.south],
                    [b.east, b.south],
                    [b.east, b.north],
                    [b.west, b.north],
                    [b.west, b.south],
                  ]],
                },
              })),
            }}
          >
            <Layer
              id="municipality-boundaries-line"
              type="line"
              paint={{ 'line-color': '#0ea5e9', 'line-width': 2 }}
            />
          </Source>
        )}

        {/* GeoJSON Source and Layer */}
        {geoJsonData.features.length > 0 && (
          <Source id="properties" type="geojson" data={geoJsonData}>
            {/* Polygon layer for properties with polygon geometry */}
            <Layer
              id="properties-layer"
              type="fill"
              filter={['==', ['geometry-type'], 'Polygon']}
              paint={{
                'fill-color': style.fillColor,
                'fill-opacity': style.fillOpacity,
                'fill-outline-color': style.color,
              }}
            />
            <Layer
              id="properties-outline"
              type="line"
              filter={['==', ['geometry-type'], 'Polygon']}
              paint={{
                'line-color': style.color,
                'line-width': style.weight,
              }}
            />
            {/* Circle layer for properties with Point geometry */}
            <Layer
              id="properties-points-layer"
              type="circle"
              filter={['==', ['geometry-type'], 'Point']}
              paint={{
                'circle-color': style.fillColor,
                'circle-opacity': style.fillOpacity,
                'circle-radius': 6,
                'circle-stroke-color': style.color,
                'circle-stroke-width': style.weight,
              }}
            />
          </Source>
        )}

        {/* Address number markers - shown when zoomed in (zoom >= 15) */}
        {mapboxAddressMarkers}
      </Map>
    </div>
  )
}
