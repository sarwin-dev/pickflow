from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from extensions import db
from models import WorkOrder, OrderItem, PickItem, Part
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

    # agrupa las partes por (ubicacion, carrito)
    # cada grupo = una ubicacion + carrito con todos los slots que la necesitan
    location_groups = {}
    for item in order.items:
        for template in item.cabinet.parts:
            part = template.part
            if part.active_aisle:
                loc_key = f"A{int(part.active_aisle):02d}.B{int(part.active_bay):02d}.S{int(part.active_shelf):02d}"
                if part.active_location:
                    loc_key += f".L{int(part.active_location):02d}"
            else:
                loc_key = "NO_LOCATION"

            group_key = (loc_key, template.cart)

            if group_key not in location_groups:
                location_groups[group_key] = {
                    'location': loc_key,
                    'part_name': part.name,
                    'cart': template.cart,
                    'aisle': int(part.active_aisle) if part.active_aisle else 99,
                    'bay': int(part.active_bay) if part.active_bay else 99,
                    'shelf': int(part.active_shelf) if part.active_shelf else 99,
                    'loc': int(part.active_location) if part.active_location else 99,
                    'slots': []
                }

            pick_item = PickItem.query.join(OrderItem).filter(
                OrderItem.id == item.id,
                PickItem.part_template_id == template.id
            ).first()

            location_groups[group_key]['slots'].append({
                'slot': item.slot,
                'pick_item_id': pick_item.id if pick_item else None,
                'is_picked': pick_item.is_picked if pick_item else False,
                'picked_by': pick_item.picked_by if pick_item else None,
            })

    sorted_groups = sorted(
        location_groups.values(),
        key=lambda x: (x['cart'], x['aisle'], x['bay'], x['shelf'], x['loc'])
    )

    return render_template('pick/pick_order.html',
                           order=order,
                           groups=sorted_groups)

@pick_bp.route('/toggle/<int:pick_item_id>', methods=['POST'])
def toggle(pick_item_id):
    check = picker_required()
    if check:
        return jsonify({'error': 'unauthorized'}), 401

    pick_item = PickItem.query.get(pick_item_id)
    action = request.json.get('action', 'pick')

    if pick_item:
        # cambia a in_progress en el primer pick
        order = pick_item.order_item.order
        if order.status == 'pending' and action == 'pick':
            order.status = 'in_progress'

        if action == 'pick':
            # marca como picked - inventario se controla solo en pulldown (two-bin)
            pick_item.is_picked = True
            pick_item.is_missing = False
            pick_item.picked_by = session['user_id']
            pick_item.picked_at = datetime.utcnow()

        elif action == 'missing':
            # marca como missing
            pick_item.is_picked = False
            pick_item.is_missing = True
            pick_item.picked_by = None
            pick_item.picked_at = None

        elif action == 'reset':
            # vuelve a pending
            pick_item.is_picked = False
            pick_item.is_missing = False
            pick_item.picked_by = None
            pick_item.picked_at = None

        db.session.commit()

        # recuenta desde la base de datos
        order = pick_item.order_item.order
        total = PickItem.query.join(OrderItem).filter(
            OrderItem.work_order_id == order.id
        ).count()
        picked = PickItem.query.join(OrderItem).filter(
            OrderItem.work_order_id == order.id,
            PickItem.is_picked == True
        ).count()
        missing = PickItem.query.join(OrderItem).filter(
            OrderItem.work_order_id == order.id,
            PickItem.is_missing == True
        ).count()

        # completa la orden solo si todo esta picked o missing
        if picked + missing == total:
            order.status = 'completed'
            db.session.commit()

        return jsonify({
            'success': True,
            'is_picked': pick_item.is_picked,
            'is_missing': pick_item.is_missing,
            'picked': picked,
            'missing': missing,
            'total': total
        })
    return jsonify({'error': 'not found'}), 404

# resetea una orden a pending - solo supervisor y admin
@pick_bp.route('/reset/<int:order_id>')
def reset_order(order_id):
    check = picker_required()
    if check:
        return check
    if session['user_role'] not in ['admin', 'supervisor']:
        return redirect(url_for('dashboard'))
    order = WorkOrder.query.get(order_id)
    if order:
        # resetea todos los pick items
        for item in order.items:
            for pick in item.picks:
                pick.is_picked = False
                pick.is_missing = False
                pick.picked_by = None
                pick.picked_at = None
        order.status = 'pending'
        db.session.commit()
    return redirect(url_for('pick.index'))

# genera el pdf de la pick list
@pick_bp.route('/<int:order_id>/pdf')
def generate_pdf(order_id):
    check = picker_required()
    if check:
        return check

    import io
    from weasyprint import HTML, CSS
    from flask import render_template, send_file

    order = WorkOrder.query.get(order_id)

    # reutiliza la misma logica de agrupacion que pick_order
    location_groups = {}
    for item in order.items:
        for template in item.cabinet.parts:
            part = template.part
            if part.active_aisle:
                loc_key = f"A{int(part.active_aisle):02d}.B{int(part.active_bay):02d}.S{int(part.active_shelf):02d}"
                if part.active_location:
                    loc_key += f".L{int(part.active_location):02d}"
            else:
                loc_key = "NO_LOCATION"
            group_key = (loc_key, template.cart)
            if group_key not in location_groups:
                location_groups[group_key] = {
                    'location': loc_key,
                    'part_name': part.name,
                    'cart': template.cart,
                    'aisle': int(part.active_aisle) if part.active_aisle else 99,
                    'bay': int(part.active_bay) if part.active_bay else 99,
                    'shelf': int(part.active_shelf) if part.active_shelf else 99,
                    'loc': int(part.active_location) if part.active_location else 99,
                    'slots': []
                }
            location_groups[group_key]['slots'].append(item.slot)

    sorted_groups = sorted(
        location_groups.values(),
        key=lambda x: (x['cart'], x['aisle'], x['bay'], x['shelf'], x['loc'])
    )

    # renderiza el template HTML igual que la pantalla
    html_string = render_template(
        'pick/pick_order_pdf.html',
        order=order,
        groups=sorted_groups,
        user_name=session['user_name']
    )

    pdf_bytes = HTML(string=html_string, base_url=request.host_url).write_pdf()
    buffer = io.BytesIO(pdf_bytes)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"picklist_{order.order_number}.pdf"
    )