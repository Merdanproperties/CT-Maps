/**
 * Diagnostics Service - Provides clear diagnostic information and fix instructions
 * for any failure scenario
 */

export interface DiagnosticInfo {
  issue: string
  severity: 'error' | 'warning' | 'info'
  cause: string
  fixSteps: string[]
  relatedServices: string[]
  checkCommands?: string[]
}

export interface SystemDiagnostics {
  timestamp: number
  backend: {
    reachable: boolean
    healthy: boolean
    database: string
    error?: string
  }
  frontend: {
    running: boolean
    port: number
  }
  database?: {
    reachable: boolean
    error?: string
  }
  issues: DiagnosticInfo[]
  recommendations: string[]
}

class DiagnosticsService {
  /**
   * Run comprehensive system diagnostics
   */
  async runDiagnostics(): Promise<SystemDiagnostics> {
    const diagnostics: SystemDiagnostics = {
      timestamp: Date.now(),
      backend: {
        reachable: false,
        healthy: false,
        database: 'unknown',
      },
      frontend: {
        running: true,
        port: 3000,
      },
      issues: [],
      recommendations: [],
    }

    // Check backend reachability
    try {
      const response = await fetch('/health/ready', {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      })

      if (response.ok) {
        const health = await response.json()
        diagnostics.backend.reachable = true
        diagnostics.backend.healthy = health.status === 'healthy'
        diagnostics.backend.database = health.database || 'unknown'

        if (!diagnostics.backend.healthy) {
          diagnostics.issues.push(this.getDiagnosticForIssue('backend_unhealthy', health))
        }
      } else {
        diagnostics.backend.reachable = true
        diagnostics.backend.healthy = false
        diagnostics.backend.error = `HTTP ${response.status}`
        diagnostics.issues.push(this.getDiagnosticForIssue('backend_error', { status: response.status }))
      }
    } catch (error: any) {
      diagnostics.backend.reachable = false
      diagnostics.backend.error = error.message
      diagnostics.issues.push(this.getDiagnosticForIssue('backend_unreachable', { error: error.message }))
    }

    // Generate recommendations
    diagnostics.recommendations = this.generateRecommendations(diagnostics)

    return diagnostics
  }

  /**
   * Get diagnostic information for a specific issue
   */
  getDiagnosticForIssue(issueType: string, context: any): DiagnosticInfo {
    const diagnostics: Record<string, DiagnosticInfo> = {
      backend_unreachable: {
        issue: 'Backend server is not reachable',
        severity: 'error',
        cause: 'The backend server is not running or not accessible on port 8000',
        fixSteps: [
          '1. Start (or restart) services from project root:',
          '   ./scripts/start_all.sh',
          '',
          '2. Verify backend is on port 8000:',
          '   lsof -i :8000',
          '',
          '3. Check backend logs for errors:',
          '   tail -f logs/backend.log',
          '',
          '4. Or start backend only:',
          '   cd backend && source venv/bin/activate && uvicorn main:app --reload',
        ],
        relatedServices: ['backend', 'uvicorn'],
        checkCommands: [
          'curl http://localhost:8000/health',
          'lsof -i :8000',
          'ps aux | grep uvicorn',
        ],
      },
      backend_unhealthy: {
        issue: 'Backend server is unhealthy',
        severity: 'error',
        cause: `Backend is running but not healthy. Database status: ${context.database || 'unknown'}`,
        fixSteps: [
          '1. Restart services from project root:',
          '   ./scripts/start_all.sh',
          '',
          '2. Check database connection:',
          '   psql -l  # Verify PostgreSQL is running',
          '',
          '3. Check backend logs:',
          '   tail -f logs/backend.log',
          '',
          '4. Verify database URL in backend/.env:',
          '   cat backend/.env | grep DATABASE_URL',
        ],
        relatedServices: ['backend', 'database'],
        checkCommands: [
          'curl http://localhost:8000/health',
          'psql -l',
        ],
      },
      backend_error: {
        issue: `Backend returned error: HTTP ${context.status}`,
        severity: 'error',
        cause: `Backend server returned HTTP ${context.status} status code`,
        fixSteps: [
          '1. Restart services from project root:',
          '   ./scripts/start_all.sh',
          '',
          '2. Check backend logs for detailed error:',
          '   tail -f logs/backend.log',
          '',
          '3. Check backend health endpoint:',
          '   curl http://localhost:8000/health',
        ],
        relatedServices: ['backend'],
        checkCommands: [
          'curl -v http://localhost:8000/health',
        ],
      },
      database_disconnected: {
        issue: 'Database connection is lost',
        severity: 'error',
        cause: 'Backend cannot connect to PostgreSQL database',
        fixSteps: [
          '1. Verify PostgreSQL is running:',
          '   brew services list | grep postgresql  # or Postgres.app',
          '',
          '2. Test database connection:',
          '   psql -l',
          '',
          '3. Restart PostgreSQL if needed:',
          '   brew services restart postgresql',
          '',
          '4. Restart services from project root after database is up:',
          '   ./scripts/start_all.sh',
        ],
        relatedServices: ['database', 'backend'],
        checkCommands: [
          'psql -l',
          'ps aux | grep postgres',
        ],
      },
      network_error: {
        issue: 'Network connection error',
        severity: 'error',
        cause: 'Cannot establish network connection to backend',
        fixSteps: [
          '1. Start (or restart) services from project root:',
          '   ./scripts/start_all.sh',
          '',
          '2. Verify backend is running:',
          '   curl http://localhost:8000/health',
          '',
          '3. Check if port 8000 is in use:',
          '   lsof -i :8000',
        ],
        relatedServices: ['backend', 'network'],
        checkCommands: [
          'curl http://localhost:8000/health',
          'netstat -an | grep 8000',
        ],
      },
    }

    return diagnostics[issueType] || {
      issue: 'Unknown issue',
      severity: 'error',
      cause: 'An unknown error occurred',
      fixSteps: ['Check logs for more information'],
      relatedServices: [],
    }
  }

  /**
   * Generate recommendations based on diagnostics
   */
  generateRecommendations(diagnostics: SystemDiagnostics): string[] {
    const recommendations: string[] = []

    if (!diagnostics.backend.reachable) {
      recommendations.push('Start services from project root: ./scripts/start_all.sh')
    }

    if (diagnostics.backend.reachable && !diagnostics.backend.healthy) {
      if (diagnostics.backend.database === 'disconnected') {
        recommendations.push('Check PostgreSQL is running: psql -l')
        recommendations.push('Restart PostgreSQL if needed, then run: ./scripts/start_all.sh')
      } else {
        recommendations.push('Restart services: ./scripts/start_all.sh')
        recommendations.push('Check backend logs: tail -f logs/backend.log')
      }
    }

    if (diagnostics.issues.length === 0) {
      recommendations.push('All systems operational! No action needed.')
    }

    return recommendations
  }

  /**
   * Format diagnostics as a user-friendly message
   */
  formatDiagnostics(diagnostics: SystemDiagnostics): string {
    let message = '🔍 System Diagnostics\n\n'

    // Status summary
    message += 'Status:\n'
    message += `  Backend: ${diagnostics.backend.reachable ? (diagnostics.backend.healthy ? '✅ Healthy' : '⚠️ Unhealthy') : '❌ Unreachable'}\n`
    message += `  Database: ${diagnostics.backend.database === 'connected' ? '✅ Connected' : '❌ Disconnected'}\n`
    message += `  Frontend: ✅ Running\n\n`

    // Issues
    if (diagnostics.issues.length > 0) {
      message += 'Issues Found:\n\n'
      diagnostics.issues.forEach((issue, index) => {
        message += `${index + 1}. ${issue.issue}\n`
        message += `   Cause: ${issue.cause}\n`
        message += `   Fix Steps:\n`
        issue.fixSteps.forEach(step => {
          message += `   ${step}\n`
        })
        message += '\n'
      })
    }

    // Recommendations
    if (diagnostics.recommendations.length > 0) {
      message += 'Recommended Actions:\n'
      diagnostics.recommendations.forEach((rec, index) => {
        message += `  ${index + 1}. ${rec}\n`
      })
    }

    return message
  }
}

export const diagnosticsService = new DiagnosticsService()
