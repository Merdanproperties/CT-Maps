import { useState, useEffect } from 'react'
import { diagnosticsService, SystemDiagnostics } from '../services/diagnostics'
import { autoRemediationService, RemediationResult } from '../services/autoRemediation'
import { X, AlertCircle, CheckCircle2, Loader2, Copy, ExternalLink, Zap } from 'lucide-react'
import './DiagnosticsPanel.css'

interface DiagnosticsPanelProps {
  isOpen: boolean
  onClose: () => void
}

export default function DiagnosticsPanel({ isOpen, onClose }: DiagnosticsPanelProps) {
  const [diagnostics, setDiagnostics] = useState<SystemDiagnostics | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [copied, setCopied] = useState(false)
  const [isFixing, setIsFixing] = useState(false)
  const [fixResults, setFixResults] = useState<RemediationResult[] | null>(null)

  useEffect(() => {
    if (isOpen && !diagnostics) {
      runDiagnostics()
    }
  }, [isOpen])

  const runDiagnostics = async () => {
    setIsRunning(true)
    try {
      const result = await diagnosticsService.runDiagnostics()
      setDiagnostics(result)
    } catch (error) {
      console.error('Diagnostics failed:', error)
    } finally {
      setIsRunning(false)
    }
  }

  const copyDiagnostics = () => {
    if (diagnostics) {
      const formatted = diagnosticsService.formatDiagnostics(diagnostics)
      navigator.clipboard.writeText(formatted)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const autoFix = async () => {
    if (!diagnostics) return
    
    setIsFixing(true)
    setFixResults(null)
    
    try {
      const results = await autoRemediationService.autoFix(diagnostics)
      setFixResults(results)
      
      // Refresh diagnostics after fix attempts
      setTimeout(() => {
        runDiagnostics()
      }, 3000)
    } catch (error) {
      console.error('Auto-fix failed:', error)
    } finally {
      setIsFixing(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="diagnostics-overlay" onClick={onClose}>
      <div className="diagnostics-panel" onClick={(e) => e.stopPropagation()}>
        <div className="diagnostics-header">
          <h2>🔍 System Diagnostics</h2>
          <div className="diagnostics-actions">
            <button
              className="diagnostics-button"
              onClick={runDiagnostics}
              disabled={isRunning}
            >
              {isRunning ? <Loader2 className="spinning" size={16} /> : '🔄'}
              Refresh
            </button>
            <button
              className="diagnostics-button"
              onClick={copyDiagnostics}
              disabled={!diagnostics}
            >
              {copied ? '✓' : <Copy size={16} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            {diagnostics && diagnostics.issues.length > 0 && (
              <button
                className="diagnostics-button auto-fix"
                onClick={autoFix}
                disabled={isFixing || isRunning}
              >
                {isFixing ? <Loader2 className="spinning" size={16} /> : <Zap size={16} />}
                {isFixing ? 'Fixing...' : 'Auto-Fix'}
              </button>
            )}
            <button className="diagnostics-close" onClick={onClose}>
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="diagnostics-content">
          {isRunning ? (
            <div className="diagnostics-loading">
              <Loader2 className="spinning" size={32} />
              <p>Running diagnostics...</p>
            </div>
          ) : diagnostics ? (
            <>
              {/* Status Summary */}
              <div className="diagnostics-section">
                <h3>System Status</h3>
                <div className="status-grid">
                  <div className="status-item">
                    <span className="status-label">Backend:</span>
                    <span className={`status-value ${diagnostics.backend.reachable && diagnostics.backend.healthy ? 'healthy' : 'error'}`}>
                      {diagnostics.backend.reachable ? (
                        diagnostics.backend.healthy ? (
                          <>✅ Healthy</>
                        ) : (
                          <>⚠️ Unhealthy</>
                        )
                      ) : (
                        <>❌ Unreachable</>
                      )}
                    </span>
                  </div>
                  <div className="status-item">
                    <span className="status-label">Database:</span>
                    <span className={`status-value ${diagnostics.backend.database === 'connected' ? 'healthy' : 'error'}`}>
                      {diagnostics.backend.database === 'connected' ? '✅ Connected' : '❌ Disconnected'}
                    </span>
                  </div>
                  <div className="status-item">
                    <span className="status-label">Frontend:</span>
                    <span className="status-value healthy">✅ Running</span>
                  </div>
                </div>
              </div>

              {/* Issues */}
              {diagnostics.issues.length > 0 && (
                <div className="diagnostics-section">
                  <h3>Issues Found ({diagnostics.issues.length})</h3>
                  {diagnostics.issues.map((issue, index) => (
                    <div key={index} className="issue-card">
                      <div className="issue-header">
                        <AlertCircle className={`issue-icon ${issue.severity}`} size={20} />
                        <strong>{issue.issue}</strong>
                      </div>
                      <div className="issue-cause">
                        <strong>Cause:</strong> {issue.cause}
                      </div>
                      <div className="issue-fix">
                        <strong>How to Fix:</strong>
                        <ol>
                          {issue.fixSteps.map((step, stepIndex) => (
                            <li key={stepIndex}>
                              <pre>{step}</pre>
                            </li>
                          ))}
                        </ol>
                      </div>
                      {issue.checkCommands && issue.checkCommands.length > 0 && (
                        <div className="issue-commands">
                          <strong>Check Commands:</strong>
                          {issue.checkCommands.map((cmd, cmdIndex) => (
                            <code key={cmdIndex} className="command-code">{cmd}</code>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Recommendations */}
              {diagnostics.recommendations.length > 0 && (
                <div className="diagnostics-section">
                  <h3>Recommended Actions</h3>
                  <ul className="recommendations-list">
                    {diagnostics.recommendations.map((rec, index) => (
                      <li key={index}>
                        <CheckCircle2 size={16} className="recommendation-icon" />
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Auto-Fix Results */}
              {fixResults && fixResults.length > 0 && (
                <div className="diagnostics-section">
                  <h3>Auto-Fix Results</h3>
                  {fixResults.map((result, index) => (
                    <div key={index} className={`fix-result ${result.success ? 'success' : 'error'}`}>
                      <div className="fix-result-header">
                        {result.success ? (
                          <CheckCircle2 size={20} className="fix-icon success" />
                        ) : (
                          <AlertCircle size={20} className="fix-icon error" />
                        )}
                        <strong>{result.action}</strong>
                      </div>
                      <div className="fix-result-message">{result.message}</div>
                      {result.executedCommands && result.executedCommands.length > 0 && (
                        <div className="fix-result-commands">
                          <strong>Executed:</strong>
                          <ul>
                            {result.executedCommands.map((cmd, cmdIndex) => (
                              <li key={cmdIndex}>{cmd}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {diagnostics.issues.length === 0 && (
                <div className="diagnostics-success">
                  <CheckCircle2 size={48} className="success-icon" />
                  <h3>All Systems Operational!</h3>
                  <p>No issues detected. Everything is running smoothly.</p>
                </div>
              )}
            </>
          ) : (
            <div className="diagnostics-empty">
              <p>Click "Refresh" to run diagnostics</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
