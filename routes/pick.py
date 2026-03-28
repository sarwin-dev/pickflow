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
                    'loc': int(part.active_location) if part.active_location else 99,
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
        key=lambda x: (x['aisle'], x['bay'], x['shelf'], x['loc'])
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

    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    import io

    order = WorkOrder.query.get(order_id)

    # genera los grupos igual que en pick_order
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

            if loc_key not in location_groups:
                location_groups[loc_key] = {
                    'location': loc_key,
                    'part_name': part.name,
                    'aisle': int(part.active_aisle) if part.active_aisle else 99,
                    'bay': int(part.active_bay) if part.active_bay else 99,
                    'shelf': int(part.active_shelf) if part.active_shelf else 99,
                    'loc': int(part.active_location) if part.active_location else 99,
                    'slots': []
                }
            location_groups[loc_key]['slots'].append(item.slot)

    sorted_groups = sorted(
        location_groups.values(),
        key=lambda x: (x['aisle'], x['bay'], x['shelf'], x['loc'])
    )

    # crea el PDF en memoria
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)

    styles = getSampleStyleSheet()
    elements = []

    # header del documento
    title_style = ParagraphStyle('title',
        fontSize=16, fontName='Helvetica-Bold', spaceAfter=4)
    subtitle_style = ParagraphStyle('subtitle',
        fontSize=11, fontName='Helvetica', spaceAfter=2)
    small_style = ParagraphStyle('small',
        fontSize=9, fontName='Helvetica', textColor=colors.grey)

    elements.append(Paragraph('CASE PICK LIST', title_style))
    elements.append(Paragraph(
        f"{order.job_name or ''} — {order.lot_number or ''}", subtitle_style))
    elements.append(Paragraph(f"W.O: {order.order_number}", subtitle_style))
    elements.append(Paragraph(
        f"Picker: {session['user_name']} · {__import__('datetime').datetime.now().strftime('%m/%d/%Y %I:%M %p')}",
        small_style))
    elements.append(Spacer(1, 0.2*inch))

    # tabla de partes
    for group in sorted_groups:
        slots_text = '  '.join([f"#{s}" for s in group['slots']])
        data = [
            [group['location'], f"QTY: {len(group['slots'])}", group['part_name']],
            [slots_text, '', ''],
        ]
        t = Table(data, colWidths=[1.8*inch, 0.8*inch, 4.4*inch])
        t.setStyle(TableStyle([
            # header row
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e1b4b')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('PADDING', (0,0), (-1,0), 5),
            # slots row
            ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#f9fafb')),
            ('FONTNAME', (0,1), (-1,1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,1), 9),
            ('PADDING', (0,1), (-1,1), 4),
            ('SPAN', (0,1), (-1,1)),
            # bordes
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
            ('LINEBELOW', (0,0), (-1,0), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.05*inch))

    doc.build(elements)
    buffer.seek(0)

    from flask import send_file
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"picklist_{order.order_number}.pdf"
    )