#!/usr/bin/env python3
"""Map a converted DXF into the Phase 1 Drawing Object Model.

The mapper is deliberately conservative: it preserves raw geometry and source
metadata, assigns an element type from layer/label hints, and records a
confidence score so later review can override uncertain classifications.
"""
import argparse
import json
import re
from pathlib import Path

import ezdxf


TYPE_RULES = {
    "beam": ("beam", "girder", "beam line", "b-"),
    "column": ("column", "col", "column line", "c-"),
    "footing": ("footing", "fnd", "foundation", "f-"),
    "slab": ("slab", "floor", "roof"),
    "chb_wall": ("chb", "masonry", "wall"),
}
LABEL_RE = re.compile(r"\b(?:[A-Z]{1,4}[- ]?\d+[A-Z]?)\b", re.I)


def _text(entity):
    return str(entity.dxf.get("text", "")).strip()


def _point(entity):
    p = entity.dxf.get("insert") or entity.dxf.get("start")
    return [round(float(p[0]), 6), round(float(p[1]), 6)] if p else None


def _geometry(entity):
    kind = entity.dxftype()
    if kind == "LINE":
        s, e = entity.dxf.start, entity.dxf.end
        return {"kind": "line", "start": [s[0], s[1]], "end": [e[0], e[1]]}
    if kind == "LWPOLYLINE":
        return {"kind": "lwpolyline", "closed": bool(entity.closed),
                "points": [[p[0], p[1], p[2]] for p in entity.get_points("xyb")]}
    return {"kind": kind.lower(), "position": _point(entity)}


def _classify(layer, label):
    hay = f"{layer} {label}".lower()
    for element_type, hints in TYPE_RULES.items():
        if any(h in hay for h in hints):
            return element_type, 0.9 if label else 0.75
    return "other", 0.35


def map_dxf(path):
    doc = ezdxf.readfile(path)
    records = []
    for entity in doc.modelspace():
        kind = entity.dxftype()
        if kind not in {"LINE", "LWPOLYLINE", "TEXT", "MTEXT", "INSERT"}:
            continue
        layer = entity.dxf.get("layer", "0")
        raw = _text(entity) if kind in {"TEXT", "MTEXT"} else ""
        label_match = LABEL_RE.search(raw)
        label = label_match.group(0).upper() if label_match else raw[:120]
        element_type, confidence = _classify(layer, label)
        records.append({
            "element_type": element_type,
            "label": label or f"{kind}-{entity.dxf.get('handle', '')}",
            "geometry": _geometry(entity),
            "raw_source": {"handle": entity.dxf.get("handle"), "layer": layer,
                            "entity_type": kind, "text": raw},
            "confidence": confidence,
        })
    return {"source": str(Path(path).name), "format": "DXF", "elements": records,
            "element_count": len(records)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dxf")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()
    result = map_dxf(args.dxf)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Mapped {result['element_count']} entities to {args.output}")


if __name__ == "__main__":
    main()
