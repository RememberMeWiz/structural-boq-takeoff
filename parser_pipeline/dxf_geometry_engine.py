#!/usr/bin/env python3
"""
dxf_geometry_engine.py

Task 2 (part 1) — agent: dxf-geometry-engineer

Objective:
    Compute real-world lengths for LINE and LWPOLYLINE entities in a DXF
    file, then aggregate those lengths per layer. This module is pure
    geometry/aggregation logic with no report formatting — it's consumed
    by takeoff_report_generator.py (agent: takeoff-report-developer),
    which turns the aggregation into the actual Excel/CSV deliverable.

Why LWPOLYLINE needs special handling:
    A polyline segment isn't always a straight line — DXF vertices carry a
    "bulge" value that encodes a circular arc between that vertex and the
    next one (bulge = tan(included_angle / 4)). Structural framing plans
    do sometimes use curved/haunched members or arced bracing, so treating
    every polyline segment as a straight chord would quietly undercount
    length on any curved run. This module computes true arc length for
    bulged segments instead of just chord distance.
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
    """Length of one polyline segment from p1 to p2, accounting for bulge.

    If bulge is 0, it's a straight segment (Euclidean distance).
    If bulge != 0, the segment is a circular arc; bulge = tan(theta/4)
    where theta is the included angle, so:
        theta = 4 * atan(bulge)
        chord  = distance(p1, p2)
        radius = chord / (2 * sin(theta/2))
        arc_length = radius * theta
    """
    chord = math.dist((p1[0], p1[1]), (p2[0], p2[1]))

    if not bulge:
        return chord

    theta = 4 * math.atan(bulge)
    if theta == 0:
        return chord

    # radius can be derived directly without re-deriving chord/2 explicitly
    radius = abs(chord / (2 * math.sin(theta / 2)))
    return radius * abs(theta)


def line_length(entity) -> float:
    """Length of a LINE entity (straight-line 3D distance, projected length
    is fine for takeoff purposes since structural plans are drawn to scale
    in a single plane)."""
    start = entity.dxf.start
    end = entity.dxf.end
    return math.dist((start[0], start[1]), (end[0], end[1]))


def lwpolyline_length(entity) -> float:
    """Total length of an LWPOLYLINE, summing straight and bulged segments.

    Uses get_points('xyb') to retrieve (x, y, bulge) per vertex, correctly
    handling both open and closed polylines.
    """
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
    """Dispatch to the right length calculation based on DXF entity type.
    Returns 0.0 for unsupported types rather than raising, so a single
    unexpected entity doesn't take down a whole-drawing aggregation run."""
    dxftype = entity.dxftype()
    if dxftype == "LINE":
        return line_length(entity)
    if dxftype == "LWPOLYLINE":
        return lwpolyline_length(entity)
    return 0.0


def compute_entity_lengths(dxf_path: str) -> list[EntityLength]:
    """Walk modelspace and return per-entity length records for every
    LINE/LWPOLYLINE entity in the drawing (all layers, unfiltered — layer
    filtering by classification happens in aggregate_by_layer)."""
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
    """Return a human-readable unit name from the DXF header ($INSUNITS),
    e.g. 'Millimeters', 'Feet', 'Unitless'. Downstream cost/report code
    should treat 'Unitless' as a flag to confirm units manually — plenty
    of real-world drawings don't set $INSUNITS correctly."""
    doc = ezdxf.readfile(dxf_path)
    insunits = doc.header.get("$INSUNITS", 0)
    return ezdxf.units.decode(insunits) if insunits else "Unitless"


def aggregate_by_layer(
    entity_lengths: list[EntityLength],
    classification: dict[str, dict],
) -> list[LayerAggregate]:
    """Roll up entity-level lengths into per-layer totals, restricted to
    layers the classifier labeled 'beam' or 'column' (i.e. skip 'other').

    Args:
        entity_lengths: output of compute_entity_lengths()
        classification: mapping of layer name -> classification dict, e.g.
            {"S-BEAM-CONC": {"label": "beam", "confidence": 0.93, ...}}
            (this is just the Task 1 classification list re-keyed by layer)

    Returns:
        One LayerAggregate per relevant layer, sorted by label then layer
        name for stable, readable report ordering.
    """
    aggregates: dict[str, LayerAggregate] = {}

    for record in entity_lengths:
        layer_info = classification.get(record.layer)
        if not layer_info:
            continue
        label = layer_info.get("label", "other")
        if label not in ("beam", "column"):
            continue

        if record.layer not in aggregates:
            aggregates[record.layer] = LayerAggregate(layer=record.layer, label=label)

        agg = aggregates[record.layer]
        agg.entity_count += 1
        agg.total_length += record.length
        agg.entity_handles.append(record.handle)

    return sorted(aggregates.values(), key=lambda a: (a.label, a.layer))


def classification_list_to_map(classification_list: list[dict]) -> dict[str, dict]:
    """Convenience helper: convert the JSON array produced by
    llm_layer_classifier.py (Task 1) into a layer-name-keyed dict for
    aggregate_by_layer()."""
    return {item["layer"]: item for item in classification_list}
