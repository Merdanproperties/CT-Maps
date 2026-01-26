import { Property } from '../../api/client'
import L from 'leaflet'

export interface MapComponentProps {
  center: [number, number]
  zoom: number
  geoJsonData: GeoJSON.FeatureCollection
  selectedProperty: Property | null
  addressNumberMarkers: JSX.Element[]
  onPropertyClick: (property: Property) => void
  onBoundsChange: (bounds: { north: number; south: number; east: number; west: number }) => void
  setCenter: (center: [number, number]) => void
  setZoom: (zoom: number) => void
  setIsMapReady: (ready: boolean) => void
  setMapBounds: (bounds: { north: number; south: number; east: number; west: number }) => void
  mapRef: React.MutableRefObject<L.Map | any | null>
  mapUpdatingRef: React.MutableRefObject<boolean>
  geoJsonStyle: () => {
    fillColor: string
    fillOpacity: number
    color: string
    weight: number
  }
  getCentroid: (geometry: any) => [number, number] | null
  properties: Property[]
  navigate: (path: string) => void
}
