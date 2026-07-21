#!/usr/bin/env python3
"""
llm_layer_classifier.py

Task 1 — LLM Semantic Layer Classifier (agent: llm-classifier-agent)

Objective:
    Scan all layer names extracted from a DXF file and use an LLM to predict
    which layers contain beams or columns, even when layer naming conventions
    are inconsistent or non-standard. Returns a normalized classification
    mapping (JSON) that downstream steps (quantity extraction, schedule
    generation) can consume.

Usage:
    export ANTHROPIC_API_KEY=sk-...
    python llm_layer_classifier.py path/to/drawing.dxf -o classification.json

Dependencies:
    pip install ezdxf anthropic --break-system-packages

Design notes:
    - We don't just hand the LLM a bare list of layer name strings. Layer
      names in the wild are often abbreviated/cryptic (e.g. "S-BEAM-CONC",
      "STRUC_BM", "A-COL-GRID", "0"), so we enrich each layer with cheap
      structural signal pulled straight from the DXF: entity count, the
      geometric entity types present (LINE, LWPOLYLINE, etc.), and a couple
      of sample entity handles. This gives the LLM more to reason with than
      the name alone, without doing any real geometric analysis ourselves.
    - The LLM call asks for strict JSON back (no prose) so the mapping can be
      parsed reliably and fed straight into the next pipeline stage.
    - Classification is per-layer, not per-entity. Beam/column detection at
      the individual-entity level is a later pipeline step; here we're only
      answering "is this layer likely to contain beams / columns / neither".
"""

import argparse
import json
import sys
import os
from collections import Counter, defaultdict

try:
    import ezdxf
except ImportError:
    print("Missing dependency: pip install ezdxf --break-system-packages", file=sys.stderr)
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("Missing dependency: pip install anthropic --break-system-packages", file=sys.stderr)
    sys.exit(1)


MODEL = "claude-sonnet-4-6"

VALID_LABELS = {"beam", "column", "other"}

CLASSIFIER_SYSTEM_PROMPT = """You are a structural CAD layer classifier.

You will be given a JSON list of DXF layer summaries from a structural \
engineering drawing. Each summary includes the layer name and cheap \
signal extracted from the file (entity count, entity types present).

Layer naming conventions in real-world structural drawings are wildly \
inconsistent between firms, countries, and CAD standards. Do not rely \
only on the literal substring match against "beam" or "column" — use \
engineering judgement. For example:
  - "S-BEAM-CONC", "STRUC_BM", "FRAMING-BM", "BEAMS-STL" -> beam
  - "S-COL-GRID", "STRUC_CLMN", "COLUMNS-CONC" -> column
  - "0", "DEFPOINTS", "TEXT", "DIMENSIONS", "A-DOOR", "HATCH" -> other
  - Ambiguous/generic names like "STRUCTURAL" or "FRAMING" with mixed \
    entity types should get a lower confidence score rather than being \
    forced into beam or column.

For every layer in the input, return a classification with:
  - "layer": the exact original layer name (unchanged)
  - "label": one of "beam", "column", "other"
  - "confidence": float between 0 and 1
  - "reasoning": one short sentence (<20 words) explaining the call

Respond with ONLY a JSON array of these objects. No markdown fences, no \
prose before or after, no additional keys."""


def extract_layer_summaries(dxf_path: str) -> list[dict]:
    """Pull every layer name from a DXF plus lightweight structural signal.

    Returns a list of dicts, one per layer defined in the DXF, e.g.:
        {
            "layer": "S-BEAM-CONC",
            "entity_count": 142,
            "entity_types": {"LINE": 98, "LWPOLYLINE": 44},
            "sample_handles": ["2A3", "2A4"]
        }

    Layers with zero entities in modelspace (defined but unused) still get
    included with entity_count 0, since they may still matter downstream.
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    per_layer_types: dict[str, Counter] = defaultdict(Counter)
    per_layer_handles: dict[str, list] = defaultdict(list)

    for entity in msp:
        layer = entity.dxf.layer
        per_layer_types[layer][entity.dxftype()] += 1
        if len(per_layer_handles[layer]) < 3:
            per_layer_handles[layer].append(entity.dxf.handle)

    summaries = []
    for layer in doc.layers:
        name = layer.dxf.name
        types = per_layer_types.get(name, Counter())
        summaries.append({
            "layer": name,
            "entity_count": sum(types.values()),
            "entity_types": dict(types),
            "sample_handles": per_layer_handles.get(name, []),
        })
    return summaries


def classify_layers(summaries: list[dict], client: "anthropic.Anthropic") -> list[dict]:
    """Send layer summaries to the LLM and return the parsed classification list."""
    if not summaries:
        return []

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=CLASSIFIER_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": json.dumps(summaries, indent=2)}
        ],
    )

    raw_text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    # Defensive cleanup in case the model wraps output in a code fence anyway.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        classifications = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM did not return valid JSON. Raw response:\n{raw_text}"
        ) from e

    # Validate and normalize each entry so downstream steps can trust the shape.
    normalized = []
    input_layers = {s["layer"] for s in summaries}
    seen = set()
    for item in classifications:
        layer = item.get("layer")
        label = str(item.get("label", "")).lower().strip()
        confidence = item.get("confidence")

        if layer not in input_layers:
            continue  # skip hallucinated layer names
        if label not in VALID_LABELS:
            label = "other"
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = 0.0

        normalized.append({
            "layer": layer,
            "label": label,
            "confidence": round(confidence, 2),
            "reasoning": item.get("reasoning", ""),
        })
        seen.add(layer)

    # Any layer the LLM dropped gets a safe fallback entry instead of silently vanishing.
    for layer in input_layers - seen:
        normalized.append({
            "layer": layer,
            "label": "other",
            "confidence": 0.0,
            "reasoning": "No classification returned by LLM; defaulted to 'other'.",
        })

    return normalized


def main():
    parser = argparse.ArgumentParser(description="LLM-based DXF layer classifier (beam/column/other)")
    parser.add_argument("dxf_path", help="Path to input DXF file")
    parser.add_argument(
        "-o", "--output", default="layer_classification.json",
        help="Output path for the classification mapping JSON (default: layer_classification.json)"
    )
    args = parser.parse_args()

    if "ANTHROPIC_API_KEY" not in os.environ:
        for env_path in [os.path.join(os.path.expanduser("~"), ".env"), ".env"]:
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("ANTHROPIC_API_KEY="):
                            os.environ["ANTHROPIC_API_KEY"] = line.strip().split("=", 1)[1].strip("'\"")
                            break

    print(f"Reading DXF: {args.dxf_path}")
    summaries = extract_layer_summaries(args.dxf_path)
    print(f"Found {len(summaries)} layers. Classifying with {MODEL}...")

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    classification = classify_layers(summaries, client)

    beams = [c for c in classification if c["label"] == "beam"]
    columns = [c for c in classification if c["label"] == "column"]
    print(f"Classified: {len(beams)} beam layer(s), {len(columns)} column layer(s), "
          f"{len(classification) - len(beams) - len(columns)} other.")

    with open(args.output, "w") as f:
        json.dump(classification, f, indent=2)
    print(f"Wrote classification mapping to {args.output}")


if __name__ == "__main__":
    main()
