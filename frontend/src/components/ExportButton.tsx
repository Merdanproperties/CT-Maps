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
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        const menu = document.getElementById('export-menu')
        menu?.classList.remove('show')
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const handleExport = async (format: 'csv' | 'json' | 'excel') => {
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
        Object.assign(params, filterParams)
      }

      let blob: Blob
      let fileExtension: string
      
      if (format === 'csv') {
        blob = await exportApi.exportCSV(params)
        fileExtension = 'csv'
      } else if (format === 'excel') {
        blob = await exportApi.exportExcel(params)
        fileExtension = 'xlsx'
      } else {
        blob = await exportApi.exportJSON({ ...params, limit: 10000 })
        fileExtension = 'json'
      }

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ct_properties_${new Date().toISOString().split('T')[0]}.${fileExtension}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Failed to export data. Please try again.')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="export-button-container">
      <div className="export-dropdown" ref={menuRef}>
        <button
          className="export-button"
          disabled={isExporting || resultCount === 0}
          onClick={() => {
            const menu = document.getElementById('export-menu')
            menu?.classList.toggle('show')
          }}
        >
          <Download size={18} />
          {isExporting ? 'Exporting...' : 'Export'}
        </button>
        <div id="export-menu" className="export-menu">
          <button
            className="export-option"
            onClick={() => {
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
            onClick={() => {
              handleExport('excel')
              document.getElementById('export-menu')?.classList.remove('show')
            }}
            disabled={isExporting}
          >
            <FileSpreadsheet size={16} />
            Export as Excel
          </button>
          <button
            className="export-option"
            onClick={() => {
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
