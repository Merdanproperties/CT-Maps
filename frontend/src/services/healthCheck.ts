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
  private readonly CHECK_INTERVAL = 5000 // Check every 5 seconds
  private readonly HEALTH_CHECK_TIMEOUT = 3000 // 3 second timeout

  /**
   * Check if backend is healthy
   */
  async checkHealth(): Promise<HealthStatus> {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), this.HEALTH_CHECK_TIMEOUT)

      // Use proxied health endpoint
      const response = await fetch('/health', {
        method: 'GET',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
        },
      })

      clearTimeout(timeoutId)

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
      
      // Trigger recovery if unhealthy
      if (!isFullyHealthy) {
        // Service manager will attempt recovery, which may trigger auto-remediation
        serviceManager.attemptRecovery(this.healthStatus).catch(() => {})
      } else {
        serviceManager.resetFailureCount()
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
