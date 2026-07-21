import { useMemo, useState } from 'react'
import { computeDivergence, DIVERGENCE_THRESHOLD_PCT } from '../utils/dualCheck'

const STATUS_OPTIONS = ['Confirmed', 'Surveyed', 'N/A']

const CMPD_RATES = {
  'CON-1.1': 4952.70, // Concrete Works - Isolated Footings
  'CON-1.2': 4952.70, // Concrete Works - Columns
  'CON-1.3': 4964.96, // Concrete Works - Beams
  'CON-1.4': 4952.70, // Concrete Works - Slabs
  'REB-2.16': 54.68,  // Grade 40 Rebar 16mm
  'REB-2.20': 54.68,  // Grade 40 Rebar 20mm
  'REB-2.12': 54.68,  // Grade 40 Rebar 12mm
  'REB-2.10': 54.68,  // Grade 40 Rebar 10mm
  'REB-2.0': 62.50,   // #16 G.I. Tie Wire
  'MAS-3.2': 830.16,  // 150mm CHB Wall
  'MAS-3.3': 173.00,  // 16mm Cement Plaster
}

const currency = (n) =>
  new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP', maximumFractionDigits: 2 }).format(n || 0)

export default function BoqTable({ checklistRows, backupRows, onSelectItemCode, activeItemCode, onStatusChange, onUnitCostChange }) {
  const [showFlaggedOnly, setShowFlaggedOnly] = useState(false)
  const rows = useMemo(() => computeDivergence(checklistRows, backupRows), [checklistRows, backupRows])
  const visibleRows = showFlaggedOnly ? rows.filter((r) => r.flagged) : rows
  const flaggedCount = rows.filter((r) => r.flagged).length

  // Calculate Trade Summaries
  const boqSummary = useMemo(() => {
    let concreteTotal = 0
    let rebarTotal = 0
    let masonryTotal = 0

    rows.forEach((r) => {
      const amt = Number(r.amount) || 0
      const code = (r.item_code || '').toUpperCase()
      if (code.startsWith('CON')) concreteTotal += amt
      else if (code.startsWith('REB')) rebarTotal += amt
      else if (code.startsWith('MAS')) masonryTotal += amt
      else concreteTotal += amt
    })

    const grandTotal = concreteTotal + rebarTotal + masonryTotal
    return { concreteTotal, rebarTotal, masonryTotal, grandTotal }
  }, [rows])

  const handleApplyAllCmpd = () => {
    rows.forEach((r, idx) => {
      const rowId = r.id || (r.item_code ? `chk-${r.item_code}` : `chk-${idx}`)
      const cmpdRate = CMPD_RATES[r.item_code] || 0
      if (cmpdRate > 0) {
        onUnitCostChange?.(rowId, cmpdRate)
      }
    })
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header controls */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-ink-500/15 bg-paper-50">
        <div className="flex items-center gap-3">
          <div className="text-sm font-medium text-ink-900">Costed BOQ Checklist</div>
          <button
            onClick={handleApplyAllCmpd}
            title="Populate all items with standard DPWH CMPD material rates"
            className="px-2 py-1 text-xs font-mono rounded bg-brass/15 text-brass hover:bg-brass/25 transition-colors font-medium"
          >
            Use CMPD Values for All
          </button>
        </div>
        <label className="flex items-center gap-1.5 text-xs text-ink-700">
          <input
            type="checkbox"
            checked={showFlaggedOnly}
            onChange={(e) => setShowFlaggedOnly(e.target.checked)}
          />
          Show divergence flags only
          {flaggedCount > 0 && (
            <span className="ml-1 px-1.5 py-0.5 rounded-full bg-flag-warn/15 text-flag-warn font-mono text-[11px]">
              {flaggedCount}
            </span>
          )}
        </label>
      </div>

      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-paper-50 text-[11px] uppercase tracking-wide text-ink-500 text-left">
            <tr>
              <th className="px-4 py-2 font-medium">Item</th>
              <th className="px-3 py-2 font-medium">Description</th>
              <th className="px-3 py-2 font-medium text-right">Qty</th>
              <th className="px-3 py-2 font-medium text-right">Backup Σ</th>
              <th className="px-3 py-2 font-medium text-right">Unit cost (₱)</th>
              <th className="px-3 py-2 font-medium text-right">Amount</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Check</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, idx) => {
              const rowId = row.id || (row.item_code ? `chk-${row.item_code}` : `chk-${idx}`)
              const cmpdRate = CMPD_RATES[row.item_code] || 0
              return (
                <tr
                  key={rowId}
                  onClick={() => onSelectItemCode?.(row.item_code)}
                  className={`border-b border-ink-500/10 cursor-pointer transition-colors ${
                    row.item_code === activeItemCode ? 'bg-brass/10' : row.flagged ? 'bg-flag-warn/5 hover:bg-flag-warn/10' : 'hover:bg-paper-100'
                  }`}
                >
                  <td className="px-4 py-2 font-mono text-xs text-ink-700">{row.item_code}</td>
                  <td className="px-3 py-2">{row.description}</td>
                  <td className="px-3 py-2 text-right font-mono">{Number(row.qty).toLocaleString()} {row.unit}</td>
                  <td className="px-3 py-2 text-right font-mono text-ink-500">
                    {row.backupQty != null ? Number(row.backupQty).toLocaleString(undefined, { maximumFractionDigits: 3 }) : '—'}
                  </td>
                  <td className="px-3 py-2 text-right font-mono" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-1.5">
                      <input
                        type="number"
                        step="0.01"
                        value={row.unit_cost ?? 0}
                        onChange={(e) => onUnitCostChange?.(rowId, parseFloat(e.target.value) || 0)}
                        className="w-20 text-right px-1.5 py-0.5 border border-ink-500/20 rounded text-xs focus:border-brass focus:outline-none bg-white font-mono"
                      />
                      {cmpdRate > 0 && (
                        <button
                          onClick={() => onUnitCostChange?.(rowId, cmpdRate)}
                          title={`Set to DPWH CMPD rate (₱${cmpdRate.toLocaleString()})`}
                          className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-brass/10 text-brass hover:bg-brass/25 transition-colors whitespace-nowrap"
                        >
                          Use CMPD Value
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right font-mono font-medium">{currency(row.amount)}</td>
                  <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                    <select
                      value={row.status}
                      onChange={(e) => onStatusChange?.(rowId, e.target.value)}
                      className={`text-xs px-1.5 py-0.5 rounded border-0 cursor-pointer ${
                        row.status === 'Confirmed'
                          ? 'bg-flag-ok/15 text-flag-ok'
                          : row.status === 'N/A'
                          ? 'bg-ink-500/10 text-ink-500'
                          : 'bg-conf-mid/15 text-brass'
                      }`}
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    {row.divergencePct === null ? (
                      <span className="text-xs text-ink-500">no backup data</span>
                    ) : row.flagged ? (
                      <span
                        className="text-xs font-medium text-flag-warn"
                        title={`Checklist qty diverges from summed Back-Up Computation qty by more than ${DIVERGENCE_THRESHOLD_PCT}%`}
                      >
                        ⚠ {row.divergencePct.toFixed(1)}% divergence
                      </span>
                    ) : (
                      <span className="text-xs text-flag-ok">✓ {row.divergencePct.toFixed(1)}%</span>
                    )}
                  </td>
                </tr>
              )
            })}
            {visibleRows.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-ink-500 text-sm">
                  {showFlaggedOnly ? 'No divergence flags — everything reconciles within 2%.' : 'No BOQ checklist rows yet for this project.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
