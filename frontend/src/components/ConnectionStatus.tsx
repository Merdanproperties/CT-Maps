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

    // Start monitoring
    healthCheckService.startMonitoring()

    return () => {
      unsubscribeHealth()
      unsubscribeRecovery()
      healthCheckService.stopMonitoring()
    }
  }, [])

  if (!isVisible && status.isHealthy) {
    return null
  }

  const getStatusIcon = () => {
    if (status.isHealthy) {
      return <CheckCircle2 className="connection-status-icon healthy" size={20} />
    }
    if (Date.now() - status.lastChecked < 2000) {
      return <Loader2 className="connection-status-icon checking" size={20} />
    }
    return <AlertCircle className="connection-status-icon error" size={20} />
  }

  const getStatusMessage = () => {
    if (status.isHealthy) {
      return `Connected${status.database === 'connected' ? ' (Database OK)' : ''}`
    }
    
    if (isRecovering) {
      return 'Attempting automatic recovery...'
    }
    
    if (recoveryAction?.type === 'notify' && !recoveryAction.success) {
      return recoveryAction.error || 'Service unavailable - please restart backend'
    }
    
    if (status.database && status.database !== 'connected') {
      return `Database: ${status.database} - Auto-recovering...`
    }
    
    return status.error || 'Checking connection...'
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
      <div className={`connection-status ${status.isHealthy ? 'healthy' : 'error'}`}>
        {getStatusIcon()}
        <span className="connection-status-message">{getStatusMessage()}</span>
        {!status.isHealthy && (
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
