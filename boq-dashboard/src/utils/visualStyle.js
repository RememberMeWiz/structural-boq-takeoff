export const ELEMENT_TYPE_COLORS = {
  footing: '#6fa8c9',
  column: '#e0b04c',
  beam: '#c97a5a',
  slab: '#8fb88a',
  chb_wall: '#a9772f',
  other: '#5b6b7a'
}

export const ELEMENT_TYPE_LABELS = {
  footing: 'Footing',
  column: 'Column',
  beam: 'Beam',
  slab: 'Slab',
  chb_wall: 'CHB Wall',
  other: 'Unclassified'
}

export function confidenceColor(confidence) {
  if (confidence >= 0.75) return '#3f8a5c' // high
  if (confidence >= 0.5) return '#d9a441'  // mid
  return '#c4501f'                          // low, needs review
}

export function confidenceLabel(confidence) {
  if (confidence >= 0.75) return 'High confidence'
  if (confidence >= 0.5) return 'Medium confidence'
  return 'Needs review'
}
