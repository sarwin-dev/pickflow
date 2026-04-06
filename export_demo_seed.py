"""
Run once when the DB is in perfect demo state:
    python export_demo_seed.py

Generates demo_seed.json with Colors, CabinetTypes (+ PartTemplates), and Parts.
"""
import json
from app import app
from models import Color, CabinetType, PartTemplate, Part

with app.app_context():
    seed = {
        "colors": [
            {"name": c.name, "hex_code": c.hex_code}
            for c in Color.query.order_by(Color.id).all()
        ],
        "cabinet_types": [
            {
                "code": ct.code, "name": ct.name,
                "width": ct.width, "height": ct.height,
                "color": ct.color, "is_custom": ct.is_custom,
                "part_templates": [
                    {
                        "part_name": pt.part.name,
                        "quantity": pt.quantity,
                        "cart": pt.cart,
                        "is_optional": pt.is_optional,
                    }
                    for pt in pt_list
                ]
            }
            for ct, pt_list in [
                (ct, PartTemplate.query.filter_by(cabinet_type_id=ct.id).all())
                for ct in CabinetType.query.order_by(CabinetType.id).all()
            ]
        ],
        "parts": [
            {
                "name": p.name, "is_shared": p.is_shared,
                "active_aisle": p.active_aisle, "active_bay": p.active_bay,
                "active_shelf": p.active_shelf, "active_location": p.active_location,
            }
            for p in Part.query.order_by(Part.id).all()
        ],
    }

with open("demo_seed.json", "w") as f:
    json.dump(seed, f, indent=2)

print(f"Exported: {len(seed['colors'])} colors, "
      f"{len(seed['cabinet_types'])} cabinet types, "
      f"{len(seed['parts'])} parts.")
print("demo_seed.json ready.")
