import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface Property {
  id: number
  parcel_id: string
  address: string | null
  city: string | null
  municipality: string | null
  zip_code: string | null
  owner_name: string | null
  owner_phone: string | null
  owner_email: string | null
  assessed_value: number | null
  land_value: number | null
  building_value: number | null
  property_type: string | null
  land_use: string | null
  lot_size_sqft: number | null
  year_built: number | null
  last_sale_date: string | null
  last_sale_price: number | null
  is_absentee: number
  is_vacant: number
  equity_estimate: number | null
  geometry: {
    type: string
    geometry: any
  }
}

export interface PropertyDetail extends Property {
  owner_address: string | null
  owner_city: string | null
  owner_state: string | null
  owner_phone: string | null
  owner_email: string | null
  building_area_sqft: number | null
  bedrooms: number | null
  bathrooms: number | null
  sales_count: number
  days_since_sale: number | null
  additional_data: any
  sales: Array<{
    sale_date: string | null
    sale_price: number
    buyer_name: string | null
    seller_name: string | null
    deed_type: string | null
  }>
}

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
  }): Promise<Blob> => {
    const response = await apiClient.get('/api/export/json', {
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
