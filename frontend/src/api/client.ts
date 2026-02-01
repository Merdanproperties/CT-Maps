import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { healthCheckService } from '../services/healthCheck'

// Use relative URLs to go through Vite proxy, or use env variable if set
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

// Note: HTTP keep-alive agents are not available in browser environment
// The browser handles connection pooling automatically
// If running in Node.js environment, uncomment the following:
/*
import http from 'http'
import https from 'https'

const httpAgent = new http.Agent({ 
  keepAlive: true,
  keepAliveMsecs: 1000,
  maxSockets: 50,
  maxFreeSockets: 10
})

const httpsAgent = new https.Agent({ 
  keepAlive: true,
  keepAliveMsecs: 1000,
  maxSockets: 50,
  maxFreeSockets: 10
})
*/

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    // Note: 'Connection' header cannot be set in browser - browser controls this automatically
  },
  timeout: 60000, // 60 second timeout (options/autocomplete can be slow on large DB)
  // httpAgent and httpsAgent would be added here if in Node.js environment
})

// Retry configuration
const MAX_RETRIES = 3
const RETRY_DELAY = 1000 // Start with 1 second

/**
 * Calculate exponential backoff delay
 */
function getRetryDelay(retryCount: number): number {
  return RETRY_DELAY * Math.pow(2, retryCount)
}

/**
 * Check if error is retryable
 */
function isRetryableError(error: AxiosError): boolean {
  // Don't retry if request was cancelled
  if (axios.isCancel(error)) {
    return false
  }

  // Retry on network errors
  if (!error.response) {
    return true
  }

  // Do not retry on 5xx - fail fast so UI doesn't hang 30+ seconds when backend/DB is down
  if (error.response?.status >= 500) {
    return false
  }

  // Retry on 408 Request Timeout
  if (error.response.status === 408) {
    return true
  }

  // Retry on 429 Too Many Requests
  if (error.response.status === 429) {
    return true
  }

  return false
}

// Add request interceptor with retry logic (no health-check triggers; status from API success/failure)
apiClient.interceptors.request.use(
  async (config) => {
    if (!(config as any).__retryCount) {
      (config as any).__retryCount = 0
    }
    // #region agent log
    const fullUrl = (config.baseURL || '') + (config.url || '');
    (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client.ts:request',message:'API request start',data:{baseURL:config.baseURL,url:config.url,fullUrl},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,B,E'})}).catch(()=>{}));
    // #endregion
    console.log('🌐 API Request:', config.method?.toUpperCase(), config.url, config.params)
    return config
  },
  (error) => {
    console.error('❌ API Request Error:', error)
    return Promise.reject(error)
  }
)

// Add response interceptor with automatic retry and data normalization
apiClient.interceptors.response.use(
  (response) => {
    console.log('✅ API Response:', response.status, response.config.url)
    if (!healthCheckService.getStatus().isHealthy) {
      healthCheckService.setHealthy()
    }
    // Skip normalization for blob responses (export endpoints)
    if (response.config.responseType === 'blob') {
      return response
    }
    // Normalize property data in responses for type safety (don't turn 200 into error on bad shape)
    if (response.data && typeof response.data === 'object') {
      try {
        if (Array.isArray(response.data.properties)) {
          response.data.properties = response.data.properties.map((prop: any) => {
            const migrated = migratePropertyData(prop)
            return PropertyNormalizer.normalize(migrated)
          })
        }
        if (response.data.id || response.data.parcel_id) {
          const migrated = migratePropertyData(response.data)
          response.data = PropertyNormalizer.normalize(migrated)
        }
        if (import.meta.env.DEV) {
          DevelopmentSafety.validateAPIResponse(
            response.config.url || '',
            response.data,
            {}
          )
        }
      } catch (err) {
        console.warn('Response shape unexpected for', response.config.url, err)
        // Return response as-is so caller still gets 200 data
      }
    }
    return response
  },
  async (error: AxiosError) => {
    const config = error.config as (InternalAxiosRequestConfig & { __retryCount?: number }) | undefined
    if (!config) return Promise.reject(error)

    // Aborted/cancelled requests (e.g. user typed again before previous request finished) – don't log as error
    const isCancelled =
      axios.isCancel(error) ||
      error.message === 'canceled' ||
      (error as any).code === 'ERR_CANCELED'
    if (isCancelled) {
      return Promise.reject(error)
    }

    // Handle blob error responses (might contain error JSON)
    if (config?.responseType === 'blob' && error.response?.data) {
      try {
        const blob = error.response.data as Blob
        const errorText = await blob.text()
        console.error('❌ [Export API] Blob error response:', errorText)
        // Try to parse as JSON
        try {
          const errorJson = JSON.parse(errorText)
          error.message = errorJson.detail || errorJson.message || error.message
        } catch {
          error.message = errorText || error.message
        }
      } catch (e) {
        console.error('❌ [Export API] Failed to read error blob:', e)
      }
    }
    
    // Initialize retry count if not present
    if (!config.__retryCount) {
      config.__retryCount = 0
    }

    // Check if we should retry
    if (config.__retryCount < MAX_RETRIES && isRetryableError(error)) {
      config.__retryCount += 1
      const delay = getRetryDelay(config.__retryCount)
      console.log(`🔄 Retrying request (${config.__retryCount}/${MAX_RETRIES}) after ${delay}ms:`, config.url)
      await new Promise(resolve => setTimeout(resolve, delay))
      return apiClient(config)
    }

    // No more retries or non-retryable: mark unhealthy on connection/timeout so banner shows
    const isNetworkError = !error.response && (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED' || error.message?.includes('Network Error'))
    if (isNetworkError) {
      healthCheckService.setUnhealthy(error.message || 'Backend unreachable')
    }
    // #region agent log
    (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client.ts:error',message:'API response error final',data:{code:error.code,message:error.message,url:config?.url,status:error.response?.status},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{}));
    // #endregion
    console.error('❌ API Response Error:', {
      message: error.message,
      url: config?.url,
      method: config?.method,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: config?.responseType === 'blob' ? '[Blob]' : error.response?.data,
      retries: config?.__retryCount,
    })
    
    // Provide more helpful error messages with fix instructions
    if (error.code === 'ECONNABORTED') {
      error.message = 'Request timeout - the server took too long to respond.\n\n' +
        'How to fix:\n' +
        '1. Check if backend is running: curl http://localhost:8000/health\n' +
        '2. Check backend logs: tail -f logs/backend.log\n' +
        '3. Restart backend: cd backend && source venv/bin/activate && uvicorn main:app --reload\n' +
        '4. Or use: ./scripts/start_all.sh\n' +
        '5. Click "Fix" button in status banner for detailed diagnostics'
    } else if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
      error.message = 'Cannot connect to backend server.\n\n' +
        'How to fix:\n' +
        '1. Start backend: cd backend && source venv/bin/activate && uvicorn main:app --reload\n' +
        '2. Verify backend is on port 8000: lsof -i :8000\n' +
        '3. Check if port is blocked by firewall\n' +
        '4. Use startup script: ./scripts/start_all.sh\n' +
        '5. Click the "Fix" button in the status banner for detailed diagnostics'
    } else if (error.response?.status === 404) {
      error.message = `API endpoint not found: ${config?.url}\n\n` +
        'How to fix:\n' +
        '1. Verify backend routes are registered\n' +
        '2. Check backend logs: tail -f logs/backend.log\n' +
        '3. Restart backend: ./scripts/stop_all.sh && ./scripts/start_all.sh\n' +
        '4. Click "Fix" button for detailed diagnostics'
    } else if (error.response && error.response.status >= 500) {
      error.message = `Server error (${error.response.status}): ${error.response.statusText || 'Internal Server Error'}\n\n` +
        'How to fix:\n' +
        '1. Check backend logs: tail -f logs/backend.log\n' +
        '2. Verify database is running: psql -l\n' +
        '3. Check backend/.env configuration\n' +
        '4. Restart backend: ./scripts/stop_all.sh && ./scripts/start_all.sh\n' +
        '5. Click "Fix" button for detailed diagnostics'
    } else if (error.response?.status === 503) {
      error.message = 'Service temporarily unavailable.\n\n' +
        'How to fix:\n' +
        '1. Backend may be starting up - wait a few seconds\n' +
        '2. Check backend health: curl http://localhost:8000/health\n' +
        '3. Check backend logs: tail -f logs/backend.log\n' +
        '4. Restart if needed: ./scripts/start_all.sh\n' +
        '5. Click "Fix" button for detailed diagnostics'
    }
    
    return Promise.reject(error)
  }
)

// Import types and utilities
import type { Property, PropertyDetail } from '../types/property'
import { PropertyNormalizer } from '../types/property'
import { migratePropertyData } from '../utils/dataMigration'
import { DevelopmentSafety } from '../utils/developmentSafety'

// Re-export for backward compatibility
export type { Property, PropertyDetail, PropertyCardData } from '../types/property'
export { PropertyNormalizer } from '../types/property'

export interface SearchResponse {
  properties: Property[]
  total: number
  page: number
  page_size: number
}

export interface FilterResponse {
  properties: Property[]
  total: number
  filter_type: string
  page?: number
  page_size?: number
}

export interface Comment {
  id: number
  property_id: number
  comment: string
  created_at: string
  updated_at: string
}

export const propertyApi = {
  getProperty: async (id: number): Promise<PropertyDetail> => {
    const response = await apiClient.get(`/api/properties/${id}`)
    return response.data
  },

  getPropertyByParcel: async (parcelId: string): Promise<PropertyDetail> => {
    const response = await apiClient.get(`/api/properties/parcel/${parcelId}`)
    return response.data
  },

  search: async (
    params: {
      q?: string
      municipality?: string
      min_value?: number
      max_value?: number
      property_type?: string
      min_lot_size?: number
      max_lot_size?: number
      bbox?: string
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
      page?: number
      page_size?: number
    },
    signal?: AbortSignal
  ): Promise<SearchResponse> => {
    const response = await apiClient.get('/api/search/', { params, signal })
    return response.data
  },

  getMunicipalityBounds: async (municipality: string, signal?: AbortSignal): Promise<{
    municipality: string
    min_lng: number
    min_lat: number
    max_lng: number
    max_lat: number
    center_lat: number
    center_lng: number
    bbox: string
  }> => {
    const response = await apiClient.get(`/api/search/municipality/${encodeURIComponent(municipality)}/bounds`, { signal })
    return response.data
  },

  getHighEquity: async (
    params: { min_equity?: number; min_equity_percent?: number; page?: number; page_size?: number },
    signal?: AbortSignal
  ): Promise<FilterResponse> => {
    const response = await apiClient.get('/api/filters/high-equity', { params, signal })
    return response.data
  },

  getVacant: async (
    params: { include_lots?: boolean; include_structures?: boolean; page?: number; page_size?: number },
    signal?: AbortSignal
  ): Promise<FilterResponse> => {
    const response = await apiClient.get('/api/filters/vacant', { params, signal })
    return response.data
  },

  getAbsenteeOwners: async (
    params: { page?: number; page_size?: number },
    signal?: AbortSignal
  ): Promise<FilterResponse> => {
    const response = await apiClient.get('/api/filters/absentee-owners', { params, signal })
    return response.data
  },

  getRecentlySold: async (
    params: { days?: number; min_price?: number; max_price?: number; page?: number; page_size?: number },
    signal?: AbortSignal
  ): Promise<FilterResponse> => {
    const response = await apiClient.get('/api/filters/recently-sold', { params, signal })
    return response.data
  },

  getLowEquity: async (
    params: { max_equity?: number; page?: number; page_size?: number },
    signal?: AbortSignal
  ): Promise<FilterResponse> => {
    const response = await apiClient.get('/api/filters/low-equity', { params, signal })
    return response.data
  },

  updateProperty: async (id: number, updates: Partial<PropertyDetail>): Promise<PropertyDetail> => {
    const response = await apiClient.patch(`/api/properties/${id}`, updates)
    return response.data
  },

  getZoningOptions: async (filters?: {
    municipality?: string
    unitType?: string
    propertyAge?: string
    timeSinceSale?: string
    annualTax?: string
    ownerCity?: string
    ownerState?: string
  }): Promise<{zoning_codes: string[]}> => {
    const params: any = {}
    if (filters?.municipality) params.municipality = filters.municipality
    if (filters?.unitType) params.unit_type = filters.unitType
    if (filters?.propertyAge) params.property_age = filters.propertyAge
    if (filters?.timeSinceSale) params.time_since_sale = filters.timeSinceSale
    if (filters?.annualTax) params.annual_tax = filters.annualTax
    if (filters?.ownerCity) params.owner_city = filters.ownerCity
    if (filters?.ownerState) params.owner_state = filters.ownerState
    const response = await apiClient.get('/api/search/zoning/options', { params })
    return response.data
  },

  getUnitTypeOptions: async (filters?: {
    municipality?: string
    zoning?: string
    propertyAge?: string
    timeSinceSale?: string
    annualTax?: string
    ownerCity?: string
    ownerState?: string
  }): Promise<{unit_types: Array<{property_type: string, land_use: string | null}>}> => {
    const params: any = {}
    if (filters?.municipality) params.municipality = filters.municipality
    if (filters?.zoning) params.zoning = filters.zoning
    if (filters?.propertyAge) params.property_age = filters.propertyAge
    if (filters?.timeSinceSale) params.time_since_sale = filters.timeSinceSale
    if (filters?.annualTax) params.annual_tax = filters.annualTax
    if (filters?.ownerCity) params.owner_city = filters.ownerCity
    if (filters?.ownerState) params.owner_state = filters.ownerState
    const response = await apiClient.get('/api/search/unit-types/options', { params })
    return response.data
  },

  getTowns: async (): Promise<string[]> => {
    const response = await apiClient.get('/api/autocomplete/towns')
    return response.data
  },

  getOwnerCities: async (filters?: {
    municipality?: string
    unitType?: string
    zoning?: string
    propertyAge?: string
    timeSinceSale?: string
    annualTax?: string
    ownerState?: string
  }): Promise<string[]> => {
    const params: any = {}
    if (filters?.municipality) params.municipality = filters.municipality
    if (filters?.unitType) params.unit_type = filters.unitType
    if (filters?.zoning) params.zoning = filters.zoning
    if (filters?.propertyAge) params.property_age = filters.propertyAge
    if (filters?.timeSinceSale) params.time_since_sale = filters.timeSinceSale
    if (filters?.annualTax) params.annual_tax = filters.annualTax
    if (filters?.ownerState) params.owner_state = filters.ownerState
    const response = await apiClient.get('/api/autocomplete/owner-cities', { params })
    return response.data
  },

  getOwnerStates: async (filters?: {
    municipality?: string
    unitType?: string
    zoning?: string
    propertyAge?: string
    timeSinceSale?: string
    annualTax?: string
    ownerCity?: string
  }): Promise<string[]> => {
    const params: any = {}
    if (filters?.municipality) params.municipality = filters.municipality
    if (filters?.unitType) params.unit_type = filters.unitType
    if (filters?.zoning) params.zoning = filters.zoning
    if (filters?.propertyAge) params.property_age = filters.propertyAge
    if (filters?.timeSinceSale) params.time_since_sale = filters.timeSinceSale
    if (filters?.annualTax) params.annual_tax = filters.annualTax
    if (filters?.ownerCity) params.owner_city = filters.ownerCity
    const response = await apiClient.get('/api/autocomplete/owner-states', { params })
    return response.data
  },

  getOwnerAddressSuggestions: async (query: string, filters?: {
    municipality?: string
    unitType?: string
    zoning?: string
    propertyAge?: string
    timeSinceSale?: string
    annualTax?: string
    ownerCity?: string
    ownerState?: string
  }): Promise<string[]> => {
    if (!query || query.length < 1) return []
    const params: any = { q: query, limit: 10 }
    if (filters?.municipality) params.municipality = filters.municipality
    if (filters?.unitType) params.unit_type = filters.unitType
    if (filters?.zoning) params.zoning = filters.zoning
    if (filters?.propertyAge) params.property_age = filters.propertyAge
    if (filters?.timeSinceSale) params.time_since_sale = filters.timeSinceSale
    if (filters?.annualTax) params.annual_tax = filters.annualTax
    if (filters?.ownerCity) params.owner_city = filters.ownerCity
    if (filters?.ownerState) params.owner_state = filters.ownerState
    const response = await apiClient.get('/api/autocomplete/owner-addresses', { params })
    return response.data
  },

  /** Main autocomplete with rich suggestions (type, value, display, count) for SearchBar-style dropdown.
   * municipality: optional comma-separated towns to scope suggestions to selected town(s). */
  getAutocompleteSuggestions: async (
    q: string,
    searchType: string,
    limit: number = 10,
    signal?: AbortSignal,
    municipality?: string | null
  ): Promise<{ suggestions: Array<{ type: string; value: string; display: string; count?: number }> }> => {
    if (!q || q.length < 2) return { suggestions: [] }
    const params: Record<string, string | number> = { q, limit, search_type: searchType }
    if (municipality && municipality.trim()) params.municipality = municipality.trim()
    const response = await apiClient.get('/api/autocomplete/', {
      params,
      signal,
    })
    return { suggestions: response.data?.suggestions ?? [] }
  },
}

export const exportApi = {
  exportCSV: async (params: {
    filter_type?: string
    min_equity?: number
    municipality?: string
    property_type?: string
    include_vacant?: boolean
    include_absentee?: boolean
    min_value?: number
    max_value?: number
    min_lot_size?: number
    max_lot_size?: number
  }): Promise<Blob> => {
    console.log('📤 [Export API] exportCSV called with params:', params)
    
    // #region agent log
    try {
      await (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client.ts:500',message:'exportCSV API call',data:{params},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
    } catch (e) {
      console.warn('Debug log failed:', e)
    }
    // #endregion
    
    const response = await apiClient.get('/api/export/csv', {
      params,
      responseType: 'blob',
    })
    
    console.log('📥 [Export API] exportCSV response:', { status: response.status, blobSize: response.data?.size, blobType: response.data?.type })
    
    // #region agent log
    try {
      await (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client.ts:506',message:'exportCSV response',data:{status:response.status,blobSize:response.data?.size,blobType:response.data?.type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
    } catch (e) {
      console.warn('Debug log failed:', e)
    }
    // #endregion
    
    return response.data
  },

  exportJSON: async (params: {
    filter_type?: string
    min_equity?: number
    municipality?: string
    property_type?: string
    include_vacant?: boolean
    include_absentee?: boolean
    limit?: number
    min_value?: number
    max_value?: number
    min_lot_size?: number
    max_lot_size?: number
  }): Promise<Blob> => {
    // #region agent log
    (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client.ts:520',message:'exportJSON API call',data:{params},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
    // #endregion
    const response = await apiClient.get('/api/export/json', {
      params,
      responseType: 'blob',
    });
    // #region agent log
    (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client.ts:526',message:'exportJSON response',data:{status:response.status,blobSize:response.data?.size,blobType:response.data?.type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
    // #endregion
    return response.data
  },

  exportExcel: async (params: {
    filter_type?: string
    min_equity?: number
    municipality?: string
    property_type?: string
    include_vacant?: boolean
    include_absentee?: boolean
    min_value?: number
    max_value?: number
    min_lot_size?: number
    max_lot_size?: number
  }): Promise<Blob> => {
    console.log('📤 [Export API] exportExcel called with params:', params)
    
    // #region agent log
    try {
      await (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client.ts:539',message:'exportExcel API call',data:{params},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
    } catch (e) {
      console.warn('Debug log failed:', e)
    }
    // #endregion
    
    const response = await apiClient.get('/api/export/excel', {
      params,
      responseType: 'blob',
    })
    
    console.log('📥 [Export API] exportExcel response:', { status: response.status, blobSize: response.data?.size, blobType: response.data?.type })
    
    // Check if response is an error (blob might contain error JSON)
    if (response.status >= 400) {
      // Clone the blob before reading it (reading consumes it)
      const blobClone = response.data.slice()
      const errorText = await blobClone.text()
      console.error('❌ [Export API] exportExcel error response:', errorText)
      // #region agent log
      try {
        await (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client.ts:550',message:'exportExcel error',data:{status:response.status,errorText},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
      } catch (e) {
        console.warn('Debug log failed:', e)
      }
      // #endregion
      throw new Error(`Export failed: ${response.status} ${response.statusText || 'Error'}`)
    }
    
    // #region agent log
    try {
      await (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'client.ts:545',message:'exportExcel response',data:{status:response.status,blobSize:response.data?.size,blobType:response.data?.type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
    } catch (e) {
      console.warn('Debug log failed:', e)
    }
    // #endregion
    
    return response.data
  },

  getPropertyComments: async (propertyId: number): Promise<Comment[]> => {
    const response = await apiClient.get(`/api/properties/${propertyId}/comments`)
    return response.data
  },

  createPropertyComment: async (propertyId: number, comment: string): Promise<Comment> => {
    const response = await apiClient.post(`/api/properties/${propertyId}/comments`, { comment })
    return response.data
  },

  updatePropertyComment: async (propertyId: number, commentId: number, comment: string): Promise<Comment> => {
    const response = await apiClient.put(`/api/properties/${propertyId}/comments/${commentId}`, { comment })
    return response.data
  },
}

export const analyticsApi = {
  trackSearch: async (event: {
    query?: string
    filter_type?: string
    municipality?: string
    result_count: number
  }): Promise<void> => {
    await apiClient.post('/api/analytics/track-search', event)
  },

  trackMapLoad: async (event: {
    map_type?: string
    viewport?: {
      center?: [number, number]
      zoom?: number
      bounds?: { north: number; south: number; east: number; west: number }
    }
    fallback_reason?: string
  }): Promise<void> => {
    await apiClient.post('/api/analytics/track-map-load', event).catch(() => {
      // Silently fail if analytics tracking fails
    })
  },

  getStats: async (days: number = 7) => {
    const response = await apiClient.get('/api/analytics/stats', {
      params: { days },
    })
    return response.data
  },

  getPopularSearches: async (days: number = 7) => {
    const response = await apiClient.get('/api/analytics/popular-searches', {
      params: { days },
    })
    return response.data
  },

  getMapUsage: async (days: number = 30) => {
    const response = await apiClient.get('/api/analytics/map-usage', {
      params: { days },
    })
    return response.data
  },
}
