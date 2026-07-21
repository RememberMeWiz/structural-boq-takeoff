// Tech Spec §2.5.0: "Automated Dual Cross-Checking: Run at least two
// independently-derived calculations per element type. Flag divergence
// beyond ~1-2% for manual review."
//
// The schema gives us two independently-maintained figures for the same
// item_code:
//   1. Back-Up Computations: individual element-level quantities, summed.
//   2. BOQ Checklist: the rolled-up quantity for that item_code.
// These should reconcile. When they don't, an element was likely added,
// edited, or overridden after the checklist was last rolled up, or the
// rollup was computed independently and disagrees — exactly the kind of
// thing this dashboard is supposed to catch before the BOQ ships.

export const DIVERGENCE_THRESHOLD_PCT = 2

export function sumBackupQtyByItemCode(backupRows) {
  const totals = new Map()
  for (const row of backupRows) {
    const prev = totals.get(row.item_code) || 0
    totals.set(row.item_code, prev + Number(row.quantity || 0))
  }
  return totals
}

export function computeDivergence(checklistRows, backupRows) {
  const backupTotals = sumBackupQtyByItemCode(backupRows)
  return checklistRows.map((item) => {
    const backupQty = backupTotals.get(item.item_code) ?? null
    if (backupQty === null) {
      return { ...item, backupQty: null, divergencePct: null, flagged: false }
    }
    const denom = Math.max(Math.abs(backupQty), 1e-9)
    const divergencePct = (Math.abs(Number(item.qty) - backupQty) / denom) * 100
    return {
      ...item,
      backupQty,
      divergencePct,
      flagged: divergencePct > DIVERGENCE_THRESHOLD_PCT
    }
  })
}
