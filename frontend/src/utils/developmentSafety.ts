/**
 * Development Safety Checks
 * 
 * Validates changes in development to prevent breaking production
 */

import { PropertyNormalizer } from '../types/property'
import { ChangeValidator } from './changeValidator'

export class DevelopmentSafety {
  private static isDevelopment = import.meta.env.DEV
  private static validationEnabled = true

  /**
   * Validate property data before rendering
   */
  static validatePropertyBeforeRender(property: any, componentName: string): boolean {
    if (!this.isDevelopment || !this.validationEnabled) {
      return true // Skip in production for performance
    }

    // Skip validation for empty objects (loading state)
    if (!property || (typeof property === 'object' && Object.keys(property).length === 0)) {
      return true
    }

    try {
      const validation = PropertyNormalizer.validate(property)
      
      if (!validation.isValid) {
        console.error(`[${componentName}] Property validation failed:`, {
          errors: validation.errors,
          property: property.id || property.parcel_id,
        })
        return false
      }

      if (validation.warnings.length > 0) {
        console.warn(`[${componentName}] Property validation warnings:`, {
          warnings: validation.warnings,
          property: property.id || property.parcel_id,
        })
      }

      return true
    } catch (error) {
      console.error(`[${componentName}] Validation error:`, error)
      return false
    }
  }

  /**
   * Validate API response structure
   */
  static validateAPIResponse(endpoint: string, response: any, expectedStructure: any): boolean {
    if (!this.isDevelopment || !this.validationEnabled) {
      return true
    }

    try {
      // If expectedStructure is empty, skip validation (accept all fields)
      const expectedFields = Object.keys(expectedStructure || {})
      if (expectedFields.length === 0) {
        // Flexible schema - accept all fields without warnings
        return true
      }

      // Check if response has expected structure
      const validation = ChangeValidator.validateAPIResponse(
        endpoint,
        expectedFields,
        response
      )

      if (!validation.isValid) {
        console.error(`[API Validation] ${endpoint} response validation failed:`, validation.errors)
        return false
      }

      if (validation.warnings.length > 0) {
        console.warn(`[API Validation] ${endpoint} response warnings:`, validation.warnings)
      }

      return true
    } catch (error) {
      console.error(`[API Validation] ${endpoint} validation error:`, error)
      return false
    }
  }

  /**
   * Warn about potential breaking changes
   */
  static warnBreakingChange(change: string, impact: string, fix: string): void {
    if (!this.isDevelopment) {
      return
    }

    console.warn(
      `⚠️ POTENTIAL BREAKING CHANGE DETECTED\n` +
      `Change: ${change}\n` +
      `Impact: ${impact}\n` +
      `Fix: ${fix}\n` +
      `\nPlease review before committing.`
    )
  }

  /**
   * Validate component props
   */
  static validateComponentProps(
    componentName: string,
    props: Record<string, any>,
    requiredProps: string[]
  ): boolean {
    if (!this.isDevelopment || !this.validationEnabled) {
      return true
    }

    const missing = requiredProps.filter(prop => !(prop in props) || props[prop] === undefined)
    
    if (missing.length > 0) {
      console.error(`[${componentName}] Missing required props:`, missing)
      return false
    }

    return true
  }

  /**
   * Enable/disable validation (useful for testing)
   */
  static setValidationEnabled(enabled: boolean): void {
    this.validationEnabled = enabled
  }

  /**
   * Check if we're in development mode
   */
  static isDevMode(): boolean {
    return this.isDevelopment
  }
}

// Auto-validate in development
if (import.meta.env.DEV) {
  console.log('🛡️ Development safety checks enabled')
}
