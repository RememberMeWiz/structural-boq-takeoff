import React, { useMemo, useState, useCallback } from 'react'
import { useProjectData } from './hooks/useProjectData'
import { useExport } from './hooks/useExport'
import DrawingViewer from './components/DrawingViewer'
import ElementInspector from './components/ElementInspector'
import BoqTable from './components/BoqTable'
import ImportModal from './components/ImportModal'
import { ELEMENT_TYPE_COLORS, ELEMENT_TYPE_LABELS } from './utils/visualStyle'
import { supabaseConfigured } from './lib/supabaseClient'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  componentDidCatch(error, errorInfo) {
    console.error('[BOQ Dashboard Error]', error, errorInfo)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen flex items-center justify-center bg-paper-100 p-6">
          <div className="max-w-lg bg-white border border-flag-warn/30 rounded-lg p-6 shadow-sm">
            <div className="text-xs font-mono uppercase tracking-wide text-flag-warn mb-1">Runtime Exception</div>
            <h2 className="text-base font-semibold text-ink-900 mb-2">BOQ Dashboard Component Error</h2>
            <pre className="text-xs font-mono bg-paper-200 p-3 rounded text-flag-warn overflow-auto mb-4 max-h-40">
              {this.state.error?.toString()}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="px-3 py-1.5 text-xs font-medium rounded bg-brass text-white hover:brightness-110"
            >
              Reload Dashboard
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function AppWrapper() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  )
}

function App() {
  const {
    loading, error, project, drawings, activeDrawingId, elements,
    backupRows, checklistRows, setActiveDrawing, updateElement, updateChecklistRow, reload
  } = useProjectData()

  const { exportXlsx, exportPdf, exporting, exportError } = useExport()

  const [selectedElementId, setSelectedElementId] = useState(null)
  const [colorMode, setColorMode] = useState('type') // 'type' | 'confidence'
  const [showImportModal, setShowImportModal] = useState(false)
  const [activeJobId, setActiveJobId] = useState(null)
  const [importBanner, setImportBanner] = useState(null)
  const [liveBoq, setLiveBoq] = useState(null) // BOQ from the most recent import

  const selectedElement = useMemo(
    () => elements.find((e) => e.id === selectedElementId) || null,
    [elements, selectedElementId]
  )

  const activeItemCode = useMemo(() => {
    if (!selectedElementId) return null
    const row = backupRows.find((r) => r.element_id === selectedElementId)
    return row?.item_code ?? null
  }, [selectedElementId, backupRows])

  const handleSelectItemCode = (itemCode) => {
    const row = backupRows.find((r) => r.item_code === itemCode && r.element_id)
    if (row) setSelectedElementId(row.element_id)
  }

  /** Called by ImportModal when the pipeline finishes. */
  const handleImportComplete = useCallback((jobId, boq) => {
    setActiveJobId(jobId)
    setShowImportModal(false)
    if (boq && boq.backup_rows?.length > 0) {
      setLiveBoq(boq)
      setImportBanner({ type: 'success', text: `Drawing processed: ${boq.backup_rows.length} takeoff rows computed. Use the Export buttons to download.` })
    } else {
      setImportBanner({ type: 'error', text: 'No BOQ data was extracted — the file may not contain recognisable structural elements (columns, beams, footings, slabs, CHB walls). Check that the PDF contains vector geometry, not a scanned image.' })
    }
    // Banner stays until user clicks ✕
  }, [])

  if (!supabaseConfigured) {
    return <ConfigNotice />
  }

  return (
    <div className="h-screen flex flex-col">
      {/* ------------------------------------------------------------------ */}
      {/* Header                                                               */}
      {/* ------------------------------------------------------------------ */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-ink-500/15 bg-white">
        <div>
          <div className="text-[11px] font-mono uppercase tracking-wide text-ink-500">BOQ Review Dashboard</div>
          <div className="text-base font-semibold text-ink-900">{project?.name ?? (loading ? 'Loading…' : '—')}</div>
        </div>

        <div className="flex items-center gap-2">
          {drawings.length > 0 && (
            <select
              value={activeDrawingId ?? ''}
              onChange={(e) => setActiveDrawing(e.target.value)}
              className="text-sm border border-ink-500/25 rounded px-2 py-1.5 bg-white"
            >
              {drawings.map((d) => (
                <option key={d.id} value={d.id}>{d.filename} ({d.sheet_ref})</option>
              ))}
            </select>
          )}

          {/* Import button */}
          <button
            id="btn-import-drawing"
            onClick={() => setShowImportModal(true)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded bg-brass text-white hover:brightness-110 transition font-medium"
          >
            <span>⬆</span> Import Drawing
          </button>

          {/* Export XLSX */}
          <button
            id="btn-export-xlsx"
            onClick={() => exportXlsx(activeJobId)}
            disabled={exporting === 'xlsx'}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded border border-ink-500/25 hover:bg-paper-100 transition disabled:opacity-50"
            title="Export BOQ as Excel workbook (.xlsx)"
          >
            {exporting === 'xlsx' ? '⏳' : '📊'} Excel
          </button>

          {/* Export PDF */}
          <button
            id="btn-export-pdf"
            onClick={() => exportPdf(activeJobId)}
            disabled={exporting === 'pdf'}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded border border-ink-500/25 hover:bg-paper-100 transition disabled:opacity-50"
            title="Export executive BOQ report (.pdf)"
          >
            {exporting === 'pdf' ? '⏳' : '📋'} PDF
          </button>

          <button
            id="btn-refresh"
            onClick={reload}
            className="text-xs px-2.5 py-1.5 rounded border border-ink-500/25 hover:bg-paper-100 transition"
          >
            Refresh
          </button>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="px-5 py-2 bg-flag-warn/10 text-flag-warn text-sm border-b border-flag-warn/20 flex items-center justify-between">
          <span>⚠ {error}</span>
          <button onClick={() => window.location.reload()} className="ml-3 text-flag-warn/70 hover:text-flag-warn text-xs underline">Retry</button>
        </div>
      )}

      {/* Export error banner */}
      {exportError && (
        <div className="px-5 py-2 bg-flag-warn/10 text-flag-warn text-sm border-b border-flag-warn/20 flex items-center justify-between">
          <span>Export error: {exportError}</span>
          <button onClick={() => {}} className="ml-3 text-flag-warn/70 hover:text-flag-warn text-lg leading-none">✕</button>
        </div>
      )}

      {/* Import result banner — stays until user clicks ✕ */}
      {importBanner && (
        <div className={`px-5 py-2 text-sm border-b flex items-start justify-between gap-3 ${
          importBanner.type === 'error'
            ? 'bg-flag-warn/10 text-flag-warn border-flag-warn/20'
            : 'bg-flag-ok/10 text-flag-ok border-flag-ok/20'
        }`}>
          <span>{importBanner.type === 'error' ? '⚠ ' : '✓ '}{importBanner.text}</span>
          <button
            onClick={() => setImportBanner(null)}
            className="shrink-0 text-lg leading-none opacity-60 hover:opacity-100 transition mt-0.5"
            aria-label="Dismiss"
          >✕</button>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Main layout                                                          */}
      {/* ------------------------------------------------------------------ */}
      <main className="flex-1 min-h-0 grid grid-cols-[1fr_320px] gap-3 p-3">
        <div className="grid grid-rows-[1fr_260px] gap-3 min-h-0">
          <div className="min-h-0 relative">
            <div className="absolute top-3 right-3 z-10 flex gap-1 bg-canvas-800/90 rounded-md p-1 border border-canvas-600">
              <ToggleButton active={colorMode === 'type'} onClick={() => setColorMode('type')}>By type</ToggleButton>
              <ToggleButton active={colorMode === 'confidence'} onClick={() => setColorMode('confidence')}>By confidence</ToggleButton>
            </div>
            <DrawingViewer
              elements={elements}
              selectedId={selectedElementId}
              onSelect={setSelectedElementId}
              colorMode={colorMode}
            />
            <Legend colorMode={colorMode} />
          </div>

          <div className="bg-white rounded-lg border border-ink-500/15 min-h-0 overflow-hidden">
            <BoqTable
              checklistRows={liveBoq ? liveBoq.checklist_rows : checklistRows}
              backupRows={liveBoq ? liveBoq.backup_rows : backupRows}
              activeItemCode={activeItemCode}
              onSelectItemCode={handleSelectItemCode}
              onStatusChange={(id, status) => updateChecklistRow(id, { status })}
            />
          </div>
        </div>

        <aside className="bg-white rounded-lg border border-ink-500/15 min-h-0">
          <ElementInspector element={selectedElement} onSave={updateElement} />
        </aside>
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* Import modal (portal-style overlay)                                  */}
      {/* ------------------------------------------------------------------ */}
      {showImportModal && (
        <ImportModal
          onClose={() => setShowImportModal(false)}
          onComplete={handleImportComplete}
        />
      )}
    </div>
  )
}

function ToggleButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`text-xs px-2 py-1 rounded font-medium transition ${
        active ? 'bg-brass text-white' : 'text-paper-200 hover:bg-canvas-700'
      }`}
    >
      {children}
    </button>
  )
}

function Legend({ colorMode }) {
  if (colorMode !== 'type') return null
  return (
    <div className="absolute bottom-3 right-3 z-10 bg-canvas-800/90 rounded-md p-2.5 border border-canvas-600 flex flex-col gap-1">
      {Object.entries(ELEMENT_TYPE_LABELS).map(([key, label]) => (
        <div key={key} className="flex items-center gap-1.5 text-[11px] text-paper-200">
          <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: ELEMENT_TYPE_COLORS[key] }} />
          {label}
        </div>
      ))}
    </div>
  )
}

function ConfigNotice() {
  return (
    <div className="h-screen flex items-center justify-center bg-paper-100 px-6">
      <div className="max-w-md bg-white border border-ink-500/15 rounded-lg p-6">
        <div className="text-sm font-mono uppercase tracking-wide text-brass mb-2">Setup needed</div>
        <h1 className="text-lg font-semibold text-ink-900 mb-2">Connect your Supabase project</h1>
        <p className="text-sm text-ink-700 mb-3">
          Copy <code className="bg-paper-200 px-1 rounded">.env.example</code> to <code className="bg-paper-200 px-1 rounded">.env</code> and
          fill in your project's URL and <strong>anon</strong> key (Project Settings → API). Never use the
          <code className="bg-paper-200 px-1 mx-1">service_role</code> key here.
        </p>
        <p className="text-sm text-ink-700">See README.md for the RLS policies this dashboard needs.</p>
      </div>
    </div>
  )
}
