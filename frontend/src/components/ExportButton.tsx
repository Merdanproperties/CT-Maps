import { useState, useEffect, useRef } from 'react'
import { Download, FileText, FileJson, FileSpreadsheet } from 'lucide-react'
import { exportApi } from '../api/client'
import './ExportButton.css'

interface ExportButtonProps {
  filterType?: string | null
  filterParams?: any
  resultCount: number
}

export default function ExportButton({ filterType, filterParams, resultCount }: ExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  
  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node
      const menu = document.getElementById('export-menu');
      const isMenuVisible = menu != null && typeof menu.classList?.contains === 'function' && menu.classList.contains('show');
      
      // #region agent log
      (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:18',message:'Click outside handler',data:{isMenuVisible,menuRefContains:menuRef.current?.contains(target),targetTagName:(target as Element)?.tagName,targetClassName:(target as Element)?.className},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{}));
      // #endregion
      
      // Only close if clicking outside the dropdown AND menu is visible
      // Don't close if clicking on export-option buttons (they handle their own closing)
      const refEl = menuRef.current;
      const clickInside = refEl != null && typeof (refEl as Node).contains === 'function' && (refEl as Node).contains(target);
      if (refEl && !clickInside && isMenuVisible) {
        // Check if target is an export-option button
        const isExportOption = (target as Element)?.closest?.('.export-option')
        if (!isExportOption) {
          menu?.classList.remove('show')
        }
      }
    }
    
    // Use click instead of mousedown to avoid interfering with button clicks
    // Use bubble phase (false) so button onClick fires first
    document.addEventListener('click', handleClickOutside)
    return () => {
      document.removeEventListener('click', handleClickOutside)
    }
  }, [])

  const handleExport = async (format: 'csv' | 'json' | 'excel') => {
    console.log('🚀 [Export] handleExport called', { format, resultCount, filterType, filterParams })
    
    // #region agent log
    try {
      await (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:31',message:'Export started',data:{format,resultCount,filterType,filterParams},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{}));
    } catch (e) {
      console.warn('Debug log failed:', e)
    }
    // #endregion
    
    if (resultCount === 0) {
      alert('No results to export')
      return
    }

    setIsExporting(true)

    try {
      
      const params: any = {}
      
      if (filterType) {
        params.filter_type = filterType
      }
      
      if (filterParams) {
        // Convert municipality array to string if needed
        const normalizedParams = { ...filterParams }
        if (normalizedParams.municipality && Array.isArray(normalizedParams.municipality)) {
          normalizedParams.municipality = normalizedParams.municipality.join(',')
        }
        Object.assign(params, normalizedParams)
      }
      
      console.log('📋 [Export] Params built:', { params, format })
      
      // #region agent log
      try {
        await (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:50',message:'Params built for export',data:{params,format},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{}));
      } catch (e) {
        console.warn('Debug log failed:', e)
      }
      // #endregion

      let blob: Blob
      let fileExtension: string
      let mimeType: string
      
      console.log('🌐 [Export] Calling API:', { format, params })
      
      // #region agent log
      try {
        await (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:55',message:'Before API call',data:{format,params},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
      } catch (e) {
        console.warn('Debug log failed:', e)
      }
      // #endregion
      
      if (format === 'csv') {
        blob = await exportApi.exportCSV(params)
        fileExtension = 'csv'
        mimeType = 'text/csv'
      } else if (format === 'excel') {
        blob = await exportApi.exportExcel(params)
        fileExtension = 'xlsx'
        mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      } else {
        blob = await exportApi.exportJSON({ ...params, limit: 10000 })
        fileExtension = 'json'
        mimeType = 'application/json'
      }
      
      console.log('✅ [Export] Blob received:', { format, blobSize: blob?.size, blobType: blob?.type, isBlob: blob instanceof Blob })
      
      // #region agent log
      try {
        await (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:70',message:'After API call - blob received',data:{format,blobSize:blob?.size,blobType:blob?.type,isBlob:blob instanceof Blob},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{}));
      } catch (e) {
        console.warn('Debug log failed:', e)
      }
      // #endregion

      // Validate blob
      const isBlob = blob instanceof Blob
      if (!blob || !isBlob) {
        // #region agent log
        (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:75',message:'Invalid blob error',data:{format,blob,isBlob},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{}));
        // #endregion
        throw new Error('Invalid blob response from server')
      }

      if (blob.size === 0) {
        // #region agent log
        (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:81',message:'Empty blob error',data:{format,blobSize:blob.size},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{}));
        // #endregion
        throw new Error('Empty file received from server');
      }

      console.log(`Export successful: ${format} file, size: ${blob.size} bytes, type: ${blob.type}`);

      // #region agent log
      (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:90',message:'Creating download link',data:{format,blobSize:blob.size,fileExtension},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{}));
      // #endregion

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ct_properties_${new Date().toISOString().split('T')[0]}.${fileExtension}`
      a.style.display = 'none'
      document.body.appendChild(a);
      
      // #region agent log
      (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:100',message:'Triggering download',data:{format,downloadFilename:a.download},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{}));
      // #endregion
      
      // Trigger download
      a.click();
      
      // Small delay before cleanup (some browsers need this, especially on Mac)
      setTimeout(() => {
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }, 100);
      
      // #region agent log
      (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:110',message:'Export completed successfully',data:{format,blobSize:blob.size},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{}));
      // #endregion
    } catch (error) {
      // #region agent log
      (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:113',message:'Export error caught',data:{format,error:error instanceof Error ? error.message : String(error),errorStack:error instanceof Error ? error.stack : undefined},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
      // #endregion
      console.error('Export failed:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      alert(`Failed to export data: ${errorMessage}. Please try again.`)
    } finally {
      setIsExporting(false)
    }
  }

  // #region agent log
  useEffect(() => {
    if (typeof import.meta.env.VITE_AGENT_INGEST_URL !== 'string') return
    try {
      fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:171',message:'Component rendered',data:{resultCount,isExporting,filterType,hasFilterParams:!!filterParams,municipality:filterParams?.municipality},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      setTimeout(() => {
        const button = document.querySelector('.export-button') as HTMLButtonElement
        const menu = document.getElementById('export-menu')
        if (button) {
          fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:180',message:'Button DOM state check',data:{buttonExists:!!button,buttonDisabled:button.disabled,buttonVisible:button.offsetParent !== null,menuExists:!!menu,menuVisible:menu?.classList.contains('show')},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
        }
      }, 100)
    } catch (_) {}
  }, [resultCount, isExporting, filterType, filterParams])
  // #endregion

  return (
    <div className="export-button-container">
      <div className="export-dropdown" ref={menuRef}>
        <button
          className="export-button"
          disabled={isExporting || resultCount === 0}
          onClick={(e) => {
            console.log('🖱️ [Export] Main Export button clicked', { isExporting, resultCount, disabled: isExporting || resultCount === 0 });
            // #region agent log
            (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:189',message:'Main Export button clicked',data:{isExporting,resultCount,disabled:isExporting || resultCount === 0,eventType:e.type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{}));
            // #endregion
            e.stopPropagation()
            const menu = document.getElementById('export-menu')
            const isShowing = menu?.classList.contains('show')
            menu?.classList.toggle('show');
            const nowShowing = menu?.classList.contains('show')
            console.log('📋 [Export] Menu toggled:', { wasShowing: isShowing, nowShowing });
            // #region agent log
            (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:196',message:'Menu toggled',data:{wasShowing:isShowing,nowShowing,menuExists:!!menu},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{}));
            // #endregion
          }}
        >
          <Download size={18} />
          {isExporting ? 'Exporting...' : 'Export'}
        </button>
        <div id="export-menu" className="export-menu">
          <button
            className="export-option"
            onClick={(e) => {
              console.log('🖱️ [Export] CSV button clicked', { isExporting, disabled: isExporting })
              e.stopPropagation()
              handleExport('csv')
              document.getElementById('export-menu')?.classList.remove('show')
            }}
            disabled={isExporting}
          >
            <FileText size={16} />
            Export as CSV
          </button>
          <button
            className="export-option"
            onClick={(e) => {
              console.log('🖱️ [Export] Excel button clicked', { 
                isExporting, 
                disabled: isExporting,
                eventType: e.type,
                target: e.target,
                currentTarget: e.currentTarget
              });
              // #region agent log
              (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:216',message:'Excel button clicked',data:{isExporting,disabled:isExporting,eventType:e.type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
              // #endregion
              
              try {
                // Stop propagation to prevent click-outside handler from firing
                e.stopPropagation();
                e.preventDefault();
                
                // #region agent log
                (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:262',message:'After stopPropagation',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
                // #endregion
                
                // Check if menu is visible
                const menu = document.getElementById('export-menu')
                const isMenuVisible = menu?.classList.contains('show');
                console.log('📋 [Export] Menu state before export:', { isMenuVisible, menuExists: !!menu });
                // #region agent log
                (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:227',message:'Menu state before export',data:{isMenuVisible,menuExists:!!menu},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
                // #endregion
                
                // Close menu first, then handle export
                document.getElementById('export-menu')?.classList.remove('show');
                
                // #region agent log
                (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:275',message:'Before setTimeout handleExport',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
                // #endregion
                
                // Use setTimeout to ensure menu closes before export starts
                setTimeout(() => {
                  // #region agent log
                  (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:280',message:'Inside setTimeout, calling handleExport',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
                  // #endregion
                  handleExport('excel')
                }, 0)
              } catch (error) {
                // #region agent log
                (typeof import.meta.env.VITE_AGENT_INGEST_URL === 'string' && fetch(import.meta.env.VITE_AGENT_INGEST_URL + '/ingest/27561713-12d3-42d2-9645-e12539baabd5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ExportButton.tsx:285',message:'Error in Excel button handler',data:{error:error instanceof Error ? error.message : String(error),errorStack:error instanceof Error ? error.stack : undefined},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{}));
                // #endregion
                console.error('Error in Excel button handler:', error)
              }
            }}
            disabled={isExporting}
            type="button"
          >
            <FileSpreadsheet size={16} />
            Export as Excel
          </button>
          <button
            className="export-option"
            onClick={(e) => {
              console.log('🖱️ [Export] JSON button clicked', { isExporting, disabled: isExporting })
              e.stopPropagation()
              handleExport('json')
              document.getElementById('export-menu')?.classList.remove('show')
            }}
            disabled={isExporting}
          >
            <FileJson size={16} />
            Export as JSON
          </button>
        </div>
      </div>
      {resultCount > 0 && (
        <span className="export-count">{resultCount.toLocaleString()} properties</span>
      )}
    </div>
  )
}
