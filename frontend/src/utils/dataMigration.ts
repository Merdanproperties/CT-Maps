/**
 * Data Migration Utilities
 * 
 * Handles data structure changes and migrations between versions
 */

export interface DataMigration {
  version: string
  migrate: (data: any) => any
  validate: (data: any) => boolean
}

class DataMigrationService {
  private migrations: DataMigration[] = []
  private currentVersion = '1.0.0'

  /**
   * Register a migration
   */
  registerMigration(migration: DataMigration): void {
    this.migrations.push(migration)
    // Sort by version
    this.migrations.sort((a, b) => a.version.localeCompare(b.version))
  }

  /**
   * Migrate data to current version
   */
  migrate(data: any, fromVersion?: string): any {
    let migratedData = { ...data }
    let startIndex = 0

    // Find starting migration if version specified
    if (fromVersion) {
      startIndex = this.migrations.findIndex(m => m.version > fromVersion)
      if (startIndex === -1) startIndex = 0
    }

    // Apply all migrations from start
    for (let i = startIndex; i < this.migrations.length; i++) {
      const migration = this.migrations[i]
      try {
        migratedData = migration.migrate(migratedData)
        
        // Validate after migration
        if (!migration.validate(migratedData)) {
          console.warn(`Migration ${migration.version} validation failed, but continuing`)
        }
      } catch (error) {
        console.error(`Migration ${migration.version} failed:`, error)
        // Return data as-is if migration fails
        return data
      }
    }

    return migratedData
  }

  /**
   * Get current data version
   */
  getCurrentVersion(): string {
    return this.currentVersion
  }

  /**
   * Detect data version from structure
   */
  detectVersion(data: any): string {
    // Check for version field
    if (data._version) {
      return data._version
    }

    // Detect version by structure
    if (data.additional_data && typeof data.additional_data === 'object') {
      return '1.1.0' // Has additional_data structure
    }

    return '1.0.0' // Default/legacy version
  }
}

export const dataMigrationService = new DataMigrationService()

// Register default migrations
dataMigrationService.registerMigration({
  version: '1.1.0',
  migrate: (data: any) => {
    // Migration: Ensure additional_data field exists
    if (!data.additional_data) {
      data.additional_data = {}
    }
    data._version = '1.1.0'
    return data
  },
  validate: (data: any) => {
    return data.additional_data !== undefined
  },
})

/**
 * Migrate property data to current version
 */
export function migratePropertyData(property: any): any {
  const version = dataMigrationService.detectVersion(property)
  return dataMigrationService.migrate(property, version)
}
