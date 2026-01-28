import { useEffect, useState } from 'react'
import { healthCheckService, HealthStatus } from '../services/healthCheck'
import { serviceManager, ServiceRecoveryAction } from '../services/serviceManager'
import { AlertCircle, CheckCircle2, Loader2, RefreshCw, Settings } from 'lucide-react'
import DiagnosticsPanel from './DiagnosticsPanel'
import './ConnectionStatus.css'

export default function ConnectionStatus() {
  const [status, setStatus] = useState<HealthStatus>(healthCheckService.getStatus())
  const [isVisible, setIsVisible] = useState(false)
  const [recoveryAction, setRecoveryAction] = useState<ServiceRecoveryAction | null>(null)
  const [isRecovering, setIsRecovering] = useState(false)
  const [showDiagnostics, setShowDiagnostics] = useState(false)

  useEffect(() => {
    // Subscribe to health status updates
    const unsubscribeHealth = healthCheckService.subscribe((newStatus) => {
      setStatus(newStatus)
      // Show banner if unhealthy
      setIsVisible(!newStatus.isHealthy)
    })

    // Subscribe to recovery actions
    const unsubscribeRecovery = serviceManager.subscribe((action) => {
      setRecoveryAction(action)
      setIsRecovering(action.type === 'reconnect' && !action.success)
      
      if (action.success && action.type === 'reconnect') {
        // Recovery succeeded, check health again
        setTimeout(() => healthCheckService.checkHealth(), 1000)
      }
    })

    // Monitoring is started by App.tsx; do not call startMonitoring() here to avoid duplicate checks

    return () => {
      unsubscribeHealth()
      unsubscribeRecovery()
    }
  }, [])

  if (!isVisible) {
    return null
  }

  const isDegraded = status.isHealthy && status.database && status.database !== 'connected'
  const getStatusIcon = () => {
    if (status.isHealthy && status.database === 'connected') {
      return <CheckCircle2 className="connection-status-icon healthy" size={20} />
    }
    if (isDegraded) {
      return <AlertCircle className="connection-status-icon error" size={20} />
    }
    if (Date.now() - status.lastChecked < 2000) {
      return <Loader2 className="connection-status-icon checking" size={20} />
    }
    return <AlertCircle className="connection-status-icon error" size={20} />
  }

  const getStatusMessage = () => {
    // Backend reachable and DB connected: show Connected
    if (status.isHealthy && status.database === 'connected') {
      return 'Connected (Database OK)'
    }
    // Backend reachable but DB degraded: softer message, no "start backend" hint
    if (status.isHealthy && status.database && status.database !== 'connected') {
      return 'Database temporarily unavailable - retrying...'
    }
    
    if (isRecovering) {
      return 'Attempting automatic recovery...'
    }
    
    if (recoveryAction?.type === 'notify' && !recoveryAction.success) {
      return recoveryAction.error || 'Service unavailable - please restart backend'
    }
    
    return status.error || 'Checking connection...'
  }

  const showStartHint = (): boolean => {
    if (status.isHealthy || isRecovering) return false
    if (recoveryAction?.type === 'notify') return true
    if (status.error && (status.error.includes('timeout') || status.error.includes('not responding'))) return true
    return false
  }

  const handleManualRecovery = async () => {
    setIsRecovering(true)
    try {
      await serviceManager.attemptRecovery(status)
      await healthCheckService.checkHealth()
    } catch (error) {
      console.error('Manual recovery failed:', error)
    } finally {
      setIsRecovering(false)
    }
  }

  return (
    <>
      <div className={`connection-status ${status.isHealthy && status.database === 'connected' ? 'healthy' : 'error'}`}>
        {getStatusIcon()}
        <div className="connection-status-message-wrap">
          <span className="connection-status-message">{getStatusMessage()}</span>
          {showStartHint() && (
            <span className="connection-status-fix-hint">
              Docker: run <strong>docker compose up -d --build</strong> from the project root. Local: <strong>./scripts/start_all.sh</strong>.
            </span>
          )}
        </div>
        {(!status.isHealthy || isDegraded) && (
          <>
            {isRecovering ? (
              <RefreshCw className="connection-status-icon checking" size={16} />
            ) : (
              <button
                className="connection-status-retry"
                onClick={handleManualRecovery}
                disabled={isRecovering}
              >
                Recover
              </button>
            )}
            <button
              className="connection-status-retry"
              onClick={() => healthCheckService.checkHealth()}
              disabled={isRecovering}
            >
              Check
            </button>
            <button
              className="connection-status-diagnostics"
              onClick={() => setShowDiagnostics(true)}
              title="Show detailed diagnostics and fix instructions"
            >
              <Settings size={16} />
              Fix
            </button>
          </>
        )}
      </div>
      <DiagnosticsPanel
        isOpen={showDiagnostics}
        onClose={() => setShowDiagnostics(false)}
      />
    </>
  )
}
