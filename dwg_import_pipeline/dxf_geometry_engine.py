#!/usr/bin/env python3
"""
dxf_geometry_engine.py

Computes real-world lengths for LINE and LWPOLYLINE entities in a DXF file
using ezdxf, then aggregates lengths per layer. Used here as a post-conversion
sanity check: after ODA converts a DWG to DXF, we run this to confirm the
output is readable and report basic entity counts back to the user.
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field

import ezdxf


@dataclass
class EntityLength:
    handle: str
    layer: str
    entity_type: str
    length: float


@dataclass
class LayerAggregate:
    layer: str
    label: str
    entity_count: int = 0
    total_length: float = 0.0
    entity_handles: list = field(default_factory=list)


def _segment_length(p1, p2, bulge: float) -> float:
    chord = math.dist((p1[0], p1[1]), (p2[0], p2[1]))
    if not bulge:
        return chord
    theta = 4 * math.atan(bulge)
    if theta == 0:
        return chord
    radius = abs(chord / (2 * math.sin(theta / 2)))
    return radius * abs(theta)


def line_length(entity) -> float:
    start = entity.dxf.start
    end = entity.dxf.end
    return math.dist((start[0], start[1]), (end[0], end[1]))


def lwpolyline_length(entity) -> float:
    points = list(entity.get_points("xyb"))
    if len(points) < 2:
        return 0.0
    total = 0.0
    n = len(points)
    is_closed = entity.closed
    segment_count = n if is_closed else n - 1
    for i in range(segment_count):
        x1, y1, bulge = points[i]
        x2, y2, _ = points[(i + 1) % n]
        total += _segment_length((x1, y1), (x2, y2), bulge)
    return total


def entity_length(entity) -> float:
    dxftype = entity.dxftype()
    if dxftype == "LINE":
        return line_length(entity)
    if dxftype == "LWPOLYLINE":
        return lwpolyline_length(entity)
    return 0.0


def compute_entity_lengths(dxf_path: str) -> list[EntityLength]:
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    results = []
    for entity in msp:
        dxftype = entity.dxftype()
        if dxftype not in ("LINE", "LWPOLYLINE"):
            continue
        length = entity_length(entity)
        results.append(EntityLength(
            handle=entity.dxf.handle,
            layer=entity.dxf.layer,
            entity_type=dxftype,
            length=length,
        ))
    return results


def get_drawing_units(dxf_path: str) -> str:
    doc = ezdxf.readfile(dxf_path)
    insunits = doc.header.get("$INSUNITS", 0)
    return ezdxf.units.decode(insunits) if insunits else "Unitless"


def summarize_drawing(dxf_path: str) -> dict:
    """High-level summary used by the import pipeline to report back to the
    user what was found in a converted/uploaded drawing."""
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    counts = defaultdict(int)
    layers = set()
    for entity in msp:
        counts[entity.dxftype()] += 1
        layers.add(entity.dxf.layer)
    return {
        "entity_counts": dict(counts),
        "layer_count": len(layers),
        "layers": sorted(layers),
        "units": get_drawing_units(dxf_path),
        "total_entities": sum(counts.values()),
    }
