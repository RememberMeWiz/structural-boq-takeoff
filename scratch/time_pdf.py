import sys
import time
sys.path.insert(0, 'dwg_import_pipeline')
from pdf_processor import extract_pdf_drawing_elements

pdf_file = 'dwg_import_pipeline/uploads/c9552a706aa547f2a8efda6b752fdf50_plan_part_1.pdf'
print(f"Timing PDF extraction for {pdf_file}...")
t0 = time.time()
summary = extract_pdf_drawing_elements(pdf_file)
t1 = time.time()

print(f"Done in {t1-t0:.2f} seconds!")
print(f"Page Count: {summary['page_count']}")
print(f"Total Entities: {summary['total_entities']}")
print(f"Elements count: {len(summary['elements'])}")
