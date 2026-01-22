import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'

interface MapBoundsUpdaterProps {
  onBoundsChange: (bounds: { north: number; south: number; east: number; west: number }) => void
}

export function MapBoundsUpdater({ onBoundsChange }: MapBoundsUpdaterProps) {
  const map = useMap()
  const lastBoundsRef = useRef<string | null>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)
  const onBoundsChangeRef = useRef(onBoundsChange)
  const isInitializedRef = useRef(false)

  // Store the latest callback in a ref to avoid re-subscribing
  useEffect(() => {
    onBoundsChangeRef.current = onBoundsChange
  }, [onBoundsChange])

  useEffect(() => {
    const updateBounds = () => {
      // Clear any pending timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }

      // Debounce the bounds update
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
      
      timeoutRef.current = setTimeout(() => {
        const bounds = map.getBounds()
        const boundsString = `${bounds.getNorth().toFixed(2)},${bounds.getSouth().toFixed(2)},${bounds.getEast().toFixed(2)},${bounds.getWest().toFixed(2)}`
        
        // Only update if bounds have changed
        if (lastBoundsRef.current !== boundsString) {
          lastBoundsRef.current = boundsString
          onBoundsChangeRef.current({
            north: bounds.getNorth(),
            south: bounds.getSouth(),
            east: bounds.getEast(),
            west: bounds.getWest(),
          })
        }
      }, 1000) // 1 second debounce
    }

    // Only set up listeners once
    if (!isInitializedRef.current) {
      isInitializedRef.current = true
      
      // Update on move and zoom (not on every move event)
      map.on('moveend', updateBounds)
      map.on('zoomend', updateBounds)
      
      // Initial bounds (immediate)
      updateBounds()
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [map]) // Only depend on map, not onBoundsChange

  return null
}
