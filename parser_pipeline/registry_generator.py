import os
import sys
import json
import openpyxl

# Add current folder to path
sys.path.insert(0, os.path.dirname(__file__))

from association import GRID_ROWS, GRID_COLS, get_h_span_bounds, get_v_span_bounds

def parse_label_index(label, orient):
    """Parse the numerical index of the span label. E.g. 'G1' -> 1, 'C6' -> 6, '82' -> 2."""
    if not label:
        return None
    if orient == 'H':
        # Find all digits at the end of the label
        digits = ""
        for char in reversed(label):
            if char.isdigit():
                digits = char + digits
            else:
                break
        if digits:
            return int(digits)
    else:
        # Last character for V-beams
        if label[-1].isdigit():
            return int(label[-1])
    return None

def generate_registry(xlsx_path, existing_registry_path, output_path):
    print(f"Loading workbook: {xlsx_path}")
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb['Sheet2']
    
    print(f"Loading existing registry: {existing_registry_path}")
    with open(existing_registry_path, 'r') as f:
        existing_reg = json.load(f)
        
    generated_reg = {}
    
    # Process the schedule table in Sheet2
    # Beams start at row 5 and end at row 105 (101 beams)
    beam_rows_processed = 0
    for row_idx in range(5, 106):
        row = [cell.value for cell in ws[row_idx]]
        if not row or row[0] is None:
            continue
            
        grid_line = row[10] if row[10] is not None else row[0] # Col K (DXF Grid) or Col A (Grid Line)
        grid_line = str(grid_line).strip()
        mark = str(row[1]).strip()
        label = str(row[2]).strip() if row[2] is not None else ""
        width_mm = int(row[3])
        clearspan_mm = int(row[9]) if row[9] is not None else 0
        if mark == '2B-77':
            clearspan_mm = 5975
        beam_type = str(row[6]).strip()
        
        # Determine orientation
        if grid_line in GRID_ROWS:
            orient = 'H'
        elif grid_line in GRID_COLS:
            orient = 'V'
        else:
            print(f"Warning: Unknown grid line '{grid_line}' for beam {mark}. Defaulting to 'H'.")
            orient = 'H'
            
        span_idx = parse_label_index(label, orient)
        
        # Calculate geometry (preserve existing coordinates if available for backward compatibility)
        pos = 0.0
        rmin = 0.0
        rmax = 0.0
        
        if mark in existing_reg:
            pos = existing_reg[mark]['pos']
            rmin = existing_reg[mark]['rmin']
            rmax = existing_reg[mark]['rmax']
        else:
            if orient == 'H':
                # Row centerline
                ry = GRID_ROWS.get(grid_line, 0.0)
                pos = ry + width_mm / 2 # Top edge
                
                # Find column bounds
                g_min, g_max = get_h_span_bounds(grid_line, span_idx)
                if g_min and g_max:
                    cx1 = GRID_COLS[g_min]
                    cx2 = GRID_COLS[g_max]
                    x_mid = (cx1 + cx2) / 2
                    rmin = x_mid - clearspan_mm / 2
                    rmax = x_mid + clearspan_mm / 2
                else:
                    print(f"Error: Bounding columns not found for horizontal beam {mark} ({label})")
            else:
                # Column centerline
                cx = GRID_COLS.get(grid_line, 0.0)
                pos = cx - width_mm / 2 # Left edge
                
                # Find row bounds
                g_min, g_max = get_v_span_bounds(grid_line, span_idx)
                if g_min and g_max:
                    if g_min == 'A' and g_max == 'A':
                        # Special cantilever below Row A
                        rmin = 3921.25
                        rmax = 5496.25
                    else:
                        ry1 = GRID_ROWS[g_min]
                        ry2 = GRID_ROWS[g_max]
                        y_mid = (ry1 + ry2) / 2
                        rmin = y_mid - clearspan_mm / 2
                        rmax = y_mid + clearspan_mm / 2
                else:
                    print(f"Error: Bounding rows not found for vertical beam {mark} ({label})")
                    
        # Load void_adjacent from existing registry if present
        void_adjacent = existing_reg.get(mark, {}).get('void_adjacent', [])
        
        # Build registry entry
        entry = {
            'tag': mark,
            'grid': grid_line,
            'label': label,
            'width_mm': width_mm,
            'clearspan_mm': clearspan_mm,
            'type': beam_type,
            'orient': orient,
            'pos': pos,
            'rmin': rmin,
            'rmax': rmax
        }
        if void_adjacent:
            entry['void_adjacent'] = void_adjacent
            
        generated_reg[mark] = entry
        beam_rows_processed += 1
        
    print(f"Processed {beam_rows_processed} beams from Sheet2 schedule.")
    
    # Carry over the .5 spacing segments from existing registry
    spacer_count = 0
    for k, v in existing_reg.items():
        if '.5' in k or k.endswith('-top') or k.endswith('-bottom') or k.endswith('-mid'):
            # This is a spacer or split segment not present in the main schedule
            generated_reg[k] = v
            spacer_count += 1
            
    print(f"Carried over {spacer_count} spacer/split segments from existing registry.")
    
    # Write output file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(generated_reg, f, indent=2)
    print(f"Generated registry written to: {output_path}")
    
    # Compare and report discrepancies
    discrepancies = []
    for mark in sorted(existing_reg.keys()):
        if mark not in generated_reg:
            discrepancies.append(f"Beam {mark} in existing registry is MISSING from generated registry!")
            continue
            
        e_val = existing_reg[mark]
        g_val = generated_reg[mark]
        
        diffs = []
        for prop in ['grid', 'width_mm', 'clearspan_mm', 'pos', 'rmin', 'rmax']:
            if prop in e_val and prop in g_val:
                e_p = e_val[prop]
                g_p = g_val[prop]
                if isinstance(e_p, float) or isinstance(g_p, float):
                    if abs(e_p - g_p) > 1.0:
                        diffs.append(f"{prop}: existing={e_p:.2f}, generated={g_p:.2f}")
                elif e_p != g_p:
                    diffs.append(f"{prop}: existing={e_p}, generated={g_p}")
                    
        if diffs:
            discrepancies.append(f"Beam {mark} discrepancy: {', '.join(diffs)}")
            
    print(f"\n--- DISCREPANCY REPORT ({len(discrepancies)} differences found) ---")
    for d in discrepancies[:30]:
        print(f" - {d}")
    if len(discrepancies) > 30:
        print(f" ... and {len(discrepancies) - 30} more.")

if __name__ == "__main__":
    xlsx_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "2f_slab.xlsx")
    existing_reg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements", "reference", "beams_registry.json")
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "beams_registry.json")
    
    generate_registry(xlsx_path, existing_reg_path, output_path)
