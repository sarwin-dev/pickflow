"""
Run once when the DB is in perfect demo state:
    python export_demo_seed.py

Generates demo_seed.json with:
- Colors
- Cabinet Types (+ PartTemplates)
- Parts (with active location assignments)
- Warehouse Config
- Active inventory records (is_active=True)
- Work Orders (+ OrderItems)
"""
import json
from app import app
from models import Color, CabinetType, PartTemplate, Part, WarehouseConfig, Inventory, WorkOrder, OrderItem

with app.app_context():
    config = WarehouseConfig.query.first()
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
                    for pt in PartTemplate.query.filter_by(cabinet_type_id=ct.id).all()
                ]
            }
            for ct in CabinetType.query.order_by(CabinetType.id).all()
        ],
        "parts": [
            {
                "name": p.name, "is_shared": p.is_shared,
                "active_aisle": p.active_aisle, "active_bay": p.active_bay,
                "active_shelf": p.active_shelf, "active_location": p.active_location,
            }
            for p in Part.query.order_by(Part.id).all()
        ],
        "warehouse_config": {
            "total_aisles": config.total_aisles,
            "total_bays": config.total_bays,
            "total_shelves": config.total_shelves,
            "total_locations": config.total_locations,
            "active_shelves": config.active_shelves,
            "max_cart_slots": config.max_cart_slots,
            "name": config.name,
            "label_aisle": config.label_aisle,
            "label_bay": config.label_bay,
            "label_shelf": config.label_shelf,
            "label_location": config.label_location,
            "prefix_aisle": config.prefix_aisle,
            "prefix_bay": config.prefix_bay,
            "prefix_shelf": config.prefix_shelf,
            "prefix_location": config.prefix_location,
        } if config else None,
        "active_inventory": [
            {
                "part_name": r.part.name,
                "aisle": r.aisle, "bay": r.bay,
                "shelf": r.shelf, "location": r.location,
                "quantity": r.quantity,
                "min_quantity": r.min_quantity,
            }
            for r in Inventory.query.filter_by(is_active=True).order_by(Inventory.id).all()
        ],
        "work_orders": [
            {
                "order_number": o.order_number,
                "job_name": o.job_name,
                "lot_number": o.lot_number,
                "scheduled_date": o.scheduled_date.isoformat() if o.scheduled_date else None,
                "status": o.status,
                "color_name": o.color.name if o.color else None,
                "items": [
                    {
                        "cabinet_code": i.cabinet.code,
                        "slot": i.slot,
                        "cart": i.cart,
                    }
                    for i in OrderItem.query.filter_by(work_order_id=o.id).all()
                ]
            }
            for o in WorkOrder.query.order_by(WorkOrder.id).all()
        ],
    }

with open("demo_seed.json", "w") as f:
    json.dump(seed, f, indent=2)

print(f"Exported: {len(seed['colors'])} colors, "
      f"{len(seed['cabinet_types'])} cabinet types, "
      f"{len(seed['parts'])} parts, "
      f"{len(seed['active_inventory'])} active records, "
      f"{len(seed['work_orders'])} orders.")
print("demo_seed.json ready.")
