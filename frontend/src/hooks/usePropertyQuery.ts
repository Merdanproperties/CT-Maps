import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { propertyApi, Property, FilterResponse } from '../api/client'
import { normalizeSearchQuery } from '../utils/searchUtils'

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
 * Determines which API call to make based on the query parameters.
 * Pass signal to cancel in-flight requests when the query is superseded.
 */
async function fetchProperties(
  params: PropertyQueryParams,
  signal?: AbortSignal
): Promise<PropertyQueryResult> {
  const { filterType, filterParams = {}, searchQuery, bbox } = params

  // Build base search params
  const buildSearchParams = (baseParams: any = {}) => {
    const searchParams: any = { ...baseParams, page_size: 200 }  // Reduced to avoid timeouts; increase when indexes/backend are tuned
    // Always include municipality from filterParams if present (ensures it's preserved when other filters change)
    // Convert array to string if needed (backend expects comma-separated string)
    if (filterParams.municipality) {
      searchParams.municipality = Array.isArray(filterParams.municipality) 
        ? filterParams.municipality.join(',') 
        : filterParams.municipality
      // Explicitly exclude bbox when municipality is set to prevent showing properties outside the municipality
      delete searchParams.bbox
    }
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
    
    // Debug logging
    if (filterParams.municipality) {
      console.log('🔍 [buildSearchParams] Building params with municipality:', {
        municipality: searchParams.municipality,
        time_since_sale: searchParams.time_since_sale,
        hasBbox: 'bbox' in searchParams,
        bboxValue: searchParams.bbox,
        allParams: { ...searchParams }
      })
    }
    
    return searchParams
  }

  // Priority 1: Municipality filter
  // Handle both string and array formats for municipality
  const municipalityValue = Array.isArray(filterParams.municipality) 
    ? (filterParams.municipality.length > 0 ? filterParams.municipality[0] : null)
    : filterParams.municipality
    
  if (municipalityValue) {
    // When municipality is set, explicitly exclude bbox to prevent showing properties outside the municipality
    // The backend applies bbox filter after municipality filter, which causes incorrect results
    // Convert array to string if needed (backend expects comma-separated string)
    const municipalityParam = Array.isArray(filterParams.municipality) 
      ? filterParams.municipality.join(',') 
      : filterParams.municipality
    const baseParams: any = { municipality: municipalityParam }
    // Do not send text search (q) when only municipality is selected so the backend returns
    // the full count for the town (LOWER(TRIM(municipality)) = town); adding q can exclude rows.
    const searchParams = buildSearchParams(baseParams)
    // Explicitly ensure bbox is not included (delete even if it doesn't exist)
    delete searchParams.bbox
    
    // Remove any undefined/null values to prevent axios from sending them
    const cleanParams: any = {}
    for (const [key, value] of Object.entries(searchParams)) {
      if (value !== undefined && value !== null && key !== 'bbox') {
        cleanParams[key] = value
      }
    }
    
    return await propertyApi.search(cleanParams, signal)
  }

  // Priority 2: Search query
  if (searchQuery) {
    const normalizedQ = normalizeSearchQuery(searchQuery)
    if (normalizedQ.length > 0) {
      const searchParams = buildSearchParams({ q: normalizedQ })
      return await propertyApi.search(searchParams, signal)
    }
  }

  // Priority 3: Filter type (lead types)
  if (filterType) {
    const defaultPageSize = 2000  // Balanced: ~1.6MB response, good performance
    let filterResult: FilterResponse
    switch (filterType) {
      case 'high-equity':
        filterResult = await propertyApi.getHighEquity({ ...filterParams, page_size: defaultPageSize }, signal)
        break
      case 'vacant':
        filterResult = await propertyApi.getVacant({ ...filterParams, page_size: defaultPageSize }, signal)
        break
      case 'absentee-owners':
        filterResult = await propertyApi.getAbsenteeOwners({ ...filterParams, page_size: defaultPageSize }, signal)
        break
      case 'recently-sold':
        filterResult = await propertyApi.getRecentlySold({ ...filterParams, page_size: defaultPageSize }, signal)
        break
      case 'low-equity':
        filterResult = await propertyApi.getLowEquity({ ...filterParams, page_size: defaultPageSize }, signal)
        break
      default:
        // Fallback to bbox search for unknown filter types
        if (bbox) {
          return await propertyApi.search({ bbox, page_size: 200 }, signal)
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

  // Priority 4: Custom filters (without bbox - show ALL matching properties, not just viewport)
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

  if (hasCustomFilters) {
    // Don't include bbox when filters are active - show ALL matching properties
    const searchParams = buildSearchParams()
    // If municipality is set, explicitly exclude bbox
    // Check both array and string formats
    const hasMunicipality = filterParams.municipality && (
      (Array.isArray(filterParams.municipality) && filterParams.municipality.length > 0) ||
      (typeof filterParams.municipality === 'string' && filterParams.municipality.length > 0)
    )
    if (hasMunicipality) {
      delete searchParams.bbox
    }
    
    // Remove any undefined/null values to prevent axios from sending them
    const cleanParams: any = {}
    for (const [key, value] of Object.entries(searchParams)) {
      if (value !== undefined && value !== null && key !== 'bbox') {
        cleanParams[key] = value
      }
    }
    
    return await propertyApi.search(cleanParams, signal)
  }

  // Priority 5: Default bbox search (show properties in viewport)
  if (bbox) {
    return await propertyApi.search({ bbox, page_size: 200 }, signal)
  }

  // No valid query - return empty result
  return { properties: [], total: 0, page: 1, page_size: 200 }
}

/**
 * Custom hook for fetching properties based on various filters and search criteria
 */
export function usePropertyQuery(params: PropertyQueryParams) {
  const { filterType, filterParams, searchQuery, bbox, mapBounds, center, zoom } = params

  // Create a stable query key
  // When municipality is set, exclude mapBounds from query key to prevent map movements from triggering new queries
  // Normalize municipality to string for consistent query key
  const municipalityKey = filterParams?.municipality 
    ? (Array.isArray(filterParams.municipality) 
        ? filterParams.municipality.join(',') 
        : filterParams.municipality)
    : null
    
  const queryKey = [
    'properties',
    filterType,
    JSON.stringify(filterParams),
    searchQuery,
    // Only include mapBounds in query key if municipality is NOT set (prevents bbox interference)
    municipalityKey ? null : (mapBounds ? `${mapBounds.west},${mapBounds.south},${mapBounds.east},${mapBounds.north}` : null),
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

  // When municipality is set, don't use bbox/mapBounds for query enabling
  // This prevents map movements from triggering queries when municipality filter is active
  const hasBbox = filterParams?.municipality ? false : (!!bbox || !!mapBounds || (!!center && !!zoom))

  const enabled = hasSearchCriteria || hasBbox

  // #region agent log
  useEffect(() => {
    (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'usePropertyQuery.ts:enabled',message:'Query enabled state',data:{enabled,hasSearchCriteria,hasBbox,searchQueryLen:searchQuery?.trim()?.length,hasOwnerAddress:!!filterParams?.owner_address},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H4,H5'})}).catch(()=>{}));
  }, [enabled, hasSearchCriteria, hasBbox, searchQuery, filterParams?.owner_address])
  // #endregion

  const queryResult = useQuery({
    queryKey,
    queryFn: async ({ signal }) => {
      // Check if cancelled
      if (signal?.aborted) {
        return { properties: [], total: 0, page: 1, page_size: 200 }
      }

      try {
        // Do not block on health check - let the request run and fail fast if backend is down
        // (waitForHealthy caused 3–30s stalls when backend was unhealthy)

        // When municipality is set, don't use bbox at all - municipality filter should be exclusive
        // Calculate bbox only if municipality is NOT set
        let calculatedBbox: string | undefined = bbox
        if (!filterParams?.municipality) {
          if (!calculatedBbox && mapBounds) {
            calculatedBbox = `${mapBounds.west},${mapBounds.south},${mapBounds.east},${mapBounds.north}`
          } else if (!calculatedBbox && center && zoom) {
            const latRange = 180 / Math.pow(2, zoom)
            const lngRange = 360 / Math.pow(2, zoom)
            calculatedBbox = `${center[1] - lngRange},${center[0] - latRange},${center[1] + lngRange},${center[0] + latRange}`
          }
        } else {
          // Municipality is set - explicitly don't use bbox
          calculatedBbox = undefined
        }

        const result = await fetchProperties(
          {
            filterType,
            filterParams,
            searchQuery,
            bbox: calculatedBbox,
            mapBounds: filterParams?.municipality ? null : mapBounds, // Don't pass mapBounds when municipality is set
            center,
            zoom,
          },
          signal
        )

        // Check if cancelled after API call
        if (signal?.aborted) {
          return { properties: [], total: 0, page: 1, page_size: 200 }
        }

        return result
      } catch (error: any) {
        // Handle cancellation gracefully
        if (signal?.aborted || error?.message?.includes('cancelled')) {
          return { properties: [], total: 0, page: 1, page_size: 200 }
        }
        throw error
      }
    },
    enabled,
    staleTime: filterParams?.municipality ? 0 : 10000, // Always consider data stale when municipality is set to force fresh queries
    refetchOnWindowFocus: false,
    retry: 1,
    retryDelay: 1000,
    gcTime: 300000, // Keep data in cache for 5 minutes
    refetchOnMount: filterParams?.municipality ? 'always' : true, // Always refetch on mount when municipality is set
    placeholderData: undefined, // Don't use placeholder data - always fetch fresh
  })
  
  return queryResult
}
