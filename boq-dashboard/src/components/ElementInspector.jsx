import { useState, useEffect } from 'react'
import { ELEMENT_TYPE_LABELS, confidenceColor, confidenceLabel } from '../utils/visualStyle'

const ELEMENT_TYPES = ['footing', 'column', 'beam', 'slab', 'chb_wall', 'other']
const CONCRETE_CLASSES = ['Class AA', 'Class A', 'Class B', 'Class C', 'Thin Topping']

export default function ElementInspector({ element, onSave }) {
  const [draft, setDraft] = useState(element)
  const [saving, setSaving] = useState(false)
  const [savedAt, setSavedAt] = useState(null)
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    setDraft(element)
    setSavedAt(null)
  }, [element?.id])

  const dirty = (draft?.element_type !== element?.element_type) || (draft?.concrete_class !== element?.concrete_class)

  const save = async () => {
    if (!element) return
    setSaving(true)
    try {
      await onSave(element.id, {
        element_type: draft.element_type,
        concrete_class: draft.concrete_class || null,
        confidence: 1.0 // a human-confirmed classification is treated as fully confident
      })
      setSavedAt(new Date())
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="border border-ink-500/15 rounded-lg bg-white overflow-hidden shadow-sm transition-all">
      {/* Panel Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-3.5 py-2.5 bg-paper-50 border-b border-ink-500/10 text-left hover:bg-paper-100 transition"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold text-ink-900 uppercase tracking-wide">
            Element Inspector {element ? `(${element.label || element.id})` : ''}
          </span>
        </div>
        <span className="text-xs font-mono font-bold text-ink-500 hover:text-ink-900 px-1">
          {collapsed ? '[+] Expand' : '[−] Collapse'}
        </span>
      </button>

      {/* Collapsible Content */}
      {!collapsed && (
        <div className="p-3 space-y-3">
          {!element ? (
            <div className="py-6 text-center text-ink-500 text-xs leading-relaxed">
              Select an element on the drawing canvas or a row in the BOQ checklist table to review or override its classification.
            </div>
          ) : (
            <>
              <div>
                <div className="text-[10px] font-mono uppercase tracking-wide text-ink-500">Selected Element Label</div>
                <div className="font-mono text-sm text-ink-900 font-semibold mt-0.5">{element.label || element.id}</div>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className="inline-block w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: confidenceColor(element.confidence) }}
                />
                <span className="text-xs text-ink-700 font-mono">
                  {confidenceLabel(element.confidence)} · {Math.round((element.confidence || 0) * 100)}%
                </span>
              </div>

              <div className="text-xs font-mono text-ink-500 bg-paper-100 rounded p-2 space-y-0.5">
                <div>layer: {element.raw_source?.layer ?? '—'}</div>
                <div>entity: {element.raw_source?.entity_type ?? '—'}</div>
                {element.raw_source?.text ? <div>text: "{element.raw_source.text}"</div> : null}
              </div>

              <label className="block">
                <span className="text-xs font-medium text-ink-700">Element Type</span>
                <select
                  className="mt-1 w-full rounded border border-ink-500/30 bg-white px-2 py-1.5 text-xs font-mono"
                  value={draft?.element_type || 'other'}
                  onChange={(e) => setDraft((d) => ({ ...d, element_type: e.target.value }))}
                >
                  {ELEMENT_TYPES.map((t) => (
                    <option key={t} value={t}>{ELEMENT_TYPE_LABELS[t]}</option>
                  ))}
                </select>
              </label>

              {draft?.element_type !== 'other' && draft?.element_type !== 'chb_wall' && (
                <label className="block">
                  <span className="text-xs font-medium text-ink-700">Concrete Class</span>
                  <select
                    className="mt-1 w-full rounded border border-ink-500/30 bg-white px-2 py-1.5 text-xs font-mono"
                    value={draft?.concrete_class || ''}
                    onChange={(e) => setDraft((d) => ({ ...d, concrete_class: e.target.value }))}
                  >
                    <option value="">— unset —</option>
                    {CONCRETE_CLASSES.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </label>
              )}

              <div className="pt-2 flex items-center gap-3">
                <button
                  disabled={!dirty || saving}
                  onClick={save}
                  className="w-full px-3 py-1.5 text-xs font-medium rounded bg-brass text-white disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110 transition font-mono"
                >
                  {saving ? 'Saving…' : 'Confirm Override'}
                </button>
              </div>
              {savedAt && !dirty && (
                <div className="text-[11px] text-flag-ok font-mono text-center">✓ Saved · confidence set to 100%</div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
