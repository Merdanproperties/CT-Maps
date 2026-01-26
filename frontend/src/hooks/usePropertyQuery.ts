import { useQuery } from '@tanstack/react-query'
import { propertyApi, Property, FilterResponse } from '../api/client'
import { healthCheckService } from '../services/healthCheck'

export interface PropertyQueryParams {
  filterType?: string | null
  filterParams?: {
    municipality?: string
    min_value?: number
    max_value?: number
    property_type?: string
    min_lot_size?: number
    max_lot_size?: number
    unit_type?: string
    zoning?: string
    year_built_min?: number
    year_built_max?: number
    has_phone?: boolean
    has_email?: boolean
    has_contact?: string
    sales_history?: string
    days_since_sale_min?: number
    days_since_sale_max?: number
    time_since_sale?: string
    tax_amount_min?: number
    tax_amount_max?: number
    annual_tax?: string
    owner_address?: string
    owner_city?: string
    owner_state?: string
  }
  searchQuery?: string
  bbox?: string
  mapBounds?: { north: number; south: number; east: number; west: number } | null
  center?: [number, number]
  zoom?: number
}

interface PropertyQueryResult {
  properties: Property[]
  total: number
  page: number
  page_size: number
}

/**
 * Determines which API call to make based on the query parameters
 */
async function fetchProperties(params: PropertyQueryParams): Promise<PropertyQueryResult> {
  const { filterType, filterParams = {}, searchQuery, bbox } = params

  // Build base search params
  const buildSearchParams = (baseParams: any = {}) => {
    const searchParams: any = { ...baseParams, page_size: 2000 }  // Balanced limit
    if (filterParams.min_value) searchParams.min_value = filterParams.min_value
    if (filterParams.max_value) searchParams.max_value = filterParams.max_value
    if (filterParams.property_type) searchParams.property_type = filterParams.property_type
    if (filterParams.min_lot_size) searchParams.min_lot_size = filterParams.min_lot_size
    if (filterParams.max_lot_size) searchParams.max_lot_size = filterParams.max_lot_size
    if (filterParams.unit_type) searchParams.unit_type = filterParams.unit_type
    if (filterParams.zoning) searchParams.zoning = filterParams.zoning
    if (filterParams.year_built_min) searchParams.year_built_min = filterParams.year_built_min
    if (filterParams.year_built_max) searchParams.year_built_max = filterParams.year_built_max
    if (filterParams.has_phone !== undefined) searchParams.has_phone = filterParams.has_phone
    if (filterParams.has_email !== undefined) searchParams.has_email = filterParams.has_email
    if (filterParams.has_contact) searchParams.has_contact = filterParams.has_contact
    if (filterParams.sales_history) searchParams.sales_history = filterParams.sales_history
    if (filterParams.days_since_sale_min) searchParams.days_since_sale_min = filterParams.days_since_sale_min
    if (filterParams.days_since_sale_max) searchParams.days_since_sale_max = filterParams.days_since_sale_max
    if (filterParams.time_since_sale) searchParams.time_since_sale = filterParams.time_since_sale
    if (filterParams.tax_amount_min) searchParams.tax_amount_min = filterParams.tax_amount_min
    if (filterParams.tax_amount_max) searchParams.tax_amount_max = filterParams.tax_amount_max
    if (filterParams.annual_tax) searchParams.annual_tax = filterParams.annual_tax
    if (filterParams.owner_address) searchParams.owner_address = filterParams.owner_address
    if (filterParams.owner_city) searchParams.owner_city = filterParams.owner_city
    if (filterParams.owner_state) searchParams.owner_state = filterParams.owner_state
    return searchParams
  }

  // Priority 1: Municipality filter
  if (filterParams.municipality) {
    const searchParams = buildSearchParams({ municipality: filterParams.municipality, page_size: 100 })
    return await propertyApi.search(searchParams)
  }

  // Priority 2: Search query
  if (searchQuery && searchQuery.trim().length > 0) {
    const searchParams = buildSearchParams({ q: searchQuery.trim(), page_size: 100 })
    return await propertyApi.search(searchParams)
  }

  // Priority 3: Filter type (lead types)
  if (filterType) {
    const defaultPageSize = 2000  // Balanced: ~1.6MB response, good performance
    let filterResult: FilterResponse
    switch (filterType) {
      case 'high-equity':
        filterResult = await propertyApi.getHighEquity({ ...filterParams, page_size: defaultPageSize })
        break
      case 'vacant':
        filterResult = await propertyApi.getVacant({ ...filterParams, page_size: defaultPageSize })
        break
      case 'absentee-owners':
        filterResult = await propertyApi.getAbsenteeOwners({ ...filterParams, page_size: defaultPageSize })
        break
      case 'recently-sold':
        filterResult = await propertyApi.getRecentlySold({ ...filterParams, page_size: defaultPageSize })
        break
      case 'low-equity':
        filterResult = await propertyApi.getLowEquity({ ...filterParams, page_size: defaultPageSize })
        break
      default:
        // Fallback to bbox search for unknown filter types
        if (bbox) {
          return await propertyApi.search({ bbox, page_size: 2000 })
        }
        throw new Error(`Unknown filter type: ${filterType}`)
    }
    // Convert FilterResponse to PropertyQueryResult
    const result: PropertyQueryResult = {
      properties: filterResult.properties,
      total: filterResult.total,
      page: filterResult.page ?? 1,
      page_size: filterResult.page_size ?? defaultPageSize,
    }
    return result
  }

  // Priority 4: Custom filters with bbox
  const hasCustomFilters = 
    filterParams.min_value !== undefined || 
    filterParams.max_value !== undefined || 
    filterParams.min_lot_size !== undefined || 
    filterParams.max_lot_size !== undefined ||
    filterParams.property_type !== undefined ||
    filterParams.unit_type !== undefined ||
    filterParams.zoning !== undefined ||
    filterParams.year_built_min !== undefined ||
    filterParams.year_built_max !== undefined ||
    filterParams.has_phone !== undefined ||
    filterParams.has_email !== undefined ||
    filterParams.has_contact !== undefined ||
    filterParams.sales_history !== undefined ||
    filterParams.days_since_sale_min !== undefined ||
    filterParams.days_since_sale_max !== undefined ||
    filterParams.time_since_sale !== undefined ||
    filterParams.tax_amount_min !== undefined ||
    filterParams.tax_amount_max !== undefined ||
    filterParams.annual_tax !== undefined ||
    filterParams.owner_address !== undefined ||
    filterParams.owner_city !== undefined ||
    filterParams.owner_state !== undefined

  if (hasCustomFilters && bbox) {
    const searchParams = buildSearchParams({ bbox })
    return await propertyApi.search(searchParams)
  }

  // Priority 5: Default bbox search (show properties in viewport)
  if (bbox) {
    return await propertyApi.search({ bbox, page_size: 2000 })  // Balanced limit: ~1.6MB per request
  }

  // No valid query - return empty result
  return { properties: [], total: 0, page: 1, page_size: 2000 }
}

/**
 * Custom hook for fetching properties based on various filters and search criteria
 */
export function usePropertyQuery(params: PropertyQueryParams) {
  const { filterType, filterParams, searchQuery, bbox, mapBounds, center, zoom } = params

  // Create a stable query key
  const queryKey = [
    'properties',
    filterType,
    JSON.stringify(filterParams),
    searchQuery,
    mapBounds ? `${mapBounds.west},${mapBounds.south},${mapBounds.east},${mapBounds.north}` : null,
  ]

  // Determine if query should be enabled
  // Only enable if we have at least one search criteria OR a valid bbox
  const hasSearchCriteria = 
    !!filterParams?.municipality ||
    (!!searchQuery && searchQuery.trim().length > 0) ||
    !!filterType ||
    (filterParams && (
      filterParams.min_value !== undefined ||
      filterParams.max_value !== undefined ||
      filterParams.min_lot_size !== undefined ||
      filterParams.max_lot_size !== undefined ||
      filterParams.property_type !== undefined ||
      filterParams.unit_type !== undefined ||
      filterParams.zoning !== undefined ||
      filterParams.year_built_min !== undefined ||
      filterParams.year_built_max !== undefined ||
      filterParams.has_phone !== undefined ||
      filterParams.has_email !== undefined ||
      filterParams.has_contact !== undefined ||
      filterParams.sales_history !== undefined ||
      filterParams.days_since_sale_min !== undefined ||
      filterParams.days_since_sale_max !== undefined ||
      filterParams.time_since_sale !== undefined ||
      filterParams.tax_amount_min !== undefined ||
      filterParams.tax_amount_max !== undefined ||
      filterParams.annual_tax !== undefined ||
      filterParams.owner_address !== undefined ||
      filterParams.owner_city !== undefined ||
      filterParams.owner_state !== undefined
    ))

  const hasBbox = !!bbox || !!mapBounds || (!!center && !!zoom)

  const enabled = hasSearchCriteria || hasBbox

  return useQuery({
    queryKey,
    queryFn: async ({ signal }) => {
      // Check if cancelled
      if (signal?.aborted) {
        return { properties: [], total: 0, page: 1, page_size: 2000 }
      }

      try {
        // Quick health check before making request (non-blocking, but will wait if backend is down)
        const healthStatus = healthCheckService.getStatus()
        if (!healthStatus.isHealthy && Date.now() - healthStatus.lastChecked > 2000) {
          // Backend might be down, wait a bit for it to come back
          const isHealthy = await healthCheckService.waitForHealthy(3000)
          if (!isHealthy) {
            throw new Error('Backend server is not responding. Please ensure the backend is running on http://localhost:8000')
          }
        }

        // Calculate bbox if not provided
        let calculatedBbox = bbox
        if (!calculatedBbox && mapBounds) {
          calculatedBbox = `${mapBounds.west},${mapBounds.south},${mapBounds.east},${mapBounds.north}`
        } else if (!calculatedBbox && center && zoom) {
          const latRange = 180 / Math.pow(2, zoom)
          const lngRange = 360 / Math.pow(2, zoom)
          calculatedBbox = `${center[1] - lngRange},${center[0] - latRange},${center[1] + lngRange},${center[0] + latRange}`
        }

        const result = await fetchProperties({
          filterType,
          filterParams,
          searchQuery,
          bbox: calculatedBbox,
          mapBounds,
          center,
          zoom,
        })

        // Check if cancelled after API call
        if (signal?.aborted) {
          return { properties: [], total: 0, page: 1, page_size: 2000 }
        }

        return result
      } catch (error: any) {
        // Handle cancellation gracefully
        if (signal?.aborted || error?.message?.includes('cancelled')) {
          return { properties: [], total: 0, page: 1, page_size: 2000 }
        }
        throw error
      }
    },
    enabled,
    staleTime: 10000,
    refetchOnWindowFocus: false,
    retry: 1,
    retryDelay: 1000,
    gcTime: 300000, // Keep data in cache for 5 minutes
    refetchOnMount: false,
  })
}
