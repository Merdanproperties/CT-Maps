import { useState, useEffect } from 'react'
import { useMapProvider } from '../../hooks/useMapProvider'
import { LeafletMap } from './LeafletMap'
import { MapboxMap } from './MapboxMap'
import { MapComponentProps } from './MapComponentProps'
import { analyticsApi } from '../../api/client'

export function MapProvider(props: MapComponentProps) {
  const { provider, mapboxToken, fallbackReason } = useMapProvider()
  const [useMapbox, setUseMapbox] = useState(provider === 'mapbox')
  const [mapboxError, setMapboxError] = useState<string | null>(null)

  // Track provider selection and log why Leaflet is used (helps debug "why isn't Mapbox running?")
  useEffect(() => {
    if (fallbackReason) {
      console.warn(`⚠️ Map provider fallback: ${fallbackReason}`)
      setUseMapbox(false)
    }
  }, [fallbackReason])
  useEffect(() => {
    if (provider === 'leaflet' && fallbackReason) {
      console.info(`🗺️ Using Leaflet (OpenStreetMap). To use Mapbox: ${fallbackReason}`)
    }
  }, [provider, fallbackReason])

  // Handle Mapbox errors and fallback
  const handleMapboxError = (error: Error) => {
    console.error('Mapbox error, falling back to Leaflet:', error)
    setMapboxError(error.message)
    setUseMapbox(false)
    // Track fallback event (fire-and-forget; trackMapLoad returns void)
    analyticsApi.trackMapLoad({
      map_type: 'leaflet',
      viewport: {
        center: props.center,
        zoom: props.zoom,
      },
      fallback_reason: `Mapbox failed: ${error.message}`
    })
  }

  // Try Mapbox if configured and no error
  if (useMapbox && mapboxToken && !mapboxError) {
    try {
      return <MapboxMap {...props} />
    } catch (error: any) {
      // If Mapbox component throws during render, catch and fallback
      handleMapboxError(error)
    }
  }

  // Use Leaflet as default or fallback
  return <LeafletMap {...props} />
}
