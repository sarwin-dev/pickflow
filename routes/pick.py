from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from extensions import db
from models import WorkOrder, OrderItem, PickItem, Part, Inventory, PartTemplate
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
    from sqlalchemy import nullslast
    from datetime import date as date_type
    orders = WorkOrder.query.filter(
        WorkOrder.status.in_(['pending', 'in_progress', 'completed'])
    ).order_by(nullslast(WorkOrder.scheduled_date.asc()), WorkOrder.created_at.asc()).all()

    # agrega conteo de pick items por orden
    order_stats = []
    for o in orders:
        total = PickItem.query.join(OrderItem).filter(OrderItem.work_order_id == o.id).count()
        picked = PickItem.query.join(OrderItem).filter(
            OrderItem.work_order_id == o.id, PickItem.is_picked == True
        ).count()
        missing = PickItem.query.join(OrderItem).filter(
            OrderItem.work_order_id == o.id, PickItem.is_missing == True
        ).count()
        order_stats.append({'order': o, 'total': total, 'picked': picked, 'missing': missing})

    # agrupa por fecha programada
    grouped = {}
    for s in order_stats:
        key = s['order'].scheduled_date
        grouped.setdefault(key, []).append(s)
    date_groups = sorted(grouped.items(), key=lambda x: (x[0] is None, x[0] or date_type.max))

    return render_template('pick/index.html', date_groups=date_groups)

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
                    'slots': [],
                    'any_pick_item_id': None,
                    'is_on_hold': part.is_on_hold,
                }

            pick_item = PickItem.query.join(OrderItem).filter(
                OrderItem.id == item.id,
                PickItem.part_template_id == template.id
            ).first()

            if pick_item and location_groups[group_key]['any_pick_item_id'] is None:
                location_groups[group_key]['any_pick_item_id'] = pick_item.id

            location_groups[group_key]['slots'].append({
                'slot': item.slot,
                'pick_item_id': pick_item.id if pick_item else None,
                'is_picked': pick_item.is_picked if pick_item else False,
                'is_missing': pick_item.is_missing if pick_item else False,
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
        depleted = False
        # cambia a in_progress en el primer pick
        order = pick_item.order_item.order
        if order.status == 'pending' and action == 'pick':
            order.status = 'in_progress'

        # aplica la accion a TODOS los pick items del mismo (slot, parte)
        # necesario cuando template.quantity > 1 crea multiples pick items por slot
        siblings = PickItem.query.filter_by(
            order_item_id=pick_item.order_item_id,
            part_template_id=pick_item.part_template_id
        ).all()

        if action == 'pick':
            for pi in siblings:
                pi.is_picked = True
                pi.is_missing = False
                pi.picked_by = session['user_id']
                pi.picked_at = datetime.utcnow()

        elif action == 'deplete':
            # elimina el registro activo de inventario de la parte específica
            pt = PartTemplate.query.get(pick_item.part_template_id)
            if pt:
                active_record = Inventory.query.filter_by(
                    part_id=pt.part_id, is_active=True
                ).first()
                if active_record:
                    db.session.delete(active_record)
                    depleted = True
            # marca como missing TODOS los pick items pendientes de la orden completa
            # esto permite que el botón Complete Order se active inmediatamente
            pending_items = PickItem.query.join(OrderItem).filter(
                OrderItem.work_order_id == order.id,
                PickItem.is_picked == False,
                PickItem.is_missing == False
            ).all()
            for pi in pending_items:
                pi.is_missing = True

        elif action == 'reset':
            for pi in siblings:
                pi.is_picked = False
                pi.is_missing = False
                pi.picked_by = None
                pi.picked_at = None
            # si la orden estaba completada la reabre
            if order.status == 'completed':
                order.status = 'in_progress'

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
            'total': total,
            'depleted': depleted,
        })
    return jsonify({'error': 'not found'}), 404

# marca todos los pending de una orden como missing + activa is_on_hold en las partes
# esto es para cuando el picker no encuentra stock en el active shelf
@pick_bp.route('/<int:order_id>/mark-missing-all', methods=['POST'])
def mark_missing_all(order_id):
    check = picker_required()
    if check:
        return jsonify({'error': 'unauthorized'}), 401

    order = WorkOrder.query.get(order_id)
    if not order:
        return jsonify({'error': 'not found'}), 404

    # obtiene todos los pending PickItems de la orden
    pending_items = PickItem.query.join(OrderItem).filter(
        OrderItem.work_order_id == order.id,
        PickItem.is_picked == False,
        PickItem.is_missing == False
    ).all()

    # recolecta las partes para activar is_on_hold
    parts_to_hold = set()
    for pi in pending_items:
        pi.is_missing = True
        # obtiene la parte de este pick item
        part_template = PartTemplate.query.get(pi.part_template_id)
        if part_template:
            parts_to_hold.add(part_template.part_id)

    # activa is_on_hold para todas las partes faltantes
    # esto notifica globalmente que esas partes necesitan pulldown
    for part_id in parts_to_hold:
        part = Part.query.get(part_id)
        if part:
            part.is_on_hold = True

    db.session.commit()

    # recuenta desde la base de datos
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

    return jsonify({
        'success': True,
        'picked': picked,
        'missing': missing,
        'total': total,
        'parts_on_hold': len(parts_to_hold),
    })

# cierra la orden marcando todo lo pendiente como missing
@pick_bp.route('/<int:order_id>/complete', methods=['POST'])
def complete_order(order_id):
    check = picker_required()
    if check:
        return jsonify({'error': 'unauthorized'}), 401
    order = WorkOrder.query.get(order_id)
    if not order:
        return jsonify({'error': 'not found'}), 404

    # marca todos los pendientes como missing
    pending = PickItem.query.join(OrderItem).filter(
        OrderItem.work_order_id == order.id,
        PickItem.is_picked == False,
        PickItem.is_missing == False
    ).all()
    for pi in pending:
        pi.is_missing = True

    order.status = 'completed'
    db.session.commit()
    return jsonify({'success': True})


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
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from flask import send_file
    from datetime import datetime as dt

    order = WorkOrder.query.get(order_id)

    # misma logica de agrupacion que pick_order
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

    sorted_groups = sorted(location_groups.values(),
        key=lambda x: (x['cart'], x['aisle'], x['bay'], x['shelf'], x['loc']))

    cart_a = [g for g in sorted_groups if g['cart'] == 1]
    cart_b = [g for g in sorted_groups if g['cart'] == 2]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)

    navy = colors.HexColor('#1e1b4b')
    light = colors.HexColor('#f9fafb')
    border = colors.HexColor('#e5e7eb')
    indigo = colors.HexColor('#eef2ff')
    now_str = dt.now().strftime('%m/%d/%Y %I:%M %p')

    title_s  = ParagraphStyle('t', fontSize=15, fontName='Helvetica-Bold', textColor=navy, spaceAfter=2)
    meta_s   = ParagraphStyle('m', fontSize=9,  fontName='Helvetica', textColor=colors.HexColor('#6b7280'), spaceAfter=8)
    cart_s   = ParagraphStyle('c', fontSize=12, fontName='Helvetica-Bold', textColor=navy, spaceAfter=6)

    def build_section(cart_label, groups):
        elems = [
            Paragraph('CASE PICK LIST', title_s),
            Paragraph(f"{order.job_name or ''}{' — ' + order.lot_number if order.lot_number else ''}  ·  W.O: {order.order_number}  ·  Picker: {session['user_name']}  ·  {now_str}", meta_s),
            Paragraph(f"▌ {cart_label}", cart_s),
        ]
        for g in groups:
            slots_str = '   '.join([f"#{s}" for s in g['slots']])
            data = [[g['location'], f"QTY: {len(g['slots'])}", g['part_name']], [slots_str, '', '']]
            t = Table(data, colWidths=[1.8*inch, 0.8*inch, 4.4*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), navy),
                ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
                ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE',   (0,0), (-1,0), 9),
                ('PADDING',    (0,0), (-1,0), 5),
                ('BACKGROUND', (0,1), (-1,1), light),
                ('FONTNAME',   (0,1), (-1,1), 'Helvetica'),
                ('FONTSIZE',   (0,1), (-1,1), 9),
                ('PADDING',    (0,1), (-1,1), 4),
                ('SPAN',       (0,1), (-1,1)),
                ('BOX',        (0,0), (-1,-1), 0.5, border),
                ('LINEBELOW',  (0,0), (-1,0), 0.5, border),
            ]))
            elems += [t, Spacer(1, 0.05*inch)]
        return elems

    elements = []
    if cart_a:
        elements += build_section('CART A', cart_a)
    if cart_b:
        if cart_a:
            elements.append(PageBreak())
        elements += build_section('CART B', cart_b)

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"picklist_{order.order_number}.pdf"
    )