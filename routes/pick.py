from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from extensions import db
from models import WorkOrder, OrderItem, PickItem, PartTemplate, Part, Inventory
from datetime import datetime

pick_bp = Blueprint('pick', __name__, url_prefix='/pick')

def picker_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'warehouse', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None

# lista de ordenes disponibles para pick
@pick_bp.route('/')
def index():
    check = picker_required()
    if check:
        return check
    # solo ordenes pendientes o en progreso
    orders = WorkOrder.query.filter(
        WorkOrder.status.in_(['pending', 'in_progress'])
    ).order_by(WorkOrder.created_at.desc()).all()
    return render_template('pick/index.html', orders=orders)

# genera y muestra la pick list de una orden
@pick_bp.route('/<int:order_id>')
def pick_order(order_id):
    check = picker_required()
    if check:
        return check
    order = WorkOrder.query.get(order_id)
    if not order:
        return redirect(url_for('pick.index'))

    # cambia el status a in_progress si estaba pending
    if order.status == 'pending':
        order.status = 'in_progress'
        db.session.commit()

    # genera los pick items si no existen todavia
    for item in order.items:
        existing = PickItem.query.filter_by(order_item_id=item.id).first()
        if not existing:
            for template in item.cabinet.parts:
                for qty in range(template.quantity):
                    pick_item = PickItem(
                        order_item_id=item.id,
                        part_template_id=template.id,
                        is_picked=False
                    )
                    db.session.add(pick_item)
    db.session.commit()

    # agrupa las partes por ubicacion para el orden de picking
    # cada grupo = una ubicacion ABSL con todos los slots que la necesitan
    location_groups = {}
    for item in order.items:
        for template in item.cabinet.parts:
            part = template.part
            # crea la clave de ubicacion
            if part.active_aisle:
                loc_key = f"A{int(part.active_aisle):02d}.B{int(part.active_bay):02d}.S{int(part.active_shelf):02d}"
                if part.active_location:
                    loc_key += f".L{int(part.active_location):02d}"
            else:
                loc_key = "NO_LOCATION"

            if loc_key not in location_groups:
                location_groups[loc_key] = {
                    'location': loc_key,
                    'part_name': part.name,
                    'aisle': int(part.active_aisle) if part.active_aisle else 99,
                    'bay': int(part.active_bay) if part.active_bay else 99,
                    'shelf': int(part.active_shelf) if part.active_shelf else 99,
                    'slots': []
                }

            # busca el pick item correspondiente
            pick_item = PickItem.query.join(OrderItem).filter(
                OrderItem.id == item.id,
                PickItem.part_template_id == template.id
            ).first()

            location_groups[loc_key]['slots'].append({
                'slot': item.slot,
                'pick_item_id': pick_item.id if pick_item else None,
                'is_picked': pick_item.is_picked if pick_item else False,
                'picked_by': pick_item.picked_by if pick_item else None,
            })

    # ordena por aisle, bay, shelf
    sorted_groups = sorted(
        location_groups.values(),
        key=lambda x: (x['aisle'], x['bay'], x['shelf'])
    )

    return render_template('pick/pick_order.html',
                           order=order,
                           groups=sorted_groups)

# marca o desmarca un pick item
@pick_bp.route('/toggle/<int:pick_item_id>', methods=['POST'])
def toggle(pick_item_id):
    check = picker_required()
    if check:
        return jsonify({'error': 'unauthorized'}), 401
    pick_item = PickItem.query.get(pick_item_id)
    if pick_item:
        pick_item.is_picked = not pick_item.is_picked
        if pick_item.is_picked:
            pick_item.picked_by = session['user_id']
            pick_item.picked_at = datetime.utcnow()
            # descuenta del inventario activo
            part = pick_item.order_item.cabinet.parts
            template = PartTemplate.query.get(pick_item.part_template_id)
            inventory = Inventory.query.filter_by(
                part_id=template.part_id,
                is_active=True
            ).first()
            if inventory:
                inventory.quantity -= 1
                inventory.updated_at = datetime.utcnow()
                if inventory.quantity <= 0:
                    db.session.delete(inventory)
        else:
            pick_item.picked_by = None
            pick_item.picked_at = None
        db.session.commit()
        # verifica si la orden esta completa
        order = pick_item.order_item.order
        total = PickItem.query.join(OrderItem).filter(
            OrderItem.work_order_id == order.id
        ).count()
        picked = PickItem.query.join(OrderItem).filter(
            OrderItem.work_order_id == order.id,
            PickItem.is_picked == True
        ).count()
        if total == picked:
            order.status = 'completed'
            db.session.commit()
        return jsonify({
            'success': True,
            'is_picked': pick_item.is_picked,
            'picked': picked,
            'total': total
        })
    return jsonify({'error': 'not found'}), 404