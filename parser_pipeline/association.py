import os
import sys

# Canonical grid row y-coordinates (centers)
GRID_ROWS = {
    'G': 43871.25, 'N': 40704.25, 'M': 37371.25, 'F': 34371.25, 'E': 31371.25,
    'K': 28171.25, 'D': 24871.25, 'C': 21871.25, 'W': 23296.25, 'Y': 23296.25,
    'O': 20196.25, 'J': 18571.25, 'B': 15371.25, 'I': 12204.25, 'P': 11696.25,
    'H': 9038.25, 'A': 5871.25
}

# Canonical grid column x-coordinates (centers)
GRID_COLS = {
    '1': 10469.76, 'V': 11969.76, '2': 19969.76, '8': 26469.76, '4': 29469.76,
    '9': 32469.76, '6': 38969.76, 'X': 46969.76, '7': 48469.76
}

# Span boundaries mapping for horizontal beams based on their span label index
# Each row's beam spans are bounded by specific columns
def get_h_span_bounds(row, span_idx):
    if row in ('G', 'N', 'M', 'H', 'A'):
        cols = ['1', '2', '8', '9', '6', '7']
        if 1 <= span_idx <= 5:
            return cols[span_idx - 1], cols[span_idx]
    elif row in ('F', 'E'):
        cols = ['1', '2', '8', '4', '9', '6', '7']
        if 1 <= span_idx <= 6:
            return cols[span_idx - 1], cols[span_idx]
    elif row in ('K', 'D', 'J', 'B', 'I'):
        # Note: void gap exists between 8 and 9, so span index 3 corresponds to grids 9-6
        if span_idx == 1:
            return '1', '2'
        elif span_idx == 2:
            return '2', '8'
        elif span_idx == 3:
            return '9', '6'
        elif span_idx == 4:
            return '6', '7'
    elif row == 'C':
        # Labels are C6..C10 corresponding to spans 1..5
        idx = span_idx - 5
        cols = ['1', '2', '8', '9', '6', '7']
        if 1 <= idx <= 5:
            return cols[idx - 1], cols[idx]
    elif row == 'W' and span_idx == 1:
        return 'V', '2'
    elif row == 'Y' and span_idx == 1:
        return '6', 'X'
    elif row == 'O' and span_idx == 1:
        return '8', '9'
    elif row == 'P' and span_idx == 1:
        return '8', '9'
    
    return None, None

# Span boundaries mapping for vertical beams based on their label index
def get_v_span_bounds(col, label_idx):
    if col == '1':
        rows = ['A', 'B', 'C', 'D', 'F', 'G']
        if 1 <= label_idx <= 5:
            return rows[label_idx - 1], rows[label_idx]
    elif col == 'V' and label_idx == 1:
        return 'C', 'D'
    elif col == '2':
        # Spans 21..25
        rows_map = {1: ('H', 'I'), 2: ('J', 'C'), 3: ('C', 'D'), 4: ('K', 'E'), 5: ('M', 'G')}
        return rows_map.get(label_idx)
    elif col == '8':
        # Spans 81..86
        # Note: 81 is a bottom cantilever bounded by A-A
        rows_map = {1: ('A', 'A'), 2: ('H', 'I'), 3: ('J', 'C'), 4: ('D', 'K'), 5: ('E', 'F'), 6: ('M', 'N')}
        return rows_map.get(label_idx)
    elif col == '4' and label_idx == 1:
        return 'E', 'F'
    elif col == '9':
        # Spans 91..96
        # 91 is a bottom cantilever A-A
        rows_map = {1: ('A', 'A'), 2: ('H', 'P'), 3: ('B', 'O'), 4: ('C', 'E'), 5: ('E', 'F'), 6: ('M', 'N')}
        return rows_map.get(label_idx)
    elif col == '6':
        # Spans 61..65
        rows_map = {1: ('H', 'I'), 2: ('J', 'C'), 3: ('C', 'D'), 4: ('K', 'E'), 5: ('M', 'N')}
        return rows_map.get(label_idx)
    elif col == 'X' and label_idx == 1:
        return 'C', 'D'
    elif col == '7':
        # Spans 71..75
        rows_map = {1: ('H', 'I'), 2: ('J', 'C'), 3: ('C', 'D'), 4: ('K', 'E'), 5: ('M', 'N')}
        return rows_map.get(label_idx)
    
    return None, None
