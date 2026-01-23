/**
 * Safe Property Hook - Provides type-safe property access with defaults
 * 
 * Use this hook when working with property data to ensure safety
 */

import { useMemo } from 'react'
import { Property, PropertyNormalizer } from '../types/property'
import { DevelopmentSafety } from '../utils/developmentSafety'
import { migratePropertyData } from '../utils/dataMigration'

/**
 * Hook for safely accessing property data
 */
export function useSafeProperty(property: Property | any) {
  return useMemo(() => {
    // Validate in development
    DevelopmentSafety.validatePropertyBeforeRender(property, 'useSafeProperty')
    
    // Migrate data if needed
    const migrated = migratePropertyData(property)
    
    // Normalize to ensure type safety
    const normalized = PropertyNormalizer.normalize(migrated)
    
    // Create safe getter function
    const getSafe = (field: string, defaultValue: any = null) => {
      return PropertyNormalizer.getSafeValue(normalized, field, defaultValue)
    }
    
    // Create safe card data
    const cardData = PropertyNormalizer.toCardData(normalized)
    
    // Validation result
    const validation = PropertyNormalizer.validate(normalized)
    
    return {
      property: normalized,
      cardData,
      getSafe,
      isValid: validation.isValid,
      validation,
    }
  }, [property])
}
