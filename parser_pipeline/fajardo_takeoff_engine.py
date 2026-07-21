"""
Automated Quantity Takeoff and Bill of Quantities (BOQ) Generation Engine
Based on Max Fajardo's Simplified Construction Estimate.

Target Trades (Phase 1):
1. Concrete Works (Footings, Columns, Beams, Slabs)
2. Steel Reinforcement (Rebar weight by diameter, GI tie wire)
3. Masonry Works (100mm / 150mm CHB walls, mortar laying, plastering)
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# ====================================================================
# FAJARDO FORMULA LIBRARY REFERENCE FACTORS
# ====================================================================

# 1. Concrete Mix Factors per 1.0 cu.m. (40kg Cement Bag Standard)
CONCRETE_MIX_FACTORS = {
    "Class AA": {"cement_bags": 12.0, "sand_m3": 0.50, "gravel_m3": 1.00},
    "Class A":  {"cement_bags": 9.00, "sand_m3": 0.50, "gravel_m3": 1.00},
    "Class B":  {"cement_bags": 7.50, "sand_m3": 0.50, "gravel_m3": 1.00},
    "Class C":  {"cement_bags": 6.00, "sand_m3": 0.50, "gravel_m3": 1.00},
}

# 2. Rebar Theoretical Unit Weights (kg/m) based on PNS 49 / ASTM A615 (D^2 / 162.2)
REBAR_UNIT_WEIGHTS = {
    10: 0.617,
    12: 0.888,
    16: 1.578,
    20: 2.466,
    25: 3.853,
    28: 4.834,
    32: 6.313,
}

# Tie wire factor (#16 G.I. wire kg per kg of rebar)
TIE_WIRE_FACTOR = 0.015  # 15kg per metric ton

# 3. Masonry factors per 1.0 sq.m. of net wall surface area.
#
# These are deliberately separate from CONCRETE_MIX_FACTORS.  The approved
# specification (tech_spec.md v2.0, Table 2.6.3) provides numerical factors
# for Class B laying mortar; the other mortar classes preserve the same
# mortar volume while changing the cement-to-sand proportion.
#
# Mortar Class Scale (distinct from the concrete-mix A/B/C/D letters):
#   Class A 1:2, Class B 1:3, Class C 1:4, Class D 1:5 (cement:sand by volume)
# The class-to-class cement scaling below is taken directly from the
# per-1.0-cu.m. cement-bag figures published in Table 2.6.3, rather than
# approximated from the mix-ratio "parts" -- the relationship between mix
# ratio and cement yield per cu.m. is not perfectly linear with the parts
# ratio (it also depends on void/bulking assumptions), so scaling off the
# ratio directly understates Class A and overstates Class C/D by ~7-11%.
MORTAR_CLASS_CEMENT_BAGS_PER_M3 = {
    "Class A": 18.0,
    "Class B": 12.0,
    "Class C": 9.0,
    "Class D": 7.5,
}

CHB_COUNT_PER_SQM = 12.5  # Constant for both 100mm and 150mm

# Class B laying-mortar & cell-fill factors per 1.0 sq.m. wall (tech_spec.md §2.6.3)
MORTAR_CLASS_B_FACTORS = {
    "100mm": {"cement_bags": 0.522, "sand_m3": 0.0435},
    "150mm": {"cement_bags": 1.010, "sand_m3": 0.0840},
}

# Plaster factors per 1.0 sq.m. of face (16mm thickness Class B plaster, one face).
PLASTER_CLASS_B_FACTORS_PER_FACE = {
    "16mm": {"cement_bags": 0.192, "sand_m3": 0.016}
}

QA_DIVERGENCE_THRESHOLD = 0.02


def mortar_factors(chb_thickness: str, mortar_class: str) -> Dict[str, float]:
    """Return CHB laying-mortar factors without borrowing concrete mixes."""
    if chb_thickness not in MORTAR_CLASS_B_FACTORS:
        raise ValueError(f"Unsupported CHB thickness: {chb_thickness}")
    if mortar_class not in MORTAR_CLASS_CEMENT_BAGS_PER_M3:
        raise ValueError(f"Unsupported mortar class: {mortar_class}")

    class_b = MORTAR_CLASS_B_FACTORS[chb_thickness]
    cement_scale = (
        MORTAR_CLASS_CEMENT_BAGS_PER_M3[mortar_class]
        / MORTAR_CLASS_CEMENT_BAGS_PER_M3["Class B"]
    )
    return {
        "cement_bags": class_b["cement_bags"] * cement_scale,
        "sand_m3": class_b["sand_m3"],
    }


def plaster_factors(plaster_class: str, thickness: str = "16mm") -> Dict[str, float]:
    """Return plaster factors using the mortar-class scale, not concrete mixes."""
    if thickness not in PLASTER_CLASS_B_FACTORS_PER_FACE:
        raise ValueError(f"Unsupported plaster thickness: {thickness}")
    if plaster_class not in MORTAR_CLASS_CEMENT_BAGS_PER_M3:
        raise ValueError(f"Unsupported plaster class: {plaster_class}")
    class_b = PLASTER_CLASS_B_FACTORS_PER_FACE[thickness]
    cement_scale = (
        MORTAR_CLASS_CEMENT_BAGS_PER_M3[plaster_class]
        / MORTAR_CLASS_CEMENT_BAGS_PER_M3["Class B"]
    )
    return {
        "cement_bags": class_b["cement_bags"] * cement_scale,
        "sand_m3": class_b["sand_m3"],
    }


# ====================================================================
# DATA CLASSES FOR TAKEOFF ELEMENTS & BACKUP COMPUTATIONS
# ====================================================================

@dataclass
class TakeoffElement:
    element_id: str
    element_type: str  # 'footing', 'column', 'beam', 'slab', 'chb_wall'
    label: str  # e.g., 'F-1', 'C-1', '2B-1', 'W-1'
    location: str  # e.g., 'Grid A-1 to B-2'
    drawing_ref: str  # e.g., 'S-1'
    length: float  # meters
    width: float  # meters
    height_or_thickness: float  # meters
    count: int = 1
    concrete_class: str = "Class A"  # for concrete elements
    rebar_specs: List[Dict[str, Any]] = field(default_factory=list)
    # rebar_specs item format: {'diameter': 16, 'count': 8, 'length': 4.5, 'type': 'main'}
    chb_thickness: str = "150mm"  # for masonry
    plaster_faces: int = 2  # standard plaster faces
    mortar_class: str = "Class B"
    plaster_class: str = "Class B"
    opening_area: float = 0.0  # sq.m. per wall occurrence; deducted from gross area


@dataclass(frozen=True)
class CalculationCheck:
    """Comparison of independent takeoff methods for a single element."""
    element_id: str
    check_name: str
    primary_quantity: float
    secondary_quantity: float
    divergence_ratio: float
    warning: bool


@dataclass
class BackupComputationRow:
    work_section: str  # 'Concrete Works', 'Steel Reinforcement', 'Masonry Works'
    item_code: str  # e.g., 'CON-1.1', 'REB-2.1', 'MAS-3.1'
    description: str
    location_description: str
    drawing_ref: str
    length_or_area: float
    width: float
    height_or_thickness: float
    count: float
    quantity: float
    unit: str  # 'cu.m.', 'sq.m.', 'kg', 'pc'
    unit_cost: float = 0.0
    amount: float = 0.0
    status: str = "Confirmed"


@dataclass
class BOQChecklistItem:
    item_no: str
    item_code: str
    description: str
    unit: str
    qty: float
    unit_cost: float = 0.0
    amount: float = 0.0
    status: str = "Confirmed"


# ====================================================================
# FAJARDO TAKEOFF CALCULATOR ENGINE
# ====================================================================

class FajardoTakeoffEngine:
    def __init__(self, base_prices: Optional[Dict[str, float]] = None):
        # Base Prices (PHP) sourced from DPWH Construction Materials Price Data (CMPD.pdf)
        self.base_prices = base_prices or {
            "Cement (40kg bag)": 205.36,         # MG03.0002 PORTLAND CEMENT (40 kg)
            "Sand (cu.m.)": 1473.21,             # MG01.0008 FINE AGGREGATE (SAND)
            "Gravel (cu.m.)": 1517.86,           # MG01.0009 GRAVEL, 3/4" (MAS 20 mm)
            "Rebar (per kg)": 42.68,             # MG10.0001 REINFORCING STEEL BAR (GRADE 40)
            "Tie Wire #16 G.I. (per kg)": 62.50, # MG10.0003 GI TIE WIRE #16
            "100mm CHB (per pc)": 15.18,          # MG04.0003 CHB ORDINARY (4" x 8" x 16")
            "150mm CHB (per pc)": 22.32,          # MG04.0004 CHB ORDINARY (6" x 8" x 16")
            "Concrete Works Labor (per cu.m.)": 850.0,
            "Rebar Works Labor (per kg)": 12.0,
            "Masonry Works Labor (per sq.m.)": 220.0,
        }
        self.backup_rows: List[BackupComputationRow] = []
        self.calculation_checks: List[CalculationCheck] = []

    def _record_check(
        self,
        elem: TakeoffElement,
        check_name: str,
        primary_quantity: float,
        secondary_quantity: float,
    ) -> CalculationCheck:
        denominator = max(abs(primary_quantity), abs(secondary_quantity), 1e-9)
        divergence = abs(primary_quantity - secondary_quantity) / denominator
        # Small epsilon guards against floating-point noise (e.g. a
        # mathematically-exact 2% divergence evaluating as
        # 0.020000000000000018) spuriously tripping the QA warning.
        check = CalculationCheck(
            element_id=elem.element_id,
            check_name=check_name,
            primary_quantity=primary_quantity,
            secondary_quantity=secondary_quantity,
            divergence_ratio=divergence,
            warning=divergence > QA_DIVERGENCE_THRESHOLD + 1e-9,
        )
        self.calculation_checks.append(check)
        return check

    @property
    def qa_warnings(self) -> List[CalculationCheck]:
        """Checks exceeding the approved 2 percent divergence threshold."""
        return [check for check in self.calculation_checks if check.warning]

    def process_concrete_element(self, elem: TakeoffElement) -> float:
        """Computes volume and adds Back-Up Computation row for Concrete Works."""
        # Volume V = L * W * H * count
        volume = elem.length * elem.width * elem.height_or_thickness * elem.count
        # Independent linear-meter method: section area x total member length.
        linear_meter_volume = (elem.width * elem.height_or_thickness) * (elem.length * elem.count)
        check = self._record_check(elem, "Concrete volume: L x W x H vs section x linear meters", volume, linear_meter_volume)
        
        # Item code mapping
        code_map = {
            'footing': ('CON-1.1', 'Concrete Works - Isolated Footings'),
            'column': ('CON-1.2', 'Concrete Works - Columns'),
            'beam': ('CON-1.3', 'Concrete Works - Beams'),
            'slab': ('CON-1.4', 'Concrete Works - Slabs'),
        }
        item_code, desc_prefix = code_map.get(elem.element_type.lower(), ('CON-1.5', 'Concrete Works - Other'))
        
        row = BackupComputationRow(
            work_section="II. Concrete Works",
            item_code=item_code,
            description=f"{desc_prefix} ({elem.label}, {elem.concrete_class})",
            location_description=elem.location,
            drawing_ref=elem.drawing_ref,
            length_or_area=elem.length,
            width=elem.width,
            height_or_thickness=elem.height_or_thickness,
            count=float(elem.count),
            quantity=round(volume, 3),
            unit="cu.m.",
            status="QA warning: volume methods diverge >2%" if check.warning else "Confirmed",
        )
        self.backup_rows.append(row)
        return volume

    def process_rebar_specs(self, elem: TakeoffElement) -> float:
        """Computes weight for reinforcement and adds Back-Up Computation rows."""
        total_weight_kg = 0.0
        
        for spec in elem.rebar_specs:
            dia = spec.get('diameter', 16)
            count = spec.get('count', 1)
            bar_len = spec.get('length', elem.length)
            unit_wt = REBAR_UNIT_WEIGHTS.get(dia, (dia ** 2) / 162.2)
            
            total_bar_len = bar_len * count * elem.count
            bar_weight_kg = total_bar_len * unit_wt
            theoretical_weight_kg = total_bar_len * ((dia ** 2) / 162.2)
            check = self._record_check(
                elem,
                f"Rebar weight Ø{dia}: PNS 49 / ASTM A615 table vs D²/162.2",
                bar_weight_kg,
                theoretical_weight_kg,
            )
            total_weight_kg += bar_weight_kg
            
            row = BackupComputationRow(
                work_section="III. Steel Reinforcement",
                item_code=f"REB-2.{dia}",
                description=f"Deformed Rebar Ø{dia}mm ({elem.label})",
                location_description=elem.location,
                drawing_ref=elem.drawing_ref,
                length_or_area=round(bar_len, 3),
                width=1.0,
                height_or_thickness=1.0,
                count=float(count * elem.count),
                quantity=round(bar_weight_kg, 2),
                unit="kg",
                status="QA warning: rebar methods diverge >2%" if check.warning else "Confirmed",
            )
            self.backup_rows.append(row)
            
        # Tie wire addition
        if total_weight_kg > 0:
            tie_wire_kg = total_weight_kg * TIE_WIRE_FACTOR
            self.backup_rows.append(BackupComputationRow(
                work_section="III. Steel Reinforcement",
                item_code="REB-2.0",
                description=f"#16 G.I. Tie Wire ({elem.label})",
                location_description=elem.location,
                drawing_ref=elem.drawing_ref,
                length_or_area=round(total_weight_kg, 2),
                width=1.0,
                height_or_thickness=1.0,
                count=1.0,
                quantity=round(tie_wire_kg, 2),
                unit="kg"
            ))
            
        return total_weight_kg

    def process_masonry_element(self, elem: TakeoffElement) -> float:
        """Computes CHB wall surface area and adds Back-Up Computation rows for CHB & Plastering."""
        if elem.opening_area < 0:
            raise ValueError("opening_area cannot be negative")
        gross_wall_area = elem.length * elem.height_or_thickness * elem.count
        total_opening_area = elem.opening_area * elem.count
        wall_area = gross_wall_area - total_opening_area
        if wall_area < 0:
            raise ValueError("opening_area cannot exceed gross wall area")
        chb_pcs = wall_area * CHB_COUNT_PER_SQM
        # Independent layer-count method.  It intentionally exposes partial
        # block/course assumptions instead of hiding them in the area factor.
        blocks_per_course = math.ceil(elem.length / 0.40)
        course_count = math.ceil(elem.height_or_thickness / 0.20)
        layer_count_chb = (blocks_per_course * course_count * elem.count) - round(total_opening_area * CHB_COUNT_PER_SQM)
        check = self._record_check(elem, "CHB count: net area factor vs block-course layers", chb_pcs, layer_count_chb)
        mortar = mortar_factors(elem.chb_thickness, elem.mortar_class)
        
        # CHB Wall Row
        self.backup_rows.append(BackupComputationRow(
            work_section="IV. Masonry Works",
            item_code="MAS-3.1" if elem.chb_thickness == "100mm" else "MAS-3.2",
            description=(f"{elem.chb_thickness} CHB Wall ({elem.label}; {elem.mortar_class} mortar: "
                         f"{mortar['cement_bags']:.3f} bag/m², {mortar['sand_m3']:.4f} m³ sand/m²)"),
            location_description=elem.location,
            drawing_ref=elem.drawing_ref,
            length_or_area=elem.length,
            width=1.0,
            height_or_thickness=elem.height_or_thickness,
            count=float(elem.count),
            quantity=round(wall_area, 2),
            unit="sq.m.",
            status="QA warning: area and layer counts diverge >2%" if check.warning else "Confirmed",
        ))
        
        # Plastering Row
        if elem.plaster_faces > 0:
            plaster_area = wall_area * elem.plaster_faces
            plaster = plaster_factors(elem.plaster_class)

            # Independent cross-check per spec §2.5.3 ("Plastering: Volume
            # Method vs. Area Method"): re-derive the plastered area from the
            # same block-course layer count used for the CHB cross-check
            # above (course count x block face width x plaster_faces), which
            # is a geometrically independent route from the plain
            # length x height x count multiplication used for the primary
            # Area Method figure.
            block_face_width = 0.40
            course_layer_area = blocks_per_course * block_face_width * course_count * 0.20 * elem.count
            layer_plaster_area = (course_layer_area - total_opening_area) * elem.plaster_faces
            plaster_check = self._record_check(
                elem,
                "Plastering: Area Method (L x H) vs block-course layer area",
                plaster_area,
                layer_plaster_area,
            )

            plaster_status = "Confirmed"
            if check.warning:
                plaster_status = "QA warning: source wall area has CHB count divergence >2%"
            elif plaster_check.warning:
                plaster_status = "QA warning: plaster area methods diverge >2%"

            self.backup_rows.append(BackupComputationRow(
                work_section="IV. Masonry Works",
                item_code="MAS-3.3",
                description=(f"16mm Cement Plaster ({elem.plaster_faces} faces, {elem.label}; "
                             f"{elem.plaster_class}: {plaster['cement_bags']:.3f} bag/m², "
                             f"{plaster['sand_m3']:.4f} m³ sand/m²)"),
                location_description=elem.location,
                drawing_ref=elem.drawing_ref,
                length_or_area=wall_area,
                width=1.0,
                height_or_thickness=1.0,
                count=float(elem.plaster_faces),
                quantity=round(plaster_area, 2),
                unit="sq.m.",
                status=plaster_status,
            ))
            
        return wall_area

    def unit_cost_for_row(self, row: BackupComputationRow) -> float:
        """Return a current rate using the element's concrete or mortar factors."""
        cement = self.base_prices["Cement (40kg bag)"]
        sand = self.base_prices["Sand (cu.m.)"]
        gravel = self.base_prices["Gravel (cu.m.)"]
        if row.item_code.startswith("CON-"):
            concrete_class = next((name for name in CONCRETE_MIX_FACTORS if name in row.description), "Class A")
            factor = CONCRETE_MIX_FACTORS[concrete_class]
            return factor["cement_bags"] * cement + factor["sand_m3"] * sand + factor["gravel_m3"] * gravel + self.base_prices["Concrete Works Labor (per cu.m.)"]
        if row.item_code == "REB-2.0":
            return self.base_prices["Tie Wire #16 G.I. (per kg)"]
        if row.item_code.startswith("REB-"):
            return self.base_prices["Rebar (per kg)"] + self.base_prices["Rebar Works Labor (per kg)"]
        if row.item_code in {"MAS-3.1", "MAS-3.2"}:
            thickness = "100mm" if row.item_code == "MAS-3.1" else "150mm"
            mortar_class = next((name for name in MORTAR_CLASS_CEMENT_BAGS_PER_M3 if name in row.description), "Class B")
            factor = mortar_factors(thickness, mortar_class)
            chb = self.base_prices[f"{thickness} CHB (per pc)"]
            return CHB_COUNT_PER_SQM * chb + factor["cement_bags"] * cement + factor["sand_m3"] * sand + self.base_prices["Masonry Works Labor (per sq.m.)"]
        if row.item_code == "MAS-3.3":
            plaster_class = next((name for name in MORTAR_CLASS_CEMENT_BAGS_PER_M3 if name in row.description), "Class B")
            factor = plaster_factors(plaster_class)
            return factor["cement_bags"] * cement + factor["sand_m3"] * sand + self.base_prices["Masonry Works Labor (per sq.m.)"] / 2
        return 0.0

    def summarize_to_boq(self) -> List[BOQChecklistItem]:
        """Rolls up Back-Up Computation rows into summary BOQ Checklist Items."""
        summary_dict: Dict[str, Dict[str, Any]] = {}
        
        for row in self.backup_rows:
            key = row.item_code
            if key not in summary_dict:
                summary_dict[key] = {
                    'item_code': row.item_code,
                    'work_section': row.work_section,
                    'description': row.description.split(' (')[0],  # high-level title
                    'unit': row.unit,
                    'qty': 0.0,
                }
            summary_dict[key]['qty'] += row.quantity
            
        checklist: List[BOQChecklistItem] = []
        item_counter = 1
        for key, data in summary_dict.items():
            checklist.append(BOQChecklistItem(
                item_no=f"2.{item_counter}",
                item_code=data['item_code'],
                description=data['description'],
                unit=data['unit'],
                qty=round(data['qty'], 2),
                unit_cost=0.0,  # Computed via Excel formulas or base prices
                amount=0.0
            ))
            item_counter += 1
            
        return checklist


# Simple CLI / Test Execution
if __name__ == "__main__":
    engine = FajardoTakeoffEngine()
    
    # Test elements based on real structural drawing members
    test_elements = [
        TakeoffElement(
            element_id="elem-01",
            element_type="footing",
            label="F-1",
            location="Grid 1-A to 4-D",
            drawing_ref="S-1",
            length=1.5,
            width=1.5,
            height_or_thickness=0.4,
            count=12,
            concrete_class="Class A",
            rebar_specs=[{"diameter": 16, "count": 10, "length": 1.7, "type": "footing_mat"}]
        ),
        TakeoffElement(
            element_id="elem-02",
            element_type="column",
            label="C-1",
            location="Ground to 2nd Floor",
            drawing_ref="S-1",
            length=0.35,
            width=0.35,
            height_or_thickness=3.2,
            count=12,
            concrete_class="Class A",
            rebar_specs=[
                {"diameter": 20, "count": 8, "length": 3.8, "type": "main"},
                {"diameter": 10, "count": 22, "length": 1.3, "type": "ties"}
            ]
        ),
        TakeoffElement(
            element_id="elem-03",
            element_type="beam",
            label="2B-1",
            location="2nd Floor Framing",
            drawing_ref="S-2",
            length=6.0,
            width=0.30,
            height_or_thickness=0.50,
            count=8,
            concrete_class="Class A",
            rebar_specs=[
                {"diameter": 20, "count": 6, "length": 6.8, "type": "main"},
                {"diameter": 10, "count": 35, "length": 1.5, "type": "stirrups"}
            ]
        ),
        TakeoffElement(
            element_id="elem-04",
            element_type="chb_wall",
            label="W-1",
            location="Exterior Perimeter Wall",
            drawing_ref="A-1",
            length=35.0,
            width=0.15,
            height_or_thickness=3.0,
            count=1,
            chb_thickness="150mm",
            plaster_faces=2
        ),
    ]

    for elem in test_elements:
        if elem.element_type in ["footing", "column", "beam", "slab"]:
            engine.process_concrete_element(elem)
            if elem.rebar_specs:
                engine.process_rebar_specs(elem)
        elif elem.element_type == "chb_wall":
            engine.process_masonry_element(elem)

    print(f"Generated {len(engine.backup_rows)} Back-Up Computation rows:")
    for r in engine.backup_rows[:5]:
        print(f" [{r.item_code}] {r.description} -> {r.quantity} {r.unit} ({r.location_description})")
        
    boq_summary = engine.summarize_to_boq()
    print(f"\nGenerated {len(boq_summary)} BOQ Checklist Summary items:")
    for b in boq_summary:
        print(f" [{b.item_no}] {b.item_code} | {b.description:<35} | {b.qty:>8.2f} {b.unit}")
