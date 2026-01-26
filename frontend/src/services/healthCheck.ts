import { apiClient } from '../api/client'
import { serviceManager } from './serviceManager'

export interface HealthStatus {
  isHealthy: boolean
  lastChecked: number
  error?: string
  database?: string
  api?: string
}

class HealthCheckService {
  private healthStatus: HealthStatus = {
    isHealthy: false,
    lastChecked: 0,
  }
  private checkInterval: number | null = null
  private listeners: Array<(status: HealthStatus) => void> = []
  private healthCache: { status: HealthStatus; timestamp: number } | null = null
  private readonly CHECK_INTERVAL = 10000 // Check every 10 seconds (reduced frequency)
  private readonly HEALTH_CHECK_TIMEOUT = 8000 // 8 second timeout (increased from 3)
  private readonly CACHE_DURATION = 3000 // Cache successful checks for 3 seconds

  /**
   * Check if backend is healthy
   */
  async checkHealth(useCache: boolean = true): Promise<HealthStatus> {
    // Check cache first if enabled
    if (useCache && this.healthCache) {
      const cacheAge = Date.now() - this.healthCache.timestamp
      if (cacheAge < this.CACHE_DURATION && this.healthCache.status.isHealthy) {
        // Return cached healthy status
        return { ...this.healthCache.status }
      }
    }

    try {
      // Progressive timeout strategy: try with shorter timeout first, then longer
      let response: Response | null = null
      let lastError: any = null
      
      // First attempt with shorter timeout (4 seconds)
      const shortTimeout = 4000
      try {
        const controller1 = new AbortController()
        const timeoutId1 = setTimeout(() => controller1.abort(), shortTimeout)
        
        response = await fetch('/health', {
          method: 'GET',
          signal: controller1.signal,
          headers: {
            'Content-Type': 'application/json',
            'Connection': 'keep-alive',
          },
        })
        
        clearTimeout(timeoutId1)
      } catch (error: any) {
        if (error.name === 'AbortError') {
          // Short timeout failed, try with full timeout
          lastError = error
          const controller2 = new AbortController()
          const timeoutId2 = setTimeout(() => controller2.abort(), this.HEALTH_CHECK_TIMEOUT)
          
          try {
            response = await fetch('/health', {
              method: 'GET',
              signal: controller2.signal,
              headers: {
                'Content-Type': 'application/json',
                'Connection': 'keep-alive',
              },
            })
            clearTimeout(timeoutId2)
          } catch (error2: any) {
            clearTimeout(timeoutId2)
            throw error2
          }
        } else {
          throw error
        }
      }
      
      if (!response) {
        throw lastError || new Error('No response received')
      }

      const isHealthy = response.ok
      let healthData: any = {}
      
      if (isHealthy) {
        try {
          healthData = await response.json()
        } catch {
          // If JSON parsing fails, use default
        }
      }
      
      const dbStatus = healthData.database || 'unknown'
      const isFullyHealthy = isHealthy && dbStatus === 'connected'
      
      this.healthStatus = {
        isHealthy: isFullyHealthy,
        lastChecked: Date.now(),
        error: isFullyHealthy ? undefined : 
          isHealthy ? `Database status: ${dbStatus}` : 
          `Backend returned status ${response.status}`,
        database: dbStatus,
        api: healthData.api || 'unknown',
      }
      
      // Cache successful health checks
      if (isFullyHealthy) {
        this.healthCache = {
          status: { ...this.healthStatus },
          timestamp: Date.now()
        }
        serviceManager.resetFailureCount()
      } else {
        // Clear cache on failure
        this.healthCache = null
        // Trigger recovery if unhealthy
        serviceManager.attemptRecovery(this.healthStatus).catch(() => {})
      }
    } catch (error: any) {
      this.healthStatus = {
        isHealthy: false,
        lastChecked: Date.now(),
        error: error.name === 'AbortError' 
          ? 'Backend connection timeout - server may be slow or unreachable'
          : error.message || 'Backend is not responding',
      }
    }

    this.notifyListeners()
    return this.healthStatus
  }

  /**
   * Start continuous health monitoring
   */
  startMonitoring(): void {
    if (this.checkInterval !== null) {
      return // Already monitoring
    }

    // Check immediately
    this.checkHealth()

    // Then check periodically
    this.checkInterval = window.setInterval(() => {
      this.checkHealth()
    }, this.CHECK_INTERVAL)
  }

  /**
   * Stop health monitoring
   */
  stopMonitoring(): void {
    if (this.checkInterval !== null) {
      clearInterval(this.checkInterval)
      this.checkInterval = null
    }
  }

  /**
   * Get current health status
   */
  getStatus(): HealthStatus {
    return { ...this.healthStatus }
  }

  /**
   * Subscribe to health status changes
   */
  subscribe(listener: (status: HealthStatus) => void): () => void {
    this.listeners.push(listener)
    // Immediately notify with current status
    listener(this.healthStatus)

    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener)
    }
  }

  private notifyListeners(): void {
    this.listeners.forEach(listener => {
      try {
        listener(this.healthStatus)
      } catch (error) {
        console.error('Error notifying health check listener:', error)
      }
    })
  }

  /**
   * Wait for backend to be healthy (with timeout)
   */
  async waitForHealthy(timeout: number = 30000): Promise<boolean> {
    const startTime = Date.now()

    while (Date.now() - startTime < timeout) {
      const status = await this.checkHealth()
      if (status.isHealthy) {
        return true
      }
      // Wait 1 second before next check
      await new Promise(resolve => setTimeout(resolve, 1000))
    }

    return false
  }
}

// Export singleton instance
export const healthCheckService = new HealthCheckService()
