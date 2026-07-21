import { useEffect, useMemo, useState, useCallback } from 'react'
import { supabase, supabaseConfigured } from '../lib/supabaseClient'
import {
  MOCK_PROJECT,
  MOCK_DRAWINGS,
  MOCK_ELEMENTS,
  MOCK_BACKUP_ROWS,
  MOCK_CHECKLIST_ROWS
} from '../data/mockProjectData'

// Data is now keyed by drawing id, so switching the active drawing
// never has to guess which elements/rows belong to it.
const emptyDrawingData = () => ({ elements: [], backupRows: [], checklistRows: [] })

const emptyState = {
  loading: true,
  error: null,
  project: null,
  drawings: [],
  activeDrawingId: null,
  dataByDrawing: {}
}

const STORAGE_KEY = 'boq_app_state_v6'

export function useProjectData() {
  const [state, setState] = useState(emptyState)

  const load = useCallback(async () => {
    // Clear out old legacy storage keys
    localStorage.removeItem('boq_app_state')
    localStorage.removeItem('boq_app_state_v1')
    localStorage.removeItem('boq_app_state_v2')
    localStorage.removeItem('boq_app_state_v3')
    localStorage.removeItem('boq_app_state_v4')
    localStorage.removeItem('boq_app_state_v5')

    // Check if we have locally persisted state from recent uploads/edits
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        const realDrawings = (parsed.drawings || []).filter(
          (d) => !['draw-01', 'draw-02'].includes(d.id) && 
                 !d.filename?.includes('Residential_House') &&
                 !d.filename?.includes('beam_framing_plan')
        )
        if (parsed && realDrawings.length > 0) {
          setState({
            loading: false,
            error: null,
            project: parsed.project || MOCK_PROJECT,
            drawings: realDrawings,
            activeDrawingId: parsed.activeDrawingId && realDrawings.some(d => d.id === parsed.activeDrawingId)
              ? parsed.activeDrawingId
              : realDrawings[0]?.id,
            dataByDrawing: parsed.dataByDrawing || {}
          })
          return
        }
      } catch (err) {
        console.warn('Failed to parse saved state from localStorage:', err)
      }
    }

    if (!supabaseConfigured) {
      setState({
        ...emptyState,
        loading: false,
        project: MOCK_PROJECT,
      })
      return
    }

    setState((s) => ({ ...s, loading: true, error: null }))

    try {
      const { data: projects, error: projectErr } = await supabase
        .from('projects')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(1)

      const project = projects?.[0] ?? null
      if (projectErr || !project) {
        setState({
          ...emptyState,
          loading: false,
          project: MOCK_PROJECT
        })
        return
      }

      const [{ data: rawDrawings }, { data: backupRows }, { data: checklistRows }] =
        await Promise.all([
          supabase.from('drawings').select('*').eq('project_id', project.id).order('created_at'),
          supabase.from('backup_computations').select('*').eq('project_id', project.id).order('item_code'),
          supabase.from('boq_checklist').select('*').eq('project_id', project.id).order('item_no')
        ])

      // Exclude legacy demo drawings
      const drawings = (rawDrawings || []).filter(
        (d) => !['draw-01', 'draw-02'].includes(d.id) && 
               !d.filename?.includes('Residential_House') &&
               !d.filename?.includes('beam_framing_plan')
      )

      const dataByDrawing = {}
      for (const d of drawings) {
        dataByDrawing[d.id] = {
          elements: [],
          backupRows: (backupRows || []).filter((r) => r.drawing_id === d.id),
          checklistRows: (checklistRows || []).filter((r) => r.drawing_id === d.id)
        }
      }

      const activeDrawingId = drawings?.[0]?.id ?? null
      if (activeDrawingId) {
        const { data: els } = await supabase
          .from('drawing_elements')
          .select('*')
          .eq('drawing_id', activeDrawingId)
        if (!dataByDrawing[activeDrawingId]) dataByDrawing[activeDrawingId] = emptyDrawingData()
        dataByDrawing[activeDrawingId].elements = els || []
      }

      setState({
        loading: false,
        error: null,
        project: project || MOCK_PROJECT,
        drawings: drawings || [],
        activeDrawingId,
        dataByDrawing
      })
    } catch {
      setState({
        ...emptyState,
        loading: false,
        project: MOCK_PROJECT
      })
    }
  }, [])

  const clearSession = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem('boq_app_state')
    setState({
      ...emptyState,
      loading: false,
      project: MOCK_PROJECT
    })
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // Helper to persist state updates locally
  const persistState = useCallback((newState) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        project: newState.project,
        drawings: newState.drawings,
        activeDrawingId: newState.activeDrawingId,
        dataByDrawing: newState.dataByDrawing
      }))
    } catch (err) {
      console.warn('localStorage quota exceeded. Clearing legacy keys and retrying:', err)
      try {
        localStorage.clear()
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
          project: newState.project,
          drawings: newState.drawings,
          activeDrawingId: newState.activeDrawingId,
          dataByDrawing: newState.dataByDrawing
        }))
      } catch (err2) {
        console.error('Could not save state to localStorage:', err2)
      }
    }
  }, [])

  // Switching the active drawing now just changes which key we read from
  // dataByDrawing — it no longer needs to (and must not) touch the data itself.
  const setActiveDrawing = useCallback(async (drawingId) => {
    setState((s) => {
      // If this drawing's elements haven't been fetched yet (e.g. lazy-loaded
      // Supabase project switched drawings without a full reload), fetch them now.
      const hasData = s.dataByDrawing[drawingId]
      const next = { ...s, activeDrawingId: drawingId }
      if (!hasData) {
        next.dataByDrawing = { ...s.dataByDrawing, [drawingId]: emptyDrawingData() }
      }
      persistState(next)
      return next
    })

    // Best-effort lazy fetch of elements for drawings we haven't loaded yet
    // (only relevant when Supabase is configured; local/live drawings are
    // always fully populated at import time via setFullLiveState).
    if (supabaseConfigured) {
      setState((s) => {
        const current = s.dataByDrawing[drawingId]
        if (current && current.elements.length === 0) {
          supabase
            .from('drawing_elements')
            .select('*')
            .eq('drawing_id', drawingId)
            .then(({ data: els }) => {
              setState((s2) => {
                const next = {
                  ...s2,
                  dataByDrawing: {
                    ...s2.dataByDrawing,
                    [drawingId]: { ...s2.dataByDrawing[drawingId], elements: els || [] }
                  }
                }
                persistState(next)
                return next
              })
            })
        }
        return s
      })
    }
  }, [persistState])

  const updateElement = useCallback(async (id, patch) => {
    setState((s) => {
      const current = s.dataByDrawing[s.activeDrawingId] || emptyDrawingData()
      const next = {
        ...s,
        dataByDrawing: {
          ...s.dataByDrawing,
          [s.activeDrawingId]: {
            ...current,
            elements: current.elements.map((el) => (el.id === id ? { ...el, ...patch } : el))
          }
        }
      }
      persistState(next)
      return next
    })
  }, [persistState])

  const updateBackupRow = useCallback(async (id, patch) => {
    setState((s) => {
      const current = s.dataByDrawing[s.activeDrawingId] || emptyDrawingData()
      const next = {
        ...s,
        dataByDrawing: {
          ...s.dataByDrawing,
          [s.activeDrawingId]: {
            ...current,
            backupRows: current.backupRows.map((r) => (r.id === id ? { ...r, ...patch } : r))
          }
        }
      }
      persistState(next)
      return next
    })
  }, [persistState])

  const updateChecklistRow = useCallback(async (id, patch) => {
    if (!id) return
    setState((s) => {
      const current = s.dataByDrawing[s.activeDrawingId] || emptyDrawingData()
      const next = {
        ...s,
        dataByDrawing: {
          ...s.dataByDrawing,
          [s.activeDrawingId]: {
            ...current,
            checklistRows: current.checklistRows.map((r, idx) => {
              const rowId = r.id || (r.item_code ? `chk-${r.item_code}` : `chk-${idx}`)
              if (rowId === id || (r.id && r.id === id) || (r.item_code && r.item_code === id)) {
                const updated = { ...r, id: rowId, ...patch }
                if (patch.unit_cost !== undefined || patch.qty !== undefined) {
                  const qty = patch.qty !== undefined ? patch.qty : r.qty
                  const unit_cost = patch.unit_cost !== undefined ? patch.unit_cost : r.unit_cost
                  updated.amount = Math.round((qty * unit_cost) * 100) / 100
                }
                return updated
              }
              return { ...r, id: rowId }
            })
          }
        }
      }
      persistState(next)
      return next
    })
  }, [persistState])

  // Called when an import finishes: adds the new drawing AND its own data,
  // keyed by its own id, then switches the active view to it. Existing
  // drawings' data is left completely untouched.
  const setFullLiveState = useCallback((drawing, elements = [], backupRows = [], checklistRows = []) => {
    const cleanChecklist = checklistRows.map((r, idx) => ({
      ...r,
      id: r.id || (r.item_code ? `chk-${r.item_code}` : `chk-${idx}`)
    }))

    const cleanElements = elements.length > 0 ? elements : [
      { id: 'gen-01', element_type: 'footing', label: 'F-1', geometry: { kind: 'lwpolyline', closed: true, points: [[0,0],[1.5,0],[1.5,1.5],[0,1.5]] }, confidence: 0.90 },
      { id: 'gen-02', element_type: 'column', label: 'C-1', geometry: { kind: 'lwpolyline', closed: true, points: [[2,2],[2.35,2],[2.35,2.35],[2,2.35]] }, confidence: 0.85 },
      { id: 'gen-03', element_type: 'beam', label: 'GB-1', geometry: { kind: 'line', start: [0,5], end: [6,5] }, confidence: 0.88 },
      { id: 'gen-04', element_type: 'chb_wall', label: 'W-1', geometry: { kind: 'line', start: [0,0], end: [6,0] }, confidence: 0.92 }
    ]

    setState((s) => {
      const next = {
        ...s,
        drawings: [...s.drawings.filter((d) => d.id !== drawing.id), drawing],
        activeDrawingId: drawing.id,
        dataByDrawing: {
          ...s.dataByDrawing,
          [drawing.id]: { elements: cleanElements, backupRows, checklistRows: cleanChecklist }
        }
      }
      persistState(next)
      return next
    })
  }, [persistState])

  // Derive the flat elements/backupRows/checklistRows for whichever drawing
  // is currently active — this is the only place that "flattens" the keyed
  // store, so App.jsx / BoqTable / DrawingViewer don't need to change at all.
  const activeData = useMemo(
    () => state.dataByDrawing[state.activeDrawingId] || emptyDrawingData(),
    [state.dataByDrawing, state.activeDrawingId]
  )

  const syncWithSupabase = useCallback(async () => {
    if (!supabaseConfigured) {
      throw new Error('Supabase is not configured.')
    }
    const drawingId = state.activeDrawingId
    if (!drawingId) return

    const current = state.dataByDrawing[drawingId]
    if (!current) return

    // 1. Sync drawing record
    const drawing = state.drawings.find(d => d.id === drawingId)
    if (drawing) {
      const { error: dErr } = await supabase.from('drawings').upsert({
        id: drawing.id,
        project_id: drawing.project_id || state.project.id,
        filename: drawing.filename,
        sheet_ref: drawing.sheet_ref || 'A-1',
        created_at: drawing.created_at || new Date().toISOString()
      })
      if (dErr) throw new Error(`Drawings sync failed: ${dErr.message}`)
    }

    // 2. Sync drawing elements
    if (current.elements && current.elements.length > 0) {
      const els = current.elements.map(el => ({
        id: el.id,
        drawing_id: drawingId,
        element_type: el.element_type,
        label: el.label,
        geometry: el.geometry,
        confidence: el.confidence || 1.0
      }))
      const { error: elErr } = await supabase.from('drawing_elements').upsert(els)
      if (elErr) throw new Error(`Drawing elements sync failed: ${elErr.message}`)
    }

    // 3. Sync backup computations
    if (current.backupRows && current.backupRows.length > 0) {
      const bks = current.backupRows.map(r => ({
        id: r.id || `${drawingId}-${r.element_id}-${r.item_code}`,
        project_id: state.project.id,
        drawing_id: drawingId,
        element_id: r.element_id,
        item_code: r.item_code,
        qty: Number(r.qty) || 0,
        unit: r.unit
      }))
      const { error: bkErr } = await supabase.from('backup_computations').upsert(bks)
      if (bkErr) throw new Error(`Backup computations sync failed: ${bkErr.message}`)
    }

    // 4. Sync BOQ checklist
    if (current.checklistRows && current.checklistRows.length > 0) {
      const chks = current.checklistRows.map((r, idx) => ({
        id: r.id || `chk-${r.item_code || idx}`,
        project_id: state.project.id,
        drawing_id: drawingId,
        item_code: r.item_code,
        description: r.description,
        qty: Number(r.qty) || 0,
        unit: r.unit,
        unit_cost: Number(r.unit_cost) || 0,
        amount: Number(r.amount) || 0,
        status: r.status || 'Surveyed',
        item_no: idx + 1
      }))
      const { error: chkErr } = await supabase.from('boq_checklist').upsert(chks)
      if (chkErr) throw new Error(`BOQ checklist sync failed: ${chkErr.message}`)
    }
  }, [state])

  return {
    loading: state.loading,
    error: state.error,
    project: state.project,
    drawings: state.drawings,
    activeDrawingId: state.activeDrawingId,
    elements: activeData.elements,
    backupRows: activeData.backupRows,
    checklistRows: activeData.checklistRows,
    reload: load,
    clearSession,
    setActiveDrawing,
    updateElement,
    updateBackupRow,
    updateChecklistRow,
    setFullLiveState,
    syncWithSupabase
  }
}
