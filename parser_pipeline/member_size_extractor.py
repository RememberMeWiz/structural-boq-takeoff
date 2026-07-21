"""Extract member tags/sizes from structural DXF annotations.

The drawings used by this project are not perfectly consistent: some labels
contain both a tag and a size (``1B137 350x750``), while other drawings put
the tag on ``Beam Label``/``Column Label`` and the size text on layer ``0``.
This module handles both forms and keeps the geometry association explicit in
the output so unresolved or ambiguous matches can be reviewed.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

try:
    import ezdxf
except ModuleNotFoundError:  # The project also ships a pure-Python DXF parser.
    ezdxf = None


SIZE_RE = re.compile(
    r"(?P<width>\d+(?:\.\d+)?)\s*[x×X]\s*(?P<depth>\d+(?:\.\d+)?)"
)

# Covers common structural tags: 2B-1, GB-12, C-28, 1B137, and 2C61.
TAG_RE = re.compile(
    r"(?<![A-Z0-9])(?:\d{1,3}\s*[A-Z]{1,4}\s*[-_]?\s*\d+(?:\.\d+)?|"
    r"[A-Z]{1,4}\s*[-_]?\s*\d+(?:\.\d+)?)(?![A-Z0-9])",
    re.IGNORECASE,
)


@dataclass
class TextRecord:
    handle: str
    layer: str
    text: str
    x: float
    y: float


@dataclass
class GeometryRecord:
    handle: str
    layer: str
    entity_type: str
    p1: tuple[float, float]
    p2: tuple[float, float]
    length: float


def clean_text(value: str | None) -> str:
    """Remove the most common MTEXT formatting escapes."""
    if not value:
        return ""
    value = re.sub(r"\\[Pp]", " ", value)
    value = re.sub(r"\\[A-Za-z][^;]*;", "", value)
    value = value.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", value).strip()


def parse_size(text: str) -> Optional[dict]:
    match = SIZE_RE.search(clean_text(text))
    if not match:
        return None
    return {
        "size_text": match.group(0).replace(" ", ""),
        "width_mm": float(match.group("width")),
        "depth_mm": float(match.group("depth")),
    }


def parse_tag(text: str, member_type: str) -> Optional[str]:
    """Return the first structural tag, excluding dimension components."""
    text_without_sizes = SIZE_RE.sub(" ", clean_text(text))
    matches = [m.group(0) for m in TAG_RE.finditer(text_without_sizes)]
    if not matches:
        return None
    tag = re.sub(r"\s+", "", matches[0]).replace("_", "-").upper()
    if member_type == "column" and re.fullmatch(r"\d+C\d+", tag):
        return tag
    return tag


def _text_value(entity) -> str:
    if entity.dxftype() == "MTEXT":
        return entity.text
    return entity.dxf.text


def _ascii_entities(path: str | Path) -> list[list[tuple[int, str]]]:
    """Read the ENTITIES section without ezdxf.

    This fallback intentionally mirrors the existing project's parser so the
    extractor remains usable in the bundled runtime, where ezdxf may not be
    installed.
    """
    with open(path, "r", errors="ignore") as stream:
        lines = [line.rstrip("\r\n") for line in stream]
    pairs = []
    for index in range(0, len(lines) - 1, 2):
        try:
            pairs.append((int(lines[index].strip()), lines[index + 1]))
        except ValueError:
            continue
    start = next((i for i, pair in enumerate(pairs) if pair == (2, "ENTITIES")), None)
    if start is None:
        return []
    end = next((i for i in range(start + 1, len(pairs)) if pairs[i] == (0, "ENDSEC")), len(pairs))
    entities = []
    current = None
    for pair in pairs[start:end]:
        if pair[0] == 0:
            if current is not None:
                entities.append(current)
            current = [pair]
        elif current is not None:
            current.append(pair)
    if current is not None:
        entities.append(current)
    return entities


def _ascii_field(entity, code: int, default=None):
    return next((value for c, value in entity if c == code), default)


def _ascii_layer(entity) -> str:
    return _ascii_field(entity, 8)


def _ascii_point(entity, xcode: int, ycode: int):
    x, y = _ascii_field(entity, xcode), _ascii_field(entity, ycode)
    return (float(x), float(y)) if x is not None and y is not None else None


def extract_text(doc, layers: Optional[set[str]] = None) -> list[TextRecord]:
    records: list[TextRecord] = []
    entities = doc.modelspace() if ezdxf is not None and hasattr(doc, "modelspace") else doc
    for entity in entities:
        if ezdxf is None or isinstance(entity, list):
            entity_type = entity[0][1]
            if entity_type not in {"TEXT", "MTEXT"}:
                continue
            layer = _ascii_layer(entity)
            if layers is not None and layer not in layers:
                continue
            point = _ascii_point(entity, 10, 20)
            if point is None:
                continue
            records.append(TextRecord(
                handle=str(_ascii_field(entity, 5, "")), layer=layer,
                text=clean_text(_ascii_field(entity, 1, "")), x=point[0], y=point[1]
            ))
            continue
        if entity.dxftype() not in {"TEXT", "MTEXT"}:
            continue
        layer = entity.dxf.layer
        if layers is not None and layer not in layers:
            continue
        insert = entity.dxf.insert
        records.append(TextRecord(
            handle=str(entity.dxf.handle),
            layer=layer,
            text=clean_text(_text_value(entity)),
            x=float(insert.x),
            y=float(insert.y),
        ))
    return records


def _distance_point_segment(point: tuple[float, float], p1, p2) -> float:
    px, py = point
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    denom = dx * dx + dy * dy
    if denom == 0:
        return math.dist(point, p1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / denom))
    return math.dist(point, (x1 + t * dx, y1 + t * dy))


def _polyline_segments(entity) -> Iterable[tuple[tuple[float, float], tuple[float, float]]]:
    if entity.dxftype() == "LINE":
        yield (float(entity.dxf.start.x), float(entity.dxf.start.y)), (
            float(entity.dxf.end.x), float(entity.dxf.end.y)
        )
        return
    if entity.dxftype() == "LWPOLYLINE":
        points = list(entity.get_points("xy"))
        for a, b in zip(points, points[1:]):
            yield (float(a[0]), float(a[1])), (float(b[0]), float(b[1]))
        if entity.closed and len(points) > 2:
            yield (float(points[-1][0]), float(points[-1][1])), (
                float(points[0][0]), float(points[0][1])
            )


def extract_geometry(doc, layer: str) -> list[GeometryRecord]:
    records: list[GeometryRecord] = []
    entities = doc.modelspace() if ezdxf is not None and hasattr(doc, "modelspace") else doc
    for entity in entities:
        if ezdxf is None or isinstance(entity, list):
            entity_type = entity[0][1]
            if entity_type not in {"LINE", "LWPOLYLINE"} or _ascii_layer(entity) != layer:
                continue
            points = []
            if entity_type == "LINE":
                p1, p2 = _ascii_point(entity, 10, 20), _ascii_point(entity, 11, 21)
                points = [(p1, p2)] if p1 and p2 else []
            else:
                current_x = None
                vertices = []
                for code, value in entity:
                    if code == 10:
                        current_x = float(value)
                    elif code == 20 and current_x is not None:
                        vertices.append((current_x, float(value)))
                points = list(zip(vertices, vertices[1:]))
            for index, (p1, p2) in enumerate(points):
                records.append(GeometryRecord(
                    handle=f"{_ascii_field(entity, 5, '')}:{index}" if len(points) > 1 else str(_ascii_field(entity, 5, "")),
                    layer=layer, entity_type=entity_type, p1=p1, p2=p2, length=math.dist(p1, p2)
                ))
            continue
        if entity.dxftype() not in {"LINE", "LWPOLYLINE"} or entity.dxf.layer != layer:
            continue
        segments = list(_polyline_segments(entity))
        for index, (p1, p2) in enumerate(segments):
            records.append(GeometryRecord(
                handle=f"{entity.dxf.handle}:{index}" if len(segments) > 1 else str(entity.dxf.handle),
                layer=layer,
                entity_type=entity.dxftype(),
                p1=p1,
                p2=p2,
                length=math.dist(p1, p2),
            ))
    return records


def nearest(point: tuple[float, float], records: list, max_distance: float | None = None):
    if not records:
        return None, None
    ranked = sorted(
        ((_distance_point_segment(point, r.p1, r.p2), r) for r in records),
        key=lambda item: item[0],
    )
    distance, record = ranked[0]
    if max_distance is not None and distance > max_distance:
        return None, distance
    return record, distance


def extract_members(
    dxf_path: str | Path,
    *,
    beam_label_layer: str = "Beam Label",
    column_label_layer: str = "Column Label",
    beam_geometry_layer: str = "Beam Line",
    column_geometry_layer: str = "Column Line",
    dimension_layers: Optional[set[str]] = None,
    max_geometry_distance: float = 1500.0,
    max_dimension_distance: float = 1500.0,
) -> dict:
    doc = ezdxf.readfile(str(dxf_path)) if ezdxf is not None else _ascii_entities(dxf_path)
    label_layers = {beam_label_layer, column_label_layer}
    labels = extract_text(doc, label_layers)
    dimensions = [t for t in extract_text(doc, dimension_layers) if parse_size(t.text)] if dimension_layers is not None else [
        t for t in extract_text(doc) if parse_size(t.text)
    ]
    geometry = {
        "beam": extract_geometry(doc, beam_geometry_layer),
        "column": extract_geometry(doc, column_geometry_layer),
    }

    members = []
    for label in labels:
        member_type = "beam" if label.layer == beam_label_layer else "column"
        tag = parse_tag(label.text, member_type)
        if not tag:
            continue
        geometry_record, geometry_distance = nearest(
            (label.x, label.y), geometry[member_type], max_geometry_distance
        )
        direct_size = parse_size(label.text)
        size = direct_size
        dimension_record = None
        dimension_distance = None
        dimension_geometry_handle = None
        dimension_source = "label" if direct_size else None

        # The VCNGC drawing places many dimension strings on layer 0 rather
        # than on the label layer. Prefer a dimension near the label, and use
        # geometry proximity as a tie-breaker through the label's link.
        if size is None:
            candidates = []
            for dimension in dimensions:
                distance = math.dist((label.x, label.y), (dimension.x, dimension.y))
                if distance <= max_dimension_distance:
                    candidate_geometry, candidate_geometry_distance = nearest(
                        (dimension.x, dimension.y), geometry[member_type], max_geometry_distance
                    )
                    same_geometry = bool(
                        geometry_record and candidate_geometry and
                        candidate_geometry.handle == geometry_record.handle
                    )
                    candidates.append((
                        0 if same_geometry else 1, distance, dimension,
                        candidate_geometry_distance,
                        candidate_geometry.handle if candidate_geometry else None,
                    ))
            if candidates:
                _, dimension_distance, dimension_record, _, dimension_geometry_handle = min(
                    candidates, key=lambda item: (item[0], item[1])
                )
                size = parse_size(dimension_record.text)
                dimension_source = f"text:{dimension_record.layer}"

        strong_indirect_match = bool(
            size and geometry_record and not direct_size and
            dimension_geometry_handle == geometry_record.handle and
            dimension_distance is not None and dimension_distance <= 500 and
            geometry_distance is not None and geometry_distance <= 500
        )
        status = (
            "matched" if size and geometry_record and (direct_size or strong_indirect_match)
            else "review" if size and geometry_record
            else "size_unresolved" if geometry_record
            else "geometry_unresolved"
        )

        record = {
            "member_type": member_type,
            "tag": tag,
            "raw_label": label.text,
            "label_handle": label.handle,
            "label_x": label.x,
            "label_y": label.y,
            "geometry_handle": geometry_record.handle if geometry_record else None,
            "geometry_layer": geometry_record.layer if geometry_record else None,
            "geometry_type": geometry_record.entity_type if geometry_record else None,
            "geometry_length": geometry_record.length if geometry_record else None,
            "geometry_distance": geometry_distance,
            "dimension_handle": dimension_record.handle if dimension_record else None,
            "dimension_raw_text": dimension_record.text if dimension_record else None,
            "dimension_distance": dimension_distance,
            "dimension_geometry_handle": dimension_geometry_handle,
            "dimension_source": dimension_source,
            "status": status,
        }
        record.update(size or {"size_text": None, "width_mm": None, "depth_mm": None})
        members.append(record)

    matched = [m for m in members if m["status"] == "matched"]
    schedule_map = {}
    for member in members:
        key = (member["member_type"], member["tag"])
        row = schedule_map.setdefault(key, {
            "member_type": member["member_type"],
            "tag": member["tag"],
            "occurrence_count": 0,
            "matched_occurrence_count": 0,
            "size_variants": [],
            "geometry_handles": [],
        })
        row["occurrence_count"] += 1
        if member["status"] == "matched":
            row["matched_occurrence_count"] += 1
        if member["size_text"] and member["size_text"] not in row["size_variants"]:
            row["size_variants"].append(member["size_text"])
        if member["geometry_handle"] and member["geometry_handle"] not in row["geometry_handles"]:
            row["geometry_handles"].append(member["geometry_handle"])
    schedule = sorted(schedule_map.values(), key=lambda row: (row["member_type"], row["tag"]))
    return {
        "schema_version": "task3.member_sizes.v1",
        "source_dxf": str(dxf_path),
        "configuration": {
            "beam_label_layer": beam_label_layer,
            "column_label_layer": column_label_layer,
            "beam_geometry_layer": beam_geometry_layer,
            "column_geometry_layer": column_geometry_layer,
            "dimension_layers": sorted(dimension_layers) if dimension_layers is not None else "all_text_layers",
            "max_geometry_distance": max_geometry_distance,
            "max_dimension_distance": max_dimension_distance,
        },
        "summary": {
            "label_count": len(members),
            "matched_count": len(matched),
            "size_unresolved_count": sum(m["status"] == "size_unresolved" for m in members),
            "review_count": sum(m["status"] == "review" for m in members),
            "geometry_unresolved_count": sum(m["status"] == "geometry_unresolved" for m in members),
            "beam_geometry_count": len(geometry["beam"]),
            "column_geometry_count": len(geometry["column"]),
            "unique_tags": len({(m["member_type"], m["tag"]) for m in members}),
            "schedule_row_count": len(schedule),
        },
        "schedule": schedule,
        "members": members,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dxf")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--beam-label-layer", default="Beam Label")
    parser.add_argument("--column-label-layer", default="Column Label")
    parser.add_argument("--beam-geometry-layer", default="Beam Line")
    parser.add_argument("--column-geometry-layer", default="Column Line")
    parser.add_argument("--dimension-layer", action="append", dest="dimension_layers")
    args = parser.parse_args()
    result = extract_members(
        args.dxf,
        beam_label_layer=args.beam_label_layer,
        column_label_layer=args.column_label_layer,
        beam_geometry_layer=args.beam_geometry_layer,
        column_geometry_layer=args.column_geometry_layer,
        dimension_layers=set(args.dimension_layers) if args.dimension_layers else None
    )
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
