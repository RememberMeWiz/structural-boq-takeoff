import React, { useMemo, useState, useCallback } from 'react'
import { useProjectData } from './hooks/useProjectData'
import { useExport } from './hooks/useExport'
import DrawingViewer from './components/DrawingViewer'
import ElementInspector from './components/ElementInspector'
import BoqTable from './components/BoqTable'
import BoqSummaryPanel from './components/BoqSummaryPanel'
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
              onClick={() => {
                try { localStorage.clear() } catch {}
                window.location.reload()
              }}
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
    backupRows, checklistRows, setActiveDrawing, updateElement, updateChecklistRow, reload, clearSession, setFullLiveState, syncWithSupabase
  } = useProjectData()

  const { exportXlsx, exportPdf, exporting, exportError } = useExport()

  const [selectedElementId, setSelectedElementId] = useState(null)
  const [colorMode, setColorMode] = useState('type') // 'type' | 'confidence'
  const [showImportModal, setShowImportModal] = useState(false)
  const [activeJobId, setActiveJobId] = useState(null)
  const [importBanner, setImportBanner] = useState(null)
  const [syncing, setSyncing] = useState(false)

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncWithSupabase()
      setImportBanner({ type: 'success', text: 'Successfully synced all local edits to Supabase database!' })
    } catch (e) {
      setImportBanner({ type: 'error', text: `Sync failed: ${e.message}` })
    } finally {
      setSyncing(false)
    }
  }

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

  const handleImportComplete = useCallback((jobId, boq, filename = 'Imported Drawing') => {
    setActiveJobId(jobId)
    setShowImportModal(false)
    if (boq && boq.backup_rows?.length > 0) {
      const newDrawing = {
        id: jobId,
        project_id: project?.id ?? 'live',
        filename: filename,
        sheet_ref: 'A-1',
        created_at: new Date().toISOString()
      }
      setFullLiveState(
        newDrawing,
        boq.elements || [],
        boq.backup_rows || [],
        boq.checklist_rows || []
      )

      setImportBanner({ type: 'success', text: `Drawing processed: ${boq.backup_rows.length} takeoff rows computed. Use the Export buttons to download.` })
    } else {
      setImportBanner({ type: 'error', text: 'No BOQ data was extracted — check file contents.' })
    }
  }, [project, setFullLiveState])

  if (!supabaseConfigured) {
    return <ConfigNotice />
  }

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-paper-100 text-ink-500 font-mono text-sm">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-brass animate-ping" />
          Loading BOQ system data…
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-paper-100 font-sans text-ink-900 overflow-hidden">
      {/* Top Header Navigation */}
      <header className="h-14 bg-white border-b border-ink-500/15 px-4 flex items-center justify-between shrink-0 shadow-sm">
        <div className="flex items-center gap-3">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-widest text-ink-500">BOQ Review Dashboard</div>
            <div className="text-sm font-semibold text-ink-900 leading-tight">
              {project?.name || 'Structural BOQ Takeoff Project'}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Drawing selector */}
          <select
            id="select-drawing"
            value={activeDrawingId || ''}
            onChange={(e) => setActiveDrawing(e.target.value)}
            className="text-xs rounded border border-ink-500/25 bg-paper-50 px-2.5 py-1.5 font-mono text-ink-900 focus:border-brass focus:outline-none"
          >
            {drawings.map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename} ({d.sheet_ref || 'sheet'})
              </option>
            ))}
          </select>

          {/* Import Button */}
          <button
            id="btn-import-drawing"
            onClick={() => setShowImportModal(true)}
            className="text-xs px-3 py-1.5 rounded font-mono font-medium bg-brass text-white hover:brightness-110 shadow-sm transition flex items-center gap-1.5"
          >
            <span className="text-sm leading-none">↑</span> Import Drawing
          </button>

          {/* Sync Button */}
          <button
            onClick={handleSync}
            disabled={syncing}
            className="text-xs px-3 py-1.5 rounded font-mono font-medium bg-flag-ok text-white hover:brightness-110 shadow-sm transition flex items-center gap-1.5"
          >
            {syncing ? '⏳ Syncing…' : '☁ Sync Supabase'}
          </button>

          {/* Export Buttons */}
          <div className="h-4 w-px bg-ink-500/20" />
          <button
            id="btn-export-excel"
            disabled={exporting !== null}
            onClick={() => exportXlsx(activeJobId)}
            className="text-xs px-2.5 py-1.5 rounded border border-ink-500/25 bg-white hover:bg-paper-100 disabled:opacity-40 transition font-mono flex items-center gap-1"
          >
            {exporting === 'xlsx' ? '⏳' : '📊'} Excel
          </button>

          <button
            id="btn-export-pdf"
            disabled={exporting !== null}
            onClick={() => exportPdf(activeJobId)}
            className="text-xs px-2.5 py-1.5 rounded border border-ink-500/25 bg-white hover:bg-paper-100 disabled:opacity-40 transition font-mono flex items-center gap-1"
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

          <button
            id="btn-clear-session"
            onClick={clearSession}
            className="text-xs px-2.5 py-1.5 rounded border border-flag-warn/30 text-flag-warn hover:bg-flag-warn/10 transition"
            title="Clear stored drawing session and reset to empty state"
          >
            Reset Session
          </button>
        </div>
      </header>

      {/* Error Banners */}
      {error && (
        <div className="px-5 py-2 bg-flag-warn/10 text-flag-warn text-sm border-b border-flag-warn/20 flex items-center justify-between">
          <span>⚠ {error}</span>
          <button onClick={() => window.location.reload()} className="ml-3 text-flag-warn/70 hover:text-flag-warn text-xs underline">Retry</button>
        </div>
      )}

      {exportError && (
        <div className="px-5 py-2 bg-flag-warn/10 text-flag-warn text-sm border-b border-flag-warn/20 flex items-center justify-between">
          <span>Export error: {exportError}</span>
        </div>
      )}

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

      {/* Main Grid Layout */}
      <main className="flex-1 min-h-0 grid grid-cols-[1fr_320px] gap-3 p-3">
        {/* Left Container: Canvas (top) + BOQ Checklist Table (bottom full height) */}
        <div className="grid grid-rows-[1fr_1.1fr] gap-3 min-h-0">
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

          <div className="bg-white rounded-lg border border-ink-500/15 min-h-0 overflow-hidden shadow-sm">
            <BoqTable
              checklistRows={checklistRows}
              backupRows={backupRows}
              activeItemCode={activeItemCode}
              onSelectItemCode={handleSelectItemCode}
              onStatusChange={(id, status) => updateChecklistRow(id, { status })}
              onUnitCostChange={(id, unit_cost) => updateChecklistRow(id, { unit_cost })}
            />
          </div>
        </div>

        {/* Right Sidebar Container: Collapsible BOQ Summary + Collapsible Element Inspector */}
        <aside className="min-h-0 overflow-y-auto space-y-3 pr-0.5">
          <BoqSummaryPanel checklistRows={checklistRows} backupRows={backupRows} />
          <ElementInspector element={selectedElement} onSave={updateElement} />
        </aside>
      </main>

      {/* Import Modal Overlay */}
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
          Copy <code className="bg-paper-200 px-1 rounded">.env.example</code> to <code className="bg-paper-200 px-1 rounded">.env</code>.
        </p>
      </div>
    </div>
  )
}
