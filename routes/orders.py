from flask import Blueprint, render_template, session, redirect, url_for, request, abort, send_file
from extensions import db
from models import WorkOrder, OrderItem, PartTemplate, CabinetType, PickItem
from datetime import datetime, date
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')

def order_entry_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'order_entry', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None

@orders_bp.route('/')
def index():
    check = order_entry_required()
    if check:
        return check
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    query = WorkOrder.query
    if search:
        query = query.filter(
            db.or_(
                WorkOrder.order_number.ilike(f'%{search}%'),
                WorkOrder.job_name.ilike(f'%{search}%'),
                WorkOrder.lot_number.ilike(f'%{search}%'),
            )
        )
    if status_filter:
        query = query.filter_by(status=status_filter)
    from sqlalchemy import nullslast
    orders = query.order_by(nullslast(WorkOrder.scheduled_date.asc()), WorkOrder.created_at.asc()).all()
    return render_template('orders/index.html', orders=orders,
                           search=search, status_filter=status_filter)

@orders_bp.route('/create', methods=['GET', 'POST'])
def create():
    check = order_entry_required()
    if check:
        return check
    cabinets = CabinetType.query.order_by(CabinetType.code).all()
    from models import WarehouseConfig, Color
    config = WarehouseConfig.query.first()
    colors = Color.query.order_by(Color.name).all()
    error = None
    if request.method == 'POST':
        order_number = request.form['order_number']
        lot_number = request.form.get('lot_number') or None
        existing = WorkOrder.query.filter_by(order_number=order_number).first()
        if existing:
            error = f'Order number {order_number} already exists.'
        elif lot_number and WorkOrder.query.filter_by(lot_number=lot_number).first():
            error = f'Batch "{lot_number}" already exists.'
        else:
            sched_raw = request.form.get('scheduled_date', '').strip()
            sched = datetime.strptime(sched_raw, '%Y-%m-%d').date() if sched_raw else None
            color_name = request.form.get('color_filter') or None
            color_obj = Color.query.filter_by(name=color_name).first() if color_name else None
            new_order = WorkOrder(
                order_number=order_number,
                job_name=request.form.get('job_name') or None,
                lot_number=lot_number,
                scheduled_date=sched,
                color_id=color_obj.id if color_obj else None,
                created_by=session['user_id'],
                status='pending'
            )
            db.session.add(new_order)
            db.session.flush()
            slots = request.form.getlist('cabinet_id')
            carts = request.form.getlist('cart')
            for i, cabinet_id in enumerate(slots):
                if cabinet_id:
                    item = OrderItem(
                        work_order_id=new_order.id,
                        cabinet_type_id=int(cabinet_id),
                        slot=i + 1,
                        cart=int(carts[i]) if carts[i] else 1
                    )
                    db.session.add(item)
            db.session.commit()
            return redirect(url_for('orders.index'))
    return render_template('orders/create.html', cabinets=cabinets, error=error, config=config, colors=colors)

@orders_bp.route('/<int:order_id>')
def view(order_id):
    check = order_entry_required()
    if check:
        return check
    order = WorkOrder.query.get(order_id)
    return render_template('orders/view.html', order=order)

@orders_bp.route('/<int:order_id>/edit', methods=['GET', 'POST'])
def edit(order_id):
    check = order_entry_required()
    if check:
        return check
    order = WorkOrder.query.get(order_id)
    if not order or order.status not in ['pending']:
        from flask import flash
        flash('Only pending orders can be edited.', 'error')
        return redirect(url_for('orders.index'))
    from models import WarehouseConfig, Color
    cabinets = CabinetType.query.order_by(CabinetType.code).all()
    config = WarehouseConfig.query.first()
    colors = Color.query.order_by(Color.name).all()
    error = None
    if request.method == 'POST':
        order.job_name = request.form.get('job_name') or None
        new_lot = request.form.get('lot_number') or None
        sched_raw = request.form.get('scheduled_date', '').strip()
        order.scheduled_date = datetime.strptime(sched_raw, '%Y-%m-%d').date() if sched_raw else None
        new_number = request.form['order_number']
        if new_number != order.order_number:
            if WorkOrder.query.filter_by(order_number=new_number).first():
                error = f'Order number {new_number} already exists.'
        if not error and new_lot and new_lot != order.lot_number:
            if WorkOrder.query.filter_by(lot_number=new_lot).first():
                error = f'Batch "{new_lot}" already exists.'
        if not error:
            order.order_number = new_number
            order.lot_number = new_lot
            color_name = request.form.get('color_filter') or None
            color_obj = Color.query.filter_by(name=color_name).first() if color_name else None
            order.color_id = color_obj.id if color_obj else order.color_id
            # reemplaza los items
            for item in order.items:
                PickItem.query.filter_by(order_item_id=item.id).delete()
            OrderItem.query.filter_by(work_order_id=order_id).delete()
            slots = request.form.getlist('cabinet_id')
            for i, cabinet_id in enumerate(slots):
                if cabinet_id:
                    db.session.add(OrderItem(
                        work_order_id=order.id,
                        cabinet_type_id=int(cabinet_id),
                        slot=i + 1,
                        cart=1
                    ))
            db.session.commit()
            return redirect(url_for('orders.index'))
    return render_template('orders/edit.html', order=order, cabinets=cabinets,
                           config=config, colors=colors, error=error)

@orders_bp.route('/<int:order_id>/cancel')
def cancel(order_id):
    check = order_entry_required()
    if check:
        return check
    order = WorkOrder.query.get(order_id)
    if order and order.status == 'pending':
        order.status = 'cancelled'
        db.session.commit()
    return redirect(url_for('orders.index'))

@orders_bp.route('/<int:order_id>/delete')
def delete(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] != 'admin':
        return redirect(url_for('dashboard'))
    order = WorkOrder.query.get(order_id)
    if order:
        for item in order.items:
            PickItem.query.filter_by(order_item_id=item.id).delete()
        OrderItem.query.filter_by(work_order_id=order_id).delete()
        db.session.delete(order)
        db.session.commit()
    return redirect(url_for('orders.index'))

# 📄 Genera PDF genérico para cualquier orden
@orders_bp.route('/<int:order_id>/picklist/pdf')
def picklist_pdf(order_id):
    order = WorkOrder.query.get(order_id)
    if not order:
        abort(404)

    # Guardar PDF en memoria
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 12)

    y = 800
    c.drawString(50, y, f"Pick List for Order {order.order_number}")
    y -= 30

    for item in order.items:
        # Cabinet
        cabinet = CabinetType.query.get(item.cabinet_type_id)
        cabinet_name = cabinet.name if cabinet else f"ID {item.cabinet_type_id}"
        c.drawString(50, y, f"Cabinet: {cabinet_name} | Slot: {item.slot}")
        y -= 20

        # Picks
        for pick in item.picks:
            # Nombre de la pieza: usar pick.description o fallback a id
            part_name = getattr(pick, 'description', None) or f"PickItem ID {pick.id}"
            status = "Picked" if getattr(pick, 'is_picked', False) else "Missing" if getattr(pick, 'is_missing', False) else "Pending"
            c.drawString(70, y, f"- Part: {part_name} | Status: {status}")
            y -= 15

        y -= 10
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = 800

    c.save()
    buffer.seek(0)

    # Enviar al navegador
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"PickList_{order.order_number}.pdf",
        mimetype='application/pdf'
    )