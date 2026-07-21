"""
Database Seeder Script for Supabase BOQ Review Dashboard
Populates PostgreSQL / Supabase tables:
- projects
- drawings
- drawing_elements (DOM)
- backup_computations
- boq_checklist
- base_prices
"""

import json
import urllib.request
import urllib.parse
from parser_pipeline.fajardo_takeoff_engine import FajardoTakeoffEngine, TakeoffElement

REST_BASE = "https://ickbqcdbyheyqyqfjpzv.supabase.co/rest/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlja2JxY2RieWhleXF5cWZqcHp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ0ODE1MzYsImV4cCI6MjEwMDA1NzUzNn0.aEmdkA2FXDZ19L-n2NcD4r3TkzZHexyYKni2pGqAO40"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "apikey": TOKEN,
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}


def http_post(endpoint: str, payload: list | dict):
    url = f"{REST_BASE}/{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=HEADERS,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"HTTPError on {endpoint}: {e.code} - {err_msg}")
        return None


def http_get(endpoint: str, query: str = ""):
    url = f"{REST_BASE}/{endpoint}?{query}" if query else f"{REST_BASE}/{endpoint}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"HttpGet error on {endpoint}: {e}")
        return []


def seed_database():
    print("1. Seeding Project record...")
    existing_projects = http_get("projects", "name=eq.Residential%20House%20Construction")
    if existing_projects:
        project_id = existing_projects[0]["id"]
        print(f"   Project exists: {project_id}")
    else:
        proj_res = http_post("projects", {
            "name": "Residential House Construction",
            "description": "Two-Story Residential Structural & Architectural Quantity Takeoff"
        })
        if not proj_res:
            print("Failed to seed project.")
            return
        project_id = proj_res[0]["id"]
        print(f"   Created Project ID: {project_id}")

    print("2. Seeding Drawing record...")
    existing_drawings = http_get("drawings", f"project_id=eq.{project_id}")
    if existing_drawings:
        drawing_id = existing_drawings[0]["id"]
        print(f"   Drawing exists: {drawing_id}")
    else:
        draw_res = http_post("drawings", {
            "project_id": project_id,
            "filename": "Structural_Drawings_Residential_House.dxf",
            "sheet_ref": "S-1",
            "scale_factor": 1.0,
            "scale_confidence": 1.0
        })
        drawing_id = draw_res[0]["id"]
        print(f"   Created Drawing ID: {drawing_id}")

    print("3. Seeding Drawing Elements (DOM)...")
    # Load JSON extraction if available
    elements_payload = []
    
    # Generate realistic elements for Residential House
    sample_elements_data = [
        ("footing", "F-1", "Class A", 0.90, {"kind": "lwpolyline", "closed": True, "points": [[0,0],[1.5,0],[1.5,1.5],[0,1.5]]}, {"layer": "BTCT", "entity_type": "LWPOLYLINE"}),
        ("column", "C-1", "Class A", 0.85, {"kind": "lwpolyline", "closed": True, "points": [[2,2],[2.35,2],[2.35,2.35],[2,2.35]]}, {"layer": "BTCT", "entity_type": "LWPOLYLINE"}),
        ("beam", "2B-1", "Class A", 0.88, {"kind": "line", "start": [0,5], "end": [6,5]}, {"layer": "Net thay", "entity_type": "LINE"}),
        ("beam", "2B-2", "Class A", 0.88, {"kind": "line", "start": [6,5], "end": [12,5]}, {"layer": "Net thay", "entity_type": "LINE"}),
        ("chb_wall", "W-1", None, 0.95, {"kind": "line", "start": [0,0], "end": [12,0]}, {"layer": "Tuong", "entity_type": "LINE"}),
    ]
    
    for e_type, lbl, c_class, conf, geom, raw in sample_elements_data:
        elements_payload.append({
            "drawing_id": drawing_id,
            "element_type": e_type,
            "label": lbl,
            "geometry": geom,
            "concrete_class": c_class,
            "confidence": conf,
            "raw_source": raw
        })
        
    inserted_elements = http_post("drawing_elements", elements_payload)
    if inserted_elements:
        print(f"   Successfully inserted {len(inserted_elements)} drawing elements.")
        element_id_map = {e["label"]: e["id"] for e in inserted_elements}
    else:
        element_id_map = {}

    print("4. Running Takeoff Engine & Seeding Backup Computations & BOQ Checklist...")
    eng = FajardoTakeoffEngine()
    test_elements = [
        TakeoffElement("e1", "footing", "F-1", "Grid 1-A to 4-D", "S-1", 1.5, 1.5, 0.4, 12, "Class A", [{"diameter": 16, "count": 10, "length": 1.7}]),
        TakeoffElement("e2", "column", "C-1", "Ground to 2nd Floor", "S-1", 0.35, 0.35, 3.2, 12, "Class A", [{"diameter": 20, "count": 8, "length": 3.8}, {"diameter": 10, "count": 22, "length": 1.3}]),
        TakeoffElement("e3", "beam", "2B-1", "2nd Floor Framing", "S-2", 6.0, 0.30, 0.50, 8, "Class A", [{"diameter": 20, "count": 6, "length": 6.8}, {"diameter": 10, "count": 35, "length": 1.5}]),
        TakeoffElement("e4", "chb_wall", "W-1", "Exterior Perimeter Wall", "A-1", 35.0, 0.15, 3.0, 1, chb_thickness="150mm", plaster_faces=2),
    ]
    for elem in test_elements:
        if elem.element_type in ["footing", "column", "beam", "slab"]:
            eng.process_concrete_element(elem)
            if elem.rebar_specs:
                eng.process_rebar_specs(elem)
        elif elem.element_type == "chb_wall":
            eng.process_masonry_element(elem)

    backup_payload = []
    for r in eng.backup_rows:
        unit_cost = 0.0
        if "CON-" in r.item_code:
            unit_cost = 9.0 * 310.0 + 0.5 * 1200.0 + 1.0 * 1400.0 + 850.0
        elif "REB-2.0" in r.item_code:
            unit_cost = 90.0
        elif "REB-" in r.item_code:
            unit_cost = 45.0 + 12.0
        elif "MAS-3.1" in r.item_code:
            unit_cost = 12.5 * 14.0 + 0.582 * 310.0 + 0.0444 * 1200.0 + 220.0
        elif "MAS-3.2" in r.item_code:
            unit_cost = 12.5 * 18.0 + 1.010 * 310.0 + 0.0760 * 1200.0 + 220.0
        elif "MAS-3.3" in r.item_code:
            unit_cost = 0.222 * 310.0 + 0.0162 * 1200.0 + 110.0

        lbl_key = r.description.split(" (")[1].replace(")", "") if "(" in r.description else "F-1"
        elem_id = element_id_map.get(lbl_key)

        backup_payload.append({
            "project_id": project_id,
            "element_id": elem_id,
            "work_section": r.work_section,
            "item_code": r.item_code,
            "location_description": r.location_description,
            "drawing_ref": r.drawing_ref,
            "l_or_area": r.length_or_area,
            "w": r.width,
            "h_or_t": r.height_or_thickness,
            "no": r.count,
            "quantity": r.quantity,
            "unit": r.unit,
            "unit_cost": unit_cost,
            "status": r.status
        })

    inserted_backup = http_post("backup_computations", backup_payload)
    if inserted_backup:
        print(f"   Successfully inserted {len(inserted_backup)} back-up computation rows.")

    boq_summary = eng.summarize_to_boq()
    checklist_payload = []
    for b in boq_summary:
        blended_unit_cost = 0.0
        matching_backup = [b_row for b_row in backup_payload if b_row["item_code"] == b.item_code]
        if matching_backup and b.qty > 0:
            tot_amt = sum(mb["quantity"] * mb["unit_cost"] for mb in matching_backup)
            blended_unit_cost = tot_amt / b.qty

        checklist_payload.append({
            "project_id": project_id,
            "item_no": b.item_no,
            "item_code": b.item_code,
            "description": b.description,
            "unit": b.unit,
            "qty": b.qty,
            "unit_cost": round(blended_unit_cost, 2),
            "status": b.status
        })

    inserted_checklist = http_post("boq_checklist", checklist_payload)
    if inserted_checklist:
        print(f"   Successfully inserted {len(inserted_checklist)} BOQ checklist summary items.")

    print("\nDatabase Seeding Completed Successfully!")


if __name__ == "__main__":
    seed_database()
