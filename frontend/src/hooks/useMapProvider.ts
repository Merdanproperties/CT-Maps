import { useMemo } from 'react'

export type MapProviderType = 'mapbox' | 'leaflet' | 'auto'

export interface MapProviderConfig {
  provider: 'mapbox' | 'leaflet'
  mapboxToken: string | undefined
  fallbackReason?: string
}

/**
 * Hook to determine which map provider to use
 * Checks environment variables and returns appropriate provider
 */
export function useMapProvider(): MapProviderConfig {
  return useMemo(() => {
    const mapProviderEnv = import.meta.env.VITE_MAP_PROVIDER as MapProviderType | undefined
    const mapboxToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN as string | undefined

    // Manual override
    if (mapProviderEnv === 'leaflet') {
      return {
        provider: 'leaflet',
        mapboxToken: undefined,
        fallbackReason: 'Manually set to leaflet'
      }
    }

    if (mapProviderEnv === 'mapbox') {
      if (!mapboxToken) {
        console.warn('⚠️ VITE_MAP_PROVIDER=mapbox but no VITE_MAPBOX_ACCESS_TOKEN found. Falling back to Leaflet.')
        return {
          provider: 'leaflet',
          mapboxToken: undefined,
          fallbackReason: 'Mapbox token missing'
        }
      }
      return {
        provider: 'mapbox',
        mapboxToken
      }
    }

    // Auto mode (default): Use Mapbox if token exists, otherwise Leaflet
    if (mapboxToken) {
      return {
        provider: 'mapbox',
        mapboxToken
      }
    }

    // Default to Leaflet (no token)
    return {
      provider: 'leaflet',
      mapboxToken: undefined,
      fallbackReason: 'No VITE_MAPBOX_ACCESS_TOKEN set (add to frontend/.env or Docker env)'
    }
  }, [])
}
