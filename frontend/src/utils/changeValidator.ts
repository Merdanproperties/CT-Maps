/**
 * Change Validator - Validates changes before they break the application
 * 
 * This utility helps ensure backward compatibility when making changes
 */

export interface ChangeValidationResult {
  isValid: boolean
  warnings: string[]
  errors: string[]
  breakingChanges: string[]
  recommendations: string[]
}

export interface PropertyDataChange {
  field: string
  oldType?: string
  newType?: string
  required?: boolean
  defaultValue?: any
}

export class ChangeValidator {
  /**
   * Validate that new property data structure is compatible
   */
  static validatePropertyDataChange(
    oldData: any,
    newData: any,
    changes: PropertyDataChange[]
  ): ChangeValidationResult {
    const warnings: string[] = []
    const errors: string[] = []
    const breakingChanges: string[] = []
    const recommendations: string[] = []

    // Check for removed required fields
    changes.forEach(change => {
      if (change.required && oldData[change.field] && !newData[change.field]) {
        errors.push(`Required field '${change.field}' was removed`)
        breakingChanges.push(`Removed required field: ${change.field}`)
      }
    })

    // Check for type changes
    changes.forEach(change => {
      if (change.oldType && change.newType && change.oldType !== change.newType) {
        const oldValue = oldData[change.field]
        if (oldValue != null) {
          const canConvert = this.canConvertType(oldValue, change.oldType, change.newType)
          if (!canConvert) {
            errors.push(`Type change for '${change.field}' from ${change.oldType} to ${change.newType} may break existing data`)
            breakingChanges.push(`Type change: ${change.field}`)
          } else {
            warnings.push(`Type change for '${change.field}' - ensure data migration`)
            recommendations.push(`Add data migration for ${change.field} field`)
          }
        }
      }
    })

    // Check for new required fields without defaults
    changes.forEach(change => {
      if (change.required && !change.defaultValue && !oldData[change.field]) {
        warnings.push(`New required field '${change.field}' has no default value`)
        recommendations.push(`Add default value for ${change.field} or make it optional`)
      }
    })

    return {
      isValid: errors.length === 0,
      warnings,
      errors,
      breakingChanges,
      recommendations,
    }
  }

  /**
   * Check if a value can be converted between types
   */
  private static canConvertType(value: any, fromType: string, toType: string): boolean {
    // Safe conversions
    const safeConversions: Record<string, string[]> = {
      'string': ['number', 'boolean'], // "123" -> 123, "true" -> true
      'number': ['string'], // 123 -> "123"
      'null': ['string', 'number', 'boolean'], // null -> any
    }

    if (fromType === toType) return true
    if (safeConversions[fromType]?.includes(toType)) return true
    if (fromType === 'null' || value === null) return true // null can become anything

    return false
  }

  /**
   * Validate component props changes
   */
  static validateComponentProps(
    componentName: string,
    oldProps: Record<string, any>,
    newProps: Record<string, any>
  ): ChangeValidationResult {
    const warnings: string[] = []
    const errors: string[] = []
    const breakingChanges: string[] = []
    const recommendations: string[] = []

    // Check for removed props
    Object.keys(oldProps).forEach(prop => {
      if (!(prop in newProps)) {
        warnings.push(`Prop '${prop}' removed from ${componentName}`)
        recommendations.push(`Make ${prop} optional or provide default in ${componentName}`)
      }
    })

    // Check for new required props
    Object.keys(newProps).forEach(prop => {
      if (!(prop in oldProps) && newProps[prop] === undefined) {
        warnings.push(`New prop '${prop}' in ${componentName} has no default`)
        recommendations.push(`Add default value for ${prop} prop in ${componentName}`)
      }
    })

    return {
      isValid: errors.length === 0,
      warnings,
      errors,
      breakingChanges,
      recommendations,
    }
  }

  /**
   * Validate API response structure
   */
  static validateAPIResponse(
    endpoint: string,
    expectedFields: string[],
    actualResponse: any
  ): ChangeValidationResult {
    const warnings: string[] = []
    const errors: string[] = []
    const breakingChanges: string[] = []
    const recommendations: string[] = []

    expectedFields.forEach(field => {
      if (!(field in actualResponse)) {
        errors.push(`Expected field '${field}' missing from ${endpoint} response`)
        breakingChanges.push(`Missing field: ${field} in ${endpoint}`)
      }
    })

    // Check for unexpected new fields (usually OK, but log as info)
    // If expectedFields is empty, accept all fields (flexible schema)
    if (expectedFields.length > 0) {
      Object.keys(actualResponse).forEach(field => {
        if (!expectedFields.includes(field)) {
          warnings.push(`Unexpected field '${field}' in ${endpoint} response`)
        }
      })
    }

    return {
      isValid: errors.length === 0,
      warnings,
      errors,
      breakingChanges,
      recommendations,
    }
  }
}
