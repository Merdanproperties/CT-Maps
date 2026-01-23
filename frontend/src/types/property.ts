/**
 * Type-Safe Property Data Models
 * 
 * This file defines all property-related types with validation and backward compatibility.
 * When adding new fields, always make them optional and provide defaults.
 */

/**
 * Base property interface - all properties must have these fields
 */
export interface PropertyBase {
  id: number
  parcel_id: string
  address: string | null
  city: string | null
  municipality: string | null
  zip_code: string | null
  geometry: {
    type: string
    geometry: any
  }
}

/**
 * Core property data - commonly used fields
 */
export interface PropertyCore extends PropertyBase {
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
}

/**
 * Extended property data - additional fields that may not always be present
 */
export interface PropertyExtended extends PropertyCore {
  // Owner details
  owner_address?: string | null
  owner_city?: string | null
  owner_state?: string | null
  
  // Building details
  building_area_sqft?: number | null
  bedrooms?: number | null
  bathrooms?: number | null
  
  // Sales history
  sales_count?: number
  days_since_sale?: number | null
  sales?: Array<{
    sale_date: string | null
    sale_price: number
    buyer_name: string | null
    seller_name: string | null
    deed_type: string | null
  }>
  
  // Tax Information
  tax_amount?: number | null
  tax_year?: number | null
  tax_exemptions?: string | null
  assessment_year?: number | null
  
  // Building Exterior Details
  exterior_walls?: string | null
  roof_type?: string | null
  roof_material?: string | null
  foundation_type?: string | null
  exterior_finish?: string | null
  garage_type?: string | null
  garage_spaces?: number | null
  
  // Building Interior Details
  interior_finish?: string | null
  heating_type?: string | null
  cooling_type?: string | null
  fireplace_count?: number | null
  stories?: number | null
  total_rooms?: number | null
  
  // Property Images
  images?: Array<{
    url: string
    source: string
    description?: string
  }>
  
  // Additional data (flexible for future additions)
  additional_data?: any
}

/**
 * Property type with all possible fields
 * Use this when you need to handle any property data
 */
export type Property = PropertyExtended

/**
 * Property detail type - used for detailed property views
 */
export interface PropertyDetail extends PropertyExtended {
  // Any additional detail-specific fields can go here
}

/**
 * Property card display data
 * Only includes fields needed for card display
 */
export interface PropertyCardData {
  id: number
  parcel_id: string
  address: string | null
  city: string | null
  municipality: string | null
  zip_code: string | null
  owner_name: string | null
  assessed_value: number | null
  property_type: string | null
  lot_size_sqft: number | null
  equity_estimate: number | null
  is_absentee: number
  is_vacant: number
  // Add new card fields here as optional
  [key: string]: any // Allow additional fields for future expansion
}

/**
 * Property validation result
 */
export interface PropertyValidationResult {
  isValid: boolean
  errors: string[]
  warnings: string[]
  missingFields: string[]
}

/**
 * Property data normalizer - ensures data consistency
 */
export class PropertyNormalizer {
  /**
   * Normalize property data to ensure all fields have expected types
   */
  static normalize(property: any): Property {
    return {
      // Required fields
      id: Number(property.id) || 0,
      parcel_id: String(property.parcel_id || ''),
      address: property.address || null,
      city: property.city || null,
      municipality: property.municipality || null,
      zip_code: property.zip_code || null,
      
      // Owner fields
      owner_name: property.owner_name || null,
      owner_phone: property.owner_phone || null,
      owner_email: property.owner_email || null,
      owner_address: property.owner_address || null,
      owner_city: property.owner_city || null,
      owner_state: property.owner_state || null,
      
      // Value fields
      assessed_value: property.assessed_value != null ? Number(property.assessed_value) : null,
      land_value: property.land_value != null ? Number(property.land_value) : null,
      building_value: property.building_value != null ? Number(property.building_value) : null,
      equity_estimate: property.equity_estimate != null ? Number(property.equity_estimate) : null,
      
      // Property details
      property_type: property.property_type || null,
      land_use: property.land_use || null,
      lot_size_sqft: property.lot_size_sqft != null ? Number(property.lot_size_sqft) : null,
      year_built: property.year_built != null ? Number(property.year_built) : null,
      building_area_sqft: property.building_area_sqft != null ? Number(property.building_area_sqft) : null,
      bedrooms: property.bedrooms != null ? Number(property.bedrooms) : null,
      bathrooms: property.bathrooms != null ? Number(property.bathrooms) : null,
      
      // Sale information
      last_sale_date: property.last_sale_date || null,
      last_sale_price: property.last_sale_price != null ? Number(property.last_sale_price) : null,
      sales_count: property.sales_count != null ? Number(property.sales_count) : 0,
      days_since_sale: property.days_since_sale != null ? Number(property.days_since_sale) : null,
      sales: property.sales || [],
      
      // Flags
      is_absentee: property.is_absentee != null ? Number(property.is_absentee) : 0,
      is_vacant: property.is_vacant != null ? Number(property.is_vacant) : 0,
      
      // Geometry
      geometry: property.geometry || { type: 'Feature', geometry: null },
      
      // Tax Information
      tax_amount: property.tax_amount != null ? Number(property.tax_amount) : null,
      tax_year: property.tax_year != null ? Number(property.tax_year) : null,
      tax_exemptions: property.tax_exemptions || null,
      assessment_year: property.assessment_year != null ? Number(property.assessment_year) : null,
      
      // Building Exterior Details
      exterior_walls: property.exterior_walls || null,
      roof_type: property.roof_type || null,
      roof_material: property.roof_material || null,
      foundation_type: property.foundation_type || null,
      exterior_finish: property.exterior_finish || null,
      garage_type: property.garage_type || null,
      garage_spaces: property.garage_spaces != null ? Number(property.garage_spaces) : null,
      
      // Building Interior Details
      interior_finish: property.interior_finish || null,
      heating_type: property.heating_type || null,
      cooling_type: property.cooling_type || null,
      fireplace_count: property.fireplace_count != null ? Number(property.fireplace_count) : null,
      stories: property.stories != null ? Number(property.stories) : null,
      total_rooms: property.total_rooms != null ? Number(property.total_rooms) : null,
      
      // Property Images
      images: property.images || [],
      
      // Additional data
      additional_data: property.additional_data || null,
    }
  }

  /**
   * Validate property data
   */
  static validate(property: any): PropertyValidationResult {
    const errors: string[] = []
    const warnings: string[] = []
    const missingFields: string[] = []

    // Required fields
    if (!property.id) errors.push('Missing required field: id')
    if (!property.parcel_id) errors.push('Missing required field: parcel_id')
    if (!property.geometry) errors.push('Missing required field: geometry')

    // Type validation
    if (property.id && isNaN(Number(property.id))) {
      errors.push('Invalid type for id: must be a number')
    }

    if (property.assessed_value != null && isNaN(Number(property.assessed_value))) {
      warnings.push('assessed_value is not a valid number')
    }

    // Warnings for missing optional but commonly used fields
    if (!property.address) warnings.push('Missing address (commonly used field)')
    if (!property.municipality) warnings.push('Missing municipality (commonly used field)')

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      missingFields,
    }
  }

  /**
   * Convert property to card data format
   */
  static toCardData(property: Property): PropertyCardData {
    const normalized = this.normalize(property)
    
    return {
      id: normalized.id,
      parcel_id: normalized.parcel_id,
      address: normalized.address,
      city: normalized.city,
      municipality: normalized.municipality,
      zip_code: normalized.zip_code,
      owner_name: normalized.owner_name,
      assessed_value: normalized.assessed_value,
      property_type: normalized.property_type,
      lot_size_sqft: normalized.lot_size_sqft,
      equity_estimate: normalized.equity_estimate,
      is_absentee: normalized.is_absentee,
      is_vacant: normalized.is_vacant,
      // Include any additional fields that might be added in the future
      ...(normalized as any),
    }
  }

  /**
   * Check if property has all required fields for display
   */
  static isDisplayable(property: any): boolean {
    const validation = this.validate(property)
    return validation.isValid
  }

  /**
   * Get safe default value for a field
   */
  static getSafeValue(property: any, field: string, defaultValue: any = null): any {
    const normalized = this.normalize(property)
    return (normalized as any)[field] ?? defaultValue
  }
}
