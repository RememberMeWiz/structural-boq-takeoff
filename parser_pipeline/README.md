# Quantity Takeoff Aggregator (Task 2)
Agents: `dxf-geometry-engineer` (geometry engine) + `takeoff-report-developer` (report output)

Takes the classification output from Task 1 (`llm_layer_classifier.py`) and
the original DXF, computes total lengths/counts per beam/column layer, and
writes a takeoff schedule to CSV or Excel — with optional cost-per-length
hooks for a future cost database.

## Files
- `dxf_geometry_engine.py` — computes true lengths for `LINE` and
  `LWPOLYLINE` entities (including arc length on bulged polyline segments,
  not just straight chords), and aggregates them per classified layer.
- `takeoff_report_generator.py` — consumes the geometry engine + Task 1's
  classification JSON, applies optional cost-table lookups, and writes the
  final schedule (CSV always works; Excel if `openpyxl` is installed).

## 1. Install dependencies

```bash
pip install ezdxf openpyxl --break-system-packages
```
(`openpyxl` is only needed for `.xlsx` output — CSV works without it.)

## 2. Run Task 1 first (if you haven't)

```bash
python llm_layer_classifier.py drawing.dxf -o classification.json
```

## 3. Run the aggregator

```bash
python takeoff_report_generator.py drawing.dxf classification.json \
    -o takeoff_schedule.xlsx \
    --cost-table cost_table.json   # optional
```

**Arguments:**
| Arg | Required | Description |
|---|---|---|
| `dxf_path` | yes | Same DXF used for classification |
| `classification_path` | yes | Task 1's output JSON |
| `-o`, `--output` | no | `.csv` or `.xlsx` (default: `takeoff_schedule.csv`) |
| `--cost-table` | no | Optional JSON for unit-cost lookups (see below) |

## Cost table format (optional)

```json
{
  "default": {"beam": 12.50, "column": 18.75},
  "layers":  {"S-BEAM-CONC": 15.00}
}
```
- `default` = fallback unit cost by label (beam/column), applied per unit
  length in whatever units the drawing uses.
- `layers` = optional per-layer override (checked first).
- If you don't pass `--cost-table` at all, cost columns are simply left
  blank — the schedule is still fully usable for lengths and counts, and
  pricing can be added once real cost data is available. **No cost is ever
  guessed or defaulted silently.**

## Output columns

`layer, label, entity_count, total_length, unit_cost, total_cost`

Plus a `TOTAL (beam)` and `TOTAL (column)` grand-total row at the bottom.
The Excel version bolds the header row and total rows, and auto-sizes
columns.

## Units

The script reads the DXF's `$INSUNITS` header value and reports it (e.g.
`mm`, `ft`) both on the console and in the Excel column header. **If the
drawing has no units set (`Unitless`), a warning is printed** — verify
lengths manually against a known dimension before trusting the schedule,
since garbage-in-garbage-out applies to unit assumptions same as anywhere
else.

## Tested against

Verified with a synthetic DXF covering: a straight `LINE`, a straight
multi-segment `LWPOLYLINE`, and a bulged (arc) `LWPOLYLINE` segment — arc
length matched the analytically expected value to 14 decimal places.
**Not yet tested against a real/messy structural drawing** — that's still
the open blocker from the project roadmap. Run it against the first real
DXF sample as soon as one's available; messy real-world polylines
(self-intersecting, closed loops, mixed straight/arc segments) are the
actual stress test this hasn't had yet.
