import { useMemo, useRef, useState, useCallback } from 'react'
import { computeBounds, projectPoint } from '../utils/geometry'
import { ELEMENT_TYPE_COLORS, confidenceColor } from '../utils/visualStyle'

export default function DrawingViewer({ elements, selectedId, onSelect, colorMode }) {
  const bounds = useMemo(() => computeBounds(elements), [elements])
  const w = bounds.maxX - bounds.minX
  const h = bounds.maxY - bounds.minY

  const viewRef = useRef({ x: 0, y: 0, w, h })
  const svgRef = useRef(null)
  const dragging = useRef(null)
  const [, forceRender] = useState(0)

  // Reset the view whenever the underlying drawing (bounds) changes.
  const boundsKey = `${bounds.minX}-${bounds.minY}-${bounds.maxX}-${bounds.maxY}`
  const lastBoundsKey = useRef(boundsKey)
  if (lastBoundsKey.current !== boundsKey) {
    lastBoundsKey.current = boundsKey
    viewRef.current = { x: 0, y: 0, w, h }
  }
  const v = viewRef.current

  const applyView = (next) => {
    viewRef.current = next
    forceRender((n) => n + 1)
  }

  const onWheel = useCallback((e) => {
    e.preventDefault()
    const factor = e.deltaY > 0 ? 1.1 : 0.9
    const cur = viewRef.current
    const rect = svgRef.current.getBoundingClientRect()
    const mx = (e.clientX - rect.left) / rect.width
    const my = (e.clientY - rect.top) / rect.height
    const newW = cur.w * factor
    const newH = cur.h * factor
    const newX = cur.x + (cur.w - newW) * mx
    const newY = cur.y + (cur.h - newH) * my
    applyView({ x: newX, y: newY, w: newW, h: newH })
  }, [])

  const onPointerDown = useCallback((e) => {
    dragging.current = { startX: e.clientX, startY: e.clientY, view: viewRef.current }
    e.currentTarget.setPointerCapture(e.pointerId)
  }, [])

  const onPointerMove = useCallback((e) => {
    if (!dragging.current) return
    const rect = svgRef.current.getBoundingClientRect()
    const { startX, startY, view: startView } = dragging.current
    const dx = ((e.clientX - startX) / rect.width) * startView.w
    const dy = ((e.clientY - startY) / rect.height) * startView.h
    applyView({ ...startView, x: startView.x - dx, y: startView.y - dy })
  }, [])

  const onPointerUp = useCallback(() => {
    dragging.current = null
  }, [])

  const resetView = () => applyView({ x: 0, y: 0, w, h })

  const strokeFor = (el) =>
    colorMode === 'confidence' ? confidenceColor(el.confidence) : (ELEMENT_TYPE_COLORS[el.element_type] || ELEMENT_TYPE_COLORS.other)

  return (
    <div className="relative h-full w-full bg-canvas-900 rounded-lg overflow-hidden border border-canvas-600">
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        <button
          onClick={resetView}
          className="px-2.5 py-1 text-xs font-mono rounded bg-canvas-700 text-paper-100 border border-canvas-500 hover:bg-canvas-600 transition-colors"
        >
          Fit to view
        </button>
        <div className="px-3 py-1 text-xs font-mono rounded bg-canvas-800/90 text-brass border border-brass/40 flex items-center gap-1.5 shadow-md">
          <span className="w-2 h-2 rounded-full bg-flag-ok animate-pulse" />
          <span className="font-semibold tracking-wide uppercase">Structural Framing Plan View</span>
        </div>
      </div>
      <div className="absolute bottom-3 left-3 z-10 text-[11px] font-mono text-paper-200/60">
        scroll to zoom · drag to pan
      </div>
      {(!elements || elements.length === 0) && (
        <div className="absolute inset-0 flex items-center justify-center text-paper-200/50 font-mono text-xs pointer-events-none">
          No vector elements to display for this drawing.
        </div>
      )}
      <svg
        ref={svgRef}
        viewBox={`${v.x} ${v.y} ${v.w} ${v.h}`}
        className="w-full h-full cursor-grab active:cursor-grabbing touch-none"
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
      >
        {elements.map((el) => {
          const isSelected = el.id === selectedId
          const stroke = strokeFor(el)
          const strokeWidth = (isSelected ? 3 : 1.4) * (v.w / (w || 1))
          const fontSize = Math.max(10, Math.min(18, 12 * (v.w / (w || 1))))
          const commonProps = {
            stroke: isSelected ? '#f2c14e' : stroke,
            strokeWidth,
            fill: el.geometry?.closed ? `${stroke}22` : 'none',
            strokeLinecap: 'round',
            opacity: isSelected ? 1 : 0.85,
            onClick: (e) => {
              e.stopPropagation()
              onSelect?.(el.id)
            },
            className: 'cursor-pointer hover:opacity-100'
          }

          let shapeNode = null
          let cx = 0
          let cy = 0
          const labelText = el.label || (el.id && !el.id.startsWith('pdf-el-') ? el.id : null)

          if (el.geometry?.kind === 'line' && Array.isArray(el.geometry.start) && Array.isArray(el.geometry.end)) {
            const [x1, y1] = projectPoint(bounds, el.geometry.start[0] || 0, el.geometry.start[1] || 0)
            const [x2, y2] = projectPoint(bounds, el.geometry.end[0] || 0, el.geometry.end[1] || 0)
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            shapeNode = <line {...commonProps} x1={x1} y1={y1} x2={x2} y2={y2} />
          } else if (el.geometry?.kind === 'lwpolyline' && Array.isArray(el.geometry.points)) {
            const projected = el.geometry.points
              .filter(p => Array.isArray(p))
              .map((p) => projectPoint(bounds, p[0] || 0, p[1] || 0))
            const ptsStr = projected.map(p => p.join(',')).join(' ')
            if (projected.length > 0) {
              cx = projected.reduce((sum, p) => sum + p[0], 0) / projected.length
              cy = projected.reduce((sum, p) => sum + p[1], 0) / projected.length
            }
            shapeNode = el.geometry.closed
              ? <polygon {...commonProps} points={ptsStr} />
              : <polyline {...commonProps} points={ptsStr} />
          } else if ((el.geometry?.kind === 'text' || el.geometry?.kind === 'insert') && Array.isArray(el.geometry.position)) {
            const [px, py] = projectPoint(bounds, el.geometry.position[0] || 0, el.geometry.position[1] || 0)
            cx = px
            cy = py
            shapeNode = (
              <circle
                {...commonProps}
                cx={cx}
                cy={cy}
                r={Math.max(strokeWidth * 1.5, 3)}
                fill={commonProps.stroke}
              />
            )
          }

          if (!shapeNode) return null

          return (
            <g key={el.id}>
              {shapeNode}
              {labelText && (
                <g transform={`translate(${cx}, ${cy})`}>
                  <rect
                    x={-((labelText.length * 7) / 2 + 3)}
                    y="-8"
                    width={labelText.length * 7 + 6}
                    height="16"
                    rx="3"
                    fill="#18181b"
                    fillOpacity="0.85"
                    stroke={stroke}
                    strokeWidth="0.8"
                    pointerEvents="none"
                  />
                  <text
                    x="0"
                    y="1"
                    fill="#ffffff"
                    fontSize="9px"
                    fontWeight="bold"
                    fontFamily="monospace"
                    textAnchor="middle"
                    dominantBaseline="middle"
                    pointerEvents="none"
                  >
                    {labelText}
                  </text>
                </g>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
