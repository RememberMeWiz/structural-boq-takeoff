/**
 * ImportModal.jsx
 *
 * Drag-and-drop file upload modal that communicates with the Flask import
 * pipeline (POST /api/upload → GET /api/status/<job_id>).
 *
 * Props:
 *   onClose   () => void          — called when the user closes the modal
 *   onComplete (jobId, boq) => void — called when processing succeeds; passes
 *                                     the job_id and the BOQ JSON payload so
 *                                     the parent can refresh the dashboard tables.
 */

import { useState, useRef, useCallback, useEffect } from 'react'

const STAGE_LABELS = {
  queued:     'Queued…',
  converting: 'Converting DWG → DXF…',
  validating: 'Validating geometry…',
  takeoff:    'Running Fajardo quantity takeoff…',
  done:       'Complete',
  error:      'Error',
}

const POLL_INTERVAL_MS = 1500

export default function ImportModal({ onClose, onComplete }) {
  const [dragActive, setDragActive] = useState(false)
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)  // { stage, progress, message }
  const [uploadError, setUploadError] = useState(null)

  const inputRef = useRef(null)
  const pollRef = useRef(null)

  // -----------------------------------------------------------------------
  // Drag & drop handlers
  // -----------------------------------------------------------------------
  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setDragActive(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setDragActive(false)
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragActive(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) _selectFile(dropped)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleFileInput = useCallback((e) => {
    const picked = e.target.files[0]
    if (picked) _selectFile(picked)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function _selectFile(f) {
    const ext = f.name.split('.').pop().toLowerCase()
    if (!['dwg', 'dxf', 'pdf'].includes(ext)) {
      setUploadError(`Unsupported file type ".${ext}". Please upload a .dwg, .dxf, or .pdf file.`)
      return
    }
    setUploadError(null)
    setFile(f)
    setJobId(null)
    setJobStatus(null)
  }

  // -----------------------------------------------------------------------
  // Upload
  // -----------------------------------------------------------------------
  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setUploadError(null)
    setJobStatus({ stage: 'queued', progress: 10, message: 'Uploading drawing to takeoff engine…' })

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('/api/upload', { method: 'POST', body: formData })
      const json = await res.json()

      if (!res.ok) {
        throw new Error(json.error || `Upload failed with status ${res.status}`)
      }

      setJobId(json.job_id)
      setUploading(false)
      setJobStatus({ stage: 'validating', progress: 30, message: 'Processing PDF geometry and structural elements…' })
      // Polling starts via useEffect below once jobId is set
    } catch (err) {
      setUploadError(err.message || 'Failed to connect to takeoff server')
      setUploading(false)
      setJobStatus(null)
    }
  }

  // -----------------------------------------------------------------------
  // Poll for job status
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (!jobId) return

    async function poll() {
      try {
        const res = await fetch(`/api/status/${jobId}`)
        const data = await res.json()
        setJobStatus(data)

        if (data.stage === 'done') {
          clearInterval(pollRef.current)
          // Fetch the structured BOQ payload for the dashboard
          try {
            const boqRes = await fetch(`/api/takeoff/${jobId}`)
            const boq = boqRes.ok ? await boqRes.json() : null
            onComplete?.(jobId, boq, file?.name || 'Imported Drawing')
          } catch {
            onComplete?.(jobId, null, file?.name || 'Imported Drawing')
          }
        } else if (data.stage === 'error') {
          clearInterval(pollRef.current)
        }
      } catch {
        // Network errors — keep polling silently
      }
    }

    pollRef.current = setInterval(poll, POLL_INTERVAL_MS)
    poll() // immediate first check

    return () => clearInterval(pollRef.current)
  }, [jobId, onComplete])

  // -----------------------------------------------------------------------
  // Derived UI state
  // -----------------------------------------------------------------------
  const isDone  = jobStatus?.stage === 'done'
  const isError = jobStatus?.stage === 'error'
  const progress = jobStatus?.progress ?? 0
  const stageLabel = STAGE_LABELS[jobStatus?.stage] || jobStatus?.stage || ''

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-ink-500/15">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wide text-ink-500">
              Unified Import Pipeline
            </div>
            <div className="text-base font-semibold text-ink-900">Import Drawing</div>
          </div>
          <button
            onClick={onClose}
            className="text-ink-500 hover:text-ink-900 transition text-xl leading-none px-1"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Drop zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors select-none ${
              dragActive
                ? 'border-brass bg-brass/5'
                : file
                ? 'border-flag-ok/50 bg-flag-ok/5'
                : 'border-ink-500/25 hover:border-brass/50 hover:bg-paper-100'
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".dwg,.dxf,.pdf"
              className="sr-only"
              onChange={handleFileInput}
            />
            <div className="text-3xl mb-2">{file ? '📄' : '📂'}</div>
            {file ? (
              <div>
                <div className="font-medium text-ink-900 text-sm truncate">{file.name}</div>
                <div className="text-xs text-ink-500 mt-0.5">
                  {(file.size / 1024 / 1024).toFixed(2)} MB — click to change
                </div>
              </div>
            ) : (
              <div>
                <div className="text-sm font-medium text-ink-700">
                  Drop a file here or click to browse
                </div>
                <div className="text-xs text-ink-500 mt-1">
                  Supported: <code>.dwg</code> · <code>.dxf</code> · <code>.pdf</code> (up to 200 MB)
                </div>
              </div>
            )}
          </div>

          {/* Error notice — stays until dismissed */}
          {uploadError && (
            <div className="text-xs bg-flag-warn/10 border border-flag-warn/20 rounded px-3 py-2 flex items-start gap-2">
              <span className="text-flag-warn flex-1">⚠ {uploadError}</span>
              <button
                onClick={() => setUploadError(null)}
                className="shrink-0 text-flag-warn/60 hover:text-flag-warn text-base leading-none"
                aria-label="Dismiss error"
              >✕</button>
            </div>
          )}

          {/* Progress */}
          {jobStatus && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className={`font-medium ${isError ? 'text-flag-warn' : isDone ? 'text-flag-ok' : 'text-brass'}`}>
                  {stageLabel}
                </span>
                <span className="text-ink-500 font-mono">{progress}%</span>
              </div>
              <div className="w-full bg-paper-200 rounded-full h-1.5 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    isError ? 'bg-flag-warn' : isDone ? 'bg-flag-ok' : 'bg-brass'
                  }`}
                  style={{ width: `${progress}%` }}
                />
              </div>
              {/* Show message — error messages stay visible, others update */}
              {jobStatus.message && (
                <div className={`text-xs leading-snug ${isError ? 'text-flag-warn font-medium' : 'text-ink-500'}`}>
                  {isError && '⚠ '}{jobStatus.message}
                  {isError && (
                    <div className="mt-1 text-ink-500 font-normal">
                      This message will remain visible. Click Cancel to close the modal.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ODA note */}
          {file && file.name.toLowerCase().endsWith('.dwg') && !jobStatus && (
            <div className="text-xs text-ink-500 bg-paper-100 rounded px-3 py-2 leading-snug">
              ℹ DWG conversion requires <strong>ODA File Converter</strong> to be installed. 
              If conversion fails, try uploading the file as <code>.dxf</code> instead.
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-ink-500/15 bg-paper-50">
          {isDone ? (
            <button
              onClick={onClose}
              className="px-4 py-1.5 text-sm font-medium rounded bg-flag-ok text-white hover:brightness-110 transition"
            >
              ✓ Done — Close
            </button>
          ) : (
            <>
              <button
                onClick={onClose}
                className="px-3 py-1.5 text-xs rounded border border-ink-500/25 hover:bg-paper-100 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={!file || uploading || !!jobId}
                className="px-4 py-1.5 text-sm font-medium rounded bg-brass text-white hover:brightness-110 transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {uploading ? 'Uploading…' : jobId ? 'Processing…' : 'Process Drawing'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
