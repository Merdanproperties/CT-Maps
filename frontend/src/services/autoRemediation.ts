/**
 * Auto-Remediation Service - Automatically fixes issues without user intervention
 * This service can execute fixes for common problems
 */

import { SystemDiagnostics, DiagnosticInfo } from './diagnostics'
import { healthCheckService } from './healthCheck'

export interface RemediationResult {
  success: boolean
  action: string
  message: string
  executedCommands?: string[]
  error?: string
}

class AutoRemediationService {
  /**
   * Attempt to automatically fix detected issues
   */
  async autoFix(diagnostics: SystemDiagnostics): Promise<RemediationResult[]> {
    const results: RemediationResult[] = []

    for (const issue of diagnostics.issues) {
      try {
        const result = await this.fixIssue(issue)
        results.push(result)
      } catch (error: any) {
        results.push({
          success: false,
          action: issue.issue,
          message: `Failed to auto-fix: ${error.message}`,
          error: error.message,
        })
      }
    }

    return results
  }

  /**
   * Fix a specific issue
   */
  async fixIssue(issue: DiagnosticInfo): Promise<RemediationResult> {
    // Map issue types to fix functions
    const fixMap: Record<string, () => Promise<RemediationResult>> = {
      backend_unreachable: () => this.fixBackendUnreachable(),
      backend_unhealthy: () => this.fixBackendUnhealthy(),
      database_disconnected: () => this.fixDatabaseDisconnected(),
      network_error: () => this.fixNetworkError(),
    }

    const fixFunction = fixMap[issue.issue.toLowerCase().replace(/\s+/g, '_')]
    
    if (!fixFunction) {
      // Try to match by issue description
      if (issue.issue.includes('backend') && issue.issue.includes('reachable')) {
        return await this.fixBackendUnreachable()
      }
      if (issue.issue.includes('database')) {
        return await this.fixDatabaseDisconnected()
      }
      if (issue.issue.includes('network')) {
        return await this.fixNetworkError()
      }
    }

    if (fixFunction) {
      return await fixFunction()
    }

    return {
      success: false,
      action: issue.issue,
      message: 'No automatic fix available for this issue. Please use manual steps.',
    }
  }

  /**
   * Fix: Backend unreachable
   */
  private async fixBackendUnreachable(): Promise<RemediationResult> {
    const executedCommands: string[] = []
    
    try {
      // Step 1: Check if backend is actually running
      const healthCheck = await this.checkBackendHealth()
      if (healthCheck) {
        return {
          success: true,
          action: 'Backend Health Check',
          message: 'Backend is actually reachable. Issue may have resolved itself.',
        }
      }

      executedCommands.push('Backend health check failed')
      
      // Step 2: Wait and retry with exponential backoff (backend might be starting)
      for (let attempt = 1; attempt <= 3; attempt++) {
        const delay = 2000 * attempt
        await new Promise(resolve => setTimeout(resolve, delay))
        
        const isHealthy = await healthCheckService.waitForHealthy(5000)
        if (isHealthy) {
          executedCommands.push(`Backend recovered after ${attempt} attempt(s)`)
          return {
            success: true,
            action: 'Backend Recovery',
            message: `Backend recovered after ${attempt} retry attempt(s)`,
            executedCommands,
          }
        }
        executedCommands.push(`Retry attempt ${attempt} failed`)
      }

      // Step 3: Backend is truly down - cannot auto-restart from frontend
      // The watchdog script should handle this, but we'll note it
      return {
        success: false,
        action: 'Backend Recovery',
        message: 'Backend is not reachable. The watchdog script should restart it automatically. If not, run: ./scripts/start_all.sh',
        executedCommands,
      }
    } catch (error: any) {
      return {
        success: false,
        action: 'Backend Recovery',
        message: `Auto-fix failed: ${error.message}`,
        error: error.message,
        executedCommands,
      }
    }
  }

  /**
   * Fix: Backend unhealthy
   */
  private async fixBackendUnhealthy(): Promise<RemediationResult> {
    const executedCommands: string[] = []
    
    try {
      // Step 1: Check health endpoint for diagnostic info
      const response = await fetch('/health', {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      })

      if (response.ok) {
        const health = await response.json()
        
        // If database is disconnected, try to fix that
        if (health.database === 'disconnected') {
          executedCommands.push('Detected database issue, attempting recovery')
          const dbResult = await this.fixDatabaseDisconnected()
          if (dbResult.success) {
            // Wait a bit and check again
            await new Promise(resolve => setTimeout(resolve, 2000))
            const newHealth = await healthCheckService.checkHealth()
            if (newHealth.isHealthy) {
              return {
                success: true,
                action: 'Backend Recovery',
                message: 'Backend recovered after fixing database connection',
                executedCommands: [...executedCommands, ...(dbResult.executedCommands || [])],
              }
            }
          }
        }
      }

      // Step 2: Retry health check
      executedCommands.push('Retrying backend health check')
      const isHealthy = await healthCheckService.waitForHealthy(10000)
      
      if (isHealthy) {
        return {
          success: true,
          action: 'Backend Recovery',
          message: 'Backend recovered after retry',
          executedCommands,
        }
      }

      return {
        success: false,
        action: 'Backend Recovery',
        message: 'Backend did not recover. Please check logs and restart manually.',
        executedCommands,
      }
    } catch (error: any) {
      return {
        success: false,
        action: 'Backend Recovery',
        message: `Auto-fix failed: ${error.message}`,
        error: error.message,
        executedCommands,
      }
    }
  }

  /**
   * Fix: Database disconnected
   */
  private async fixDatabaseDisconnected(): Promise<RemediationResult> {
    const executedCommands: string[] = []
    
    try {
      // Step 1: Try backend remediation API first
      try {
        const response = await fetch('/api/remediation/reconnect-database', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: AbortSignal.timeout(10000),
        })
        
        if (response.ok) {
          const result = await response.json()
          executedCommands.push(...(result.executed_commands || []))
          
          if (result.success) {
            // Verify it worked
            await new Promise(resolve => setTimeout(resolve, 2000))
            const healthCheck = await healthCheckService.checkHealth()
            if (healthCheck.database === 'connected') {
              return {
                success: true,
                action: 'Database Recovery',
                message: result.message || 'Database connection recovered',
                executedCommands,
              }
            }
          }
        }
      } catch (apiError) {
        executedCommands.push('Backend remediation API unavailable, using fallback')
      }

      // Step 2: Fallback - Trigger backend database reconnection via health check
      executedCommands.push('Triggering backend database reconnection')
      
      const response = await fetch('/health', {
        method: 'GET',
        signal: AbortSignal.timeout(10000),
      })

      if (response.ok) {
        const health = await response.json()
        if (health.database === 'connected') {
          return {
            success: true,
            action: 'Database Recovery',
            message: 'Database connection recovered automatically',
            executedCommands,
          }
        }
      }

      // Step 3: Wait and retry
      executedCommands.push('Waiting for database recovery')
      await new Promise(resolve => setTimeout(resolve, 3000))
      
      const healthCheck = await healthCheckService.checkHealth()
      if (healthCheck.database === 'connected') {
        return {
          success: true,
          action: 'Database Recovery',
          message: 'Database recovered after retry',
          executedCommands,
        }
      }

      return {
        success: false,
        action: 'Database Recovery',
        message: 'Database did not recover automatically. Please check PostgreSQL is running: psql -l',
        executedCommands,
      }
    } catch (error: any) {
      return {
        success: false,
        action: 'Database Recovery',
        message: `Auto-fix failed: ${error.message}`,
        error: error.message,
        executedCommands,
      }
    }
  }

  /**
   * Fix: Network error
   */
  private async fixNetworkError(): Promise<RemediationResult> {
    const executedCommands: string[] = []
    
    try {
      // Network errors are usually temporary, so we retry
      executedCommands.push('Retrying network connection')
      
      for (let attempt = 1; attempt <= 3; attempt++) {
        const delay = 1000 * attempt
        await new Promise(resolve => setTimeout(resolve, delay))
        
        const isHealthy = await healthCheckService.waitForHealthy(5000)
        if (isHealthy) {
          return {
            success: true,
            action: 'Network Recovery',
            message: `Network connection recovered after ${attempt} retry attempt(s)`,
            executedCommands,
          }
        }
        executedCommands.push(`Network retry attempt ${attempt} failed`)
      }

      return {
        success: false,
        action: 'Network Recovery',
        message: 'Network connection did not recover. Please check your internet connection and firewall settings.',
        executedCommands,
      }
    } catch (error: any) {
      return {
        success: false,
        action: 'Network Recovery',
        message: `Auto-fix failed: ${error.message}`,
        error: error.message,
        executedCommands,
      }
    }
  }

  /**
   * Check backend health
   */
  private async checkBackendHealth(): Promise<boolean> {
    try {
      const response = await fetch('/health', {
        method: 'GET',
        signal: AbortSignal.timeout(3000),
      })
      return response.ok
    } catch {
      return false
    }
  }

  /**
   * Execute a remediation action via backend API
   */
  async executeRemediation(action: string, params?: any): Promise<RemediationResult> {
    try {
      const response = await fetch(`/api/remediation/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action, params: params || {} }),
        signal: AbortSignal.timeout(30000),
      })

      if (response.ok) {
        const result = await response.json()
        return {
          success: result.success,
          action,
          message: result.message,
          executedCommands: result.executed_commands || [],
        }
      } else {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
        return {
          success: false,
          action,
          message: error.detail || `Remediation failed: HTTP ${response.status}`,
        }
      }
    } catch (error: any) {
      // Fallback to frontend-based fixes if backend API unavailable
      switch (action) {
        case 'restart_backend':
          return await this.fixBackendUnreachable()
        case 'reconnect_database':
          return await this.fixDatabaseDisconnected()
        case 'retry_connection':
          return await this.fixNetworkError()
        default:
          return {
            success: false,
            action,
            message: `Remediation failed: ${error.message}`,
            error: error.message,
          }
      }
    }
  }
}

export const autoRemediationService = new AutoRemediationService()
