import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { healthCheckService } from '../services/healthCheck'

// Use relative URLs to go through Vite proxy, or use env variable if set
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
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

  // Retry on 5xx server errors
  if (error.response.status >= 500) {
    return true
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

// Add request interceptor with retry logic
apiClient.interceptors.request.use(
  async (config) => {
    // Check backend health before making request (non-blocking)
    const healthStatus = healthCheckService.getStatus()
    if (!healthStatus.isHealthy && Date.now() - healthStatus.lastChecked > 5000) {
      // Backend might be down, check health in background
      healthCheckService.checkHealth().catch(() => {})
    }

    // Add retry count to config if not present
    if (!(config as any).__retryCount) {
      (config as any).__retryCount = 0
    }

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
    
      // Normalize property data in responses for type safety
      if (response.data && typeof response.data === 'object') {
        // Normalize properties array
        if (Array.isArray(response.data.properties)) {
          response.data.properties = response.data.properties.map((prop: any) => {
            // Migrate data if needed
            const migrated = migratePropertyData(prop)
            // Normalize to ensure type safety
            return PropertyNormalizer.normalize(migrated)
          })
        }
        
        // Normalize single property
        if (response.data.id || response.data.parcel_id) {
          const migrated = migratePropertyData(response.data)
          response.data = PropertyNormalizer.normalize(migrated)
        }
        
        // Validate in development
        if (import.meta.env.DEV) {
          DevelopmentSafety.validateAPIResponse(
            response.config.url || '',
            response.data,
            {} // Expected structure - will be validated by PropertyNormalizer
          )
        }
      }
    
    return response
  },
  async (error: AxiosError) => {
    const config = error.config as InternalAxiosRequestConfig & { __retryCount?: number }
    
    // Initialize retry count if not present
    if (!config.__retryCount) {
      config.__retryCount = 0
    }

    // Check if we should retry
    if (config.__retryCount < MAX_RETRIES && isRetryableError(error)) {
      config.__retryCount += 1
      const delay = getRetryDelay(config.__retryCount)

      console.log(`🔄 Retrying request (${config.__retryCount}/${MAX_RETRIES}) after ${delay}ms:`, config.url)

      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, delay))

      // Check backend health before retry
      try {
        await healthCheckService.checkHealth()
      } catch {
        // Health check failed, but continue with retry anyway
      }

      // Retry the request
      return apiClient(config)
    }

    // No more retries or non-retryable error
    console.error('❌ API Response Error:', {
      message: error.message,
      url: config?.url,
      method: config?.method,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      retries: config.__retryCount,
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

export const propertyApi = {
  getProperty: async (id: number): Promise<PropertyDetail> => {
    const response = await apiClient.get(`/api/properties/${id}`)
    return response.data
  },

  getPropertyByParcel: async (parcelId: string): Promise<PropertyDetail> => {
    const response = await apiClient.get(`/api/properties/parcel/${parcelId}`)
    return response.data
  },

  search: async (params: {
    q?: string
    municipality?: string
    min_value?: number
    max_value?: number
    property_type?: string
    min_lot_size?: number
    max_lot_size?: number
    bbox?: string
    page?: number
    page_size?: number
  }): Promise<SearchResponse> => {
    const response = await apiClient.get('/api/search/', { params })
    return response.data
  },

  getHighEquity: async (params: {
    min_equity?: number
    min_equity_percent?: number
    page?: number
    page_size?: number
  }): Promise<FilterResponse> => {
    const response = await apiClient.get('/api/filters/high-equity', { params })
    return response.data
  },

  getVacant: async (params: {
    include_lots?: boolean
    include_structures?: boolean
    page?: number
    page_size?: number
  }): Promise<FilterResponse> => {
    const response = await apiClient.get('/api/filters/vacant', { params })
    return response.data
  },

  getAbsenteeOwners: async (params: {
    page?: number
    page_size?: number
  }): Promise<FilterResponse> => {
    const response = await apiClient.get('/api/filters/absentee-owners', { params })
    return response.data
  },

  getRecentlySold: async (params: {
    days?: number
    min_price?: number
    max_price?: number
    page?: number
    page_size?: number
  }): Promise<FilterResponse> => {
    const response = await apiClient.get('/api/filters/recently-sold', { params })
    return response.data
  },

  getLowEquity: async (params: {
    max_equity?: number
    page?: number
    page_size?: number
  }): Promise<FilterResponse> => {
    const response = await apiClient.get('/api/filters/low-equity', { params })
    return response.data
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
    const response = await apiClient.get('/api/export/csv', {
      params,
      responseType: 'blob',
    })
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
    const response = await apiClient.get('/api/export/json', {
      params,
      responseType: 'blob',
    })
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
    const response = await apiClient.get('/api/export/excel', {
      params,
      responseType: 'blob',
    })
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
}
