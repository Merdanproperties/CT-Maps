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
    isHealthy: true,
    lastChecked: 0,
    error: undefined,
  }
  private checkInterval: number | null = null
  private listeners: Array<(status: HealthStatus) => void> = []
  private healthCache: { status: HealthStatus; timestamp: number } | null = null
  private lastRecoveryTrigger = 0
  private checkInProgress = false
  private consecutiveFailures = 0
  private readonly HEALTH_CHECK_TIMEOUT = 20000 // 20s for single initial check
  private readonly CACHE_DURATION = 5000 // Cache successful checks for 5 seconds
  private readonly RECOVERY_TRIGGER_COOLDOWN = 20000 // Only trigger recovery at most every 20s to avoid loop

  /**
   * Check if backend is healthy
   */
  async checkHealth(useCache: boolean = true): Promise<HealthStatus> {
    // Single in-flight: avoid overlapping health checks (prevents 200+ requests when backend is down)
    if (this.checkInProgress) {
      return {
        ...this.healthStatus,
        error: 'Connection check in progress',
      }
    }
    // Check cache first if enabled (backend reachable = isHealthy)
    if (useCache && this.healthCache) {
      const cacheAge = Date.now() - this.healthCache.timestamp
      if (cacheAge < this.CACHE_DURATION && this.healthCache.status.isHealthy) {
        return { ...this.healthCache.status }
      }
    }

    this.checkInProgress = true
    try {
      // Use shallow /health (no DB) so we don't timeout on every refresh when /health/ready is slow
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), this.HEALTH_CHECK_TIMEOUT)
      let response: Response
      try {
        response = await fetch('/health', {
          method: 'GET',
          signal: controller.signal,
          headers: { 'Content-Type': 'application/json' },
        })
        clearTimeout(timeoutId)
      } catch (err: any) {
        clearTimeout(timeoutId)
        throw err
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
      const databaseConnected = dbStatus === 'connected'
      const backendReachable = isHealthy

      this.healthStatus = {
        isHealthy: backendReachable,
        lastChecked: Date.now(),
        error: backendReachable
          ? (databaseConnected ? undefined : dbStatus === 'disconnected' ? `Database status: ${dbStatus}` : undefined)
          : `Backend returned status ${response.status}`,
        database: dbStatus,
        api: healthData.api || 'unknown',
      }
      
      // Cache when backend is reachable so we don't hammer /health
      if (backendReachable) {
        this.consecutiveFailures = 0
        this.healthCache = {
          status: { ...this.healthStatus },
          timestamp: Date.now()
        }
        serviceManager.resetFailureCount()
      } else {
        this.consecutiveFailures += 1
        this.healthCache = null
        const now = Date.now()
        if (now - this.lastRecoveryTrigger >= this.RECOVERY_TRIGGER_COOLDOWN) {
          this.lastRecoveryTrigger = now
          serviceManager.attemptRecovery(this.healthStatus).catch(() => {})
        }
      }
      this.notifyListeners();
      return this.healthStatus;
    } catch (error: any) {
      this.consecutiveFailures += 1
      const timeoutMessage = error.name === 'AbortError'
        ? 'Backend connection timeout - server may be slow or unreachable'
        : error.message || 'Backend is not responding'
      // Don't show scary timeout on first failure; give backend time to respond (e.g. after restart)
      const showTimeout = this.consecutiveFailures >= 2
      this.healthStatus = {
        isHealthy: false,
        lastChecked: Date.now(),
        error: showTimeout ? timeoutMessage : 'Connecting to backend...',
      }
      // Don't trigger recovery on first failure (cold start)
      const wasEverHealthy = this.healthCache !== null || this.consecutiveFailures > 1
      const now = Date.now()
      if (wasEverHealthy && now - this.lastRecoveryTrigger >= this.RECOVERY_TRIGGER_COOLDOWN) {
        this.lastRecoveryTrigger = now
        serviceManager.attemptRecovery(this.healthStatus).catch(() => {})
      }
      this.notifyListeners();
      return this.healthStatus;
    } finally {
      this.checkInProgress = false;
    }
  }

  /**
   * Set backend as healthy (e.g. after a successful API response).
   * Called by API client when a real request succeeds.
   */
  setHealthy(): void {
    if (this.healthStatus.isHealthy) return
    this.consecutiveFailures = 0
    this.healthStatus = {
      isHealthy: true,
      lastChecked: Date.now(),
      error: undefined,
    }
    this.healthCache = { status: { ...this.healthStatus }, timestamp: Date.now() }
    serviceManager.resetFailureCount()
    this.notifyListeners()
  }

  /**
   * Set backend as unhealthy (e.g. after network error on API request).
   * Called by API client when a real request fails with connection/timeout.
   */
  setUnhealthy(message?: string): void {
    this.healthStatus = {
      isHealthy: false,
      lastChecked: Date.now(),
      error: message ?? 'Backend unreachable',
    }
    this.healthCache = null
    this.notifyListeners()
  }

  /**
   * Start continuous health monitoring.
   * Disabled: we no longer poll /health; status is driven by real API success/failure.
   */
  startMonitoring(): void {
    // No-op: no periodic checks to reduce backend load
  }

  /**
   * Stop health monitoring
   */
  stopMonitoring(): void {
    if (this.checkInterval !== null) {
      clearTimeout(this.checkInterval)
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
