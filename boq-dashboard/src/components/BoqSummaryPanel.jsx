import { useMemo, useState } from 'react'

const currency = (n) =>
  new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP', maximumFractionDigits: 2 }).format(n || 0)

export default function BoqSummaryPanel({ checklistRows, backupRows }) {
  const [collapsed, setCollapsed] = useState(false)

  const boqSummary = useMemo(() => {
    let concreteTotal = 0
    let rebarTotal = 0
    let masonryTotal = 0

    const rows = checklistRows || []
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
  }, [checklistRows])

  return (
    <div className="border border-ink-500/15 rounded-lg bg-white overflow-hidden shadow-sm transition-all">
      {/* Panel Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-3.5 py-2.5 bg-paper-50 border-b border-ink-500/10 text-left hover:bg-paper-100 transition"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold text-ink-900 uppercase tracking-wide">
            BOQ Executive Cost Summary
          </span>
        </div>
        <span className="text-xs font-mono font-bold text-ink-500 hover:text-ink-900 px-1">
          {collapsed ? '[+] Expand' : '[−] Collapse'}
        </span>
      </button>

      {/* Collapsible Content */}
      {!collapsed && (
        <div className="p-3 space-y-2.5 text-xs">
          <div className="bg-paper-50/80 p-2.5 rounded border border-ink-500/10">
            <div className="text-[10px] text-ink-500 uppercase font-mono font-medium">Trade I: Concrete Works</div>
            <div className="text-sm font-semibold font-mono text-ink-900 mt-0.5">{currency(boqSummary.concreteTotal)}</div>
          </div>

          <div className="bg-paper-50/80 p-2.5 rounded border border-ink-500/10">
            <div className="text-[10px] text-ink-500 uppercase font-mono font-medium">Trade II: Steel Reinforcement</div>
            <div className="text-sm font-semibold font-mono text-ink-900 mt-0.5">{currency(boqSummary.rebarTotal)}</div>
          </div>

          <div className="bg-paper-50/80 p-2.5 rounded border border-ink-500/10">
            <div className="text-[10px] text-ink-500 uppercase font-mono font-medium">Trade III: Masonry Works</div>
            <div className="text-sm font-semibold font-mono text-ink-900 mt-0.5">{currency(boqSummary.masonryTotal)}</div>
          </div>

          <div className="bg-brass/10 p-2.5 rounded border border-brass/35">
            <div className="text-[10px] text-brass uppercase font-mono font-bold">Grand Total Direct Cost</div>
            <div className="text-base font-bold font-mono text-brass mt-0.5">{currency(boqSummary.grandTotal)}</div>
          </div>
        </div>
      )}
    </div>
  )
}
