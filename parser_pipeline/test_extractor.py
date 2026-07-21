import os
import sys

# Ensure parser_pipeline folder is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from dxf_parser import DXFParser
from extractor import DXFExtractor

def main():
    dxf_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "requirements", "inputs", "2nd_floor_beam_framing_plan.dxf"
    )
    print(f"Loading DXF from: {dxf_path}")
    parser = DXFParser(dxf_path)
    
    print("Parsing DXF...")
    parser.parse()
    
    print("Splitting entities...")
    entities = parser.split_entities()
    print(f"Found {len(entities)} total entities in section ENTITIES")
    
    extractor = DXFExtractor(entities)
    
    print("Extracting Beam Line segments...")
    beam_segments = extractor.extract_segments(target_layers={"Beam Line"})
    print(f"Extracted {len(beam_segments)} 'Beam Line' segments")
    
    print("Extracting Beam Label texts...")
    beam_labels = extractor.extract_text(target_layers={"Beam Label"})
    print(f"Extracted {len(beam_labels)} 'Beam Label' texts")
    
    # Assertions
    assert len(beam_segments) == 276, f"Expected 276 Beam Line segments, got {len(beam_segments)}"
    assert len(beam_labels) == 156, f"Expected 156 Beam Label texts, got {len(beam_labels)}"
    
    print("\nSUCCESS: DXF Parser and Extractor tests passed successfully!")

if __name__ == "__main__":
    main()
