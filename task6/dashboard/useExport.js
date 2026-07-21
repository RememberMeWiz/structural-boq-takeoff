/**
 * useExport.js
 *
 * React hook that calls the Flask export endpoints (/api/export/xlsx and
 * /api/export/pdf) and triggers a browser file download with the binary response.
 *
 * Usage:
 *   const { exportXlsx, exportPdf, exporting, exportError } = useExport()
 *   <button onClick={() => exportXlsx(jobId)}>Export Excel</button>
 */

import { useState, useCallback } from 'react'

export function useExport() {
  const [exporting, setExporting] = useState(null) // 'xlsx' | 'pdf' | null
  const [exportError, setExportError] = useState(null)

  /**
   * Download a file from a URL and trigger browser save-as dialog.
   * @param {string} url  - Fetch URL
   * @param {string} name - Suggested filename for download
   */
  const _download = useCallback(async (url, name) => {
    setExportError(null)
    try {
      const res = await fetch(url)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error || `HTTP ${res.status}`)
      }
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = name
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(objectUrl)
    } catch (err) {
      setExportError(err.message || 'Export failed')
    }
  }, [])

  /**
   * Export the BOQ as an Excel workbook.
   * @param {string|null} jobId - Optional job_id to tie export to an uploaded drawing
   */
  const exportXlsx = useCallback(
    async (jobId = null) => {
      setExporting('xlsx')
      const params = jobId ? `?job_id=${encodeURIComponent(jobId)}` : ''
      await _download(`/api/export/xlsx${params}`, 'BOQ_Schedule.xlsx')
      setExporting(null)
    },
    [_download]
  )

  /**
   * Export the BOQ as an executive PDF report.
   * @param {string|null} jobId - Optional job_id to tie export to an uploaded drawing
   */
  const exportPdf = useCallback(
    async (jobId = null) => {
      setExporting('pdf')
      const params = jobId ? `?job_id=${encodeURIComponent(jobId)}` : ''
      await _download(`/api/export/pdf${params}`, 'Executive_BOQ_Report.pdf')
      setExporting(null)
    },
    [_download]
  )

  return { exportXlsx, exportPdf, exporting, exportError }
}
