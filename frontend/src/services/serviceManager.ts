/**
 * Service Manager - Automatically keeps services running
 * 
 * This service monitors backend health and automatically attempts to recover
 * by restarting services, reconnecting, and maintaining app functionality.
 */

import { healthCheckService, HealthStatus } from './healthCheck'
import { autoRemediationService } from './autoRemediation'

export interface ServiceRecoveryAction {
  type: 'restart' | 'reconnect' | 'fallback' | 'notify'
  timestamp: number
  success: boolean
  error?: string
}

class ServiceManager {
  private recoveryHistory: ServiceRecoveryAction[] = []
  private isRecovering = false
  private consecutiveFailures = 0
  private readonly MAX_CONSECUTIVE_FAILURES = 3
  private readonly RECOVERY_COOLDOWN = 10000 // 10 seconds between recovery attempts
  private lastRecoveryAttempt = 0
  private listeners: Array<(action: ServiceRecoveryAction) => void> = []

  /**
   * Attempt to recover from service failure
   * This will try auto-remediation first, then fall back to manual recovery
   */
  async attemptRecovery(status: HealthStatus): Promise<ServiceRecoveryAction | null> {
    // First, try automatic remediation if we have diagnostic info
    try {
      const diagnostics = await this.getDiagnosticsForHealthStatus(status)
      if (diagnostics && diagnostics.issues.length > 0) {
        const fixResults = await autoRemediationService.autoFix(diagnostics)
        const successfulFixes = fixResults.filter(r => r.success)
        
        if (successfulFixes.length > 0) {
          // Auto-fix succeeded, verify health
          await new Promise(resolve => setTimeout(resolve, 2000))
          const newStatus = await healthCheckService.checkHealth()
          if (newStatus.isHealthy) {
            this.consecutiveFailures = 0
            return {
              type: 'reconnect',
              timestamp: Date.now(),
              success: true,
            }
          }
        }
      }
    } catch (error) {
      // Auto-remediation failed or unavailable, continue with manual recovery
      console.log('Auto-remediation unavailable, using manual recovery')
    }
    // Prevent too frequent recovery attempts
    const now = Date.now()
    if (now - this.lastRecoveryAttempt < this.RECOVERY_COOLDOWN) {
      return null
    }

    if (this.isRecovering) {
      return null
    }

    this.isRecovering = true
    this.lastRecoveryAttempt = now
    this.consecutiveFailures++

    try {
      // Strategy 1: Wait and check if backend recovers on its own
      console.log('🔄 Attempting service recovery...')
      const waitTime = Math.min(2000 * this.consecutiveFailures, 10000) // Max 10 seconds
      await new Promise(resolve => setTimeout(resolve, waitTime))

      // Check if backend recovered
      const newStatus = await healthCheckService.checkHealth()
      if (newStatus.isHealthy) {
        this.consecutiveFailures = 0
        const action: ServiceRecoveryAction = {
          type: 'reconnect',
          timestamp: Date.now(),
          success: true,
        }
        this.recordAction(action)
        return action
      }

      // Strategy 2: Try to reconnect with exponential backoff
      for (let attempt = 1; attempt <= 3; attempt++) {
        const delay = 1000 * Math.pow(2, attempt - 1)
        await new Promise(resolve => setTimeout(resolve, delay))
        
        const checkStatus = await healthCheckService.checkHealth()
        if (checkStatus.isHealthy) {
          this.consecutiveFailures = 0
          const action: ServiceRecoveryAction = {
            type: 'reconnect',
            timestamp: Date.now(),
            success: true,
          }
          this.recordAction(action)
          return action
        }
      }

      // Strategy 3: Notify user and provide instructions
      if (this.consecutiveFailures >= this.MAX_CONSECUTIVE_FAILURES) {
        const action: ServiceRecoveryAction = {
          type: 'notify',
          timestamp: Date.now(),
          success: false,
          error: `Backend has been down for ${this.consecutiveFailures} consecutive checks. Please restart the backend server.`,
        }
        this.recordAction(action)
        return action
      }

      // Strategy 4: Fallback mode - continue with cached data
      const action: ServiceRecoveryAction = {
        type: 'fallback',
        timestamp: Date.now(),
        success: true,
      }
      this.recordAction(action)
      return action

    } catch (error: any) {
      const action: ServiceRecoveryAction = {
        type: 'reconnect',
        timestamp: Date.now(),
        success: false,
        error: error.message,
      }
      this.recordAction(action)
      return action
    } finally {
      this.isRecovering = false
    }
  }

  /**
   * Reset failure counter when service is healthy
   */
  resetFailureCount(): void {
    if (this.consecutiveFailures > 0) {
      console.log('✅ Service recovered, resetting failure count')
      this.consecutiveFailures = 0
    }
  }

  /**
   * Get recovery history
   */
  getRecoveryHistory(): ServiceRecoveryAction[] {
    return [...this.recoveryHistory]
  }

  /**
   * Subscribe to recovery actions
   */
  subscribe(listener: (action: ServiceRecoveryAction) => void): () => void {
    this.listeners.push(listener)
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener)
    }
  }

  private recordAction(action: ServiceRecoveryAction): void {
    this.recoveryHistory.push(action)
    // Keep only last 50 actions
    if (this.recoveryHistory.length > 50) {
      this.recoveryHistory.shift()
    }
    this.notifyListeners(action)
  }

  private notifyListeners(action: ServiceRecoveryAction): void {
    this.listeners.forEach(listener => {
      try {
        listener(action)
      } catch (error) {
        console.error('Error notifying recovery listener:', error)
      }
    })
  }

  /**
   * Get current recovery status
   */
  getStatus(): {
    isRecovering: boolean
    consecutiveFailures: number
    lastRecoveryAttempt: number
  } {
    return {
      isRecovering: this.isRecovering,
      consecutiveFailures: this.consecutiveFailures,
      lastRecoveryAttempt: this.lastRecoveryAttempt,
    }
  }

  /**
   * Get diagnostics for a health status
   */
  private async getDiagnosticsForHealthStatus(status: HealthStatus): Promise<any> {
    // Import diagnostics service dynamically to avoid circular dependencies
    try {
      const { diagnosticsService } = await import('./diagnostics')
      return await diagnosticsService.runDiagnostics()
    } catch {
      return null
    }
  }
}

export const serviceManager = new ServiceManager()
