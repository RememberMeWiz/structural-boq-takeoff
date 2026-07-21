// The DOM (Drawing Object Model) stores raw drawing-unit coordinates, which can
// be arbitrary CAD survey coordinates (see the sample DXF: values in the
// hundreds of thousands). We compute a bounding box across all elements and
// derive a simple linear transform into SVG viewBox space, flipping Y since
// CAD coordinate systems are Y-up and SVG is Y-down.

export function collectPoints(geometry) {
  if (!geometry) return []
  switch (geometry.kind) {
    case 'line':
      return [geometry.start, geometry.end].filter(Boolean)
    case 'lwpolyline':
      return (geometry.points || []).map((p) => [p[0], p[1]])
    case 'insert':
    case 'text':
      return geometry.position ? [geometry.position] : []
    default:
      return []
  }
}

export function computeBounds(elements) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (const el of elements) {
    for (const [x, y] of collectPoints(el.geometry)) {
      if (x < minX) minX = x
      if (y < minY) minY = y
      if (x > maxX) maxX = x
      if (y > maxY) maxY = y
    }
  }
  if (!isFinite(minX)) return { minX: 0, minY: 0, maxX: 100, maxY: 100 }
  // pad by 3% of the larger dimension so edge elements aren't clipped
  const pad = Math.max(maxX - minX, maxY - minY) * 0.03 || 1
  return { minX: minX - pad, minY: minY - pad, maxX: maxX + pad, maxY: maxY + pad }
}

// Translate to origin, then flip Y (CAD is Y-up, SVG is Y-down).
export function projectPoint(bounds, x, y) {
  const w = bounds.maxX - bounds.minX
  const h = bounds.maxY - bounds.minY
  return [x - bounds.minX, h - (y - bounds.minY)]
}

export function boundsViewBox(bounds) {
  const w = bounds.maxX - bounds.minX
  const h = bounds.maxY - bounds.minY
  return `0 0 ${w} ${h}`
}
