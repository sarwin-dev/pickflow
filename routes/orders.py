from flask import Blueprint, render_template, session, redirect, url_for, request
from extensions import db
from models import WorkOrder, OrderItem, PartTemplate, CabinetType, User, PickItem
from datetime import datetime

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')

def order_entry_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'order_entry', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None

# lista todas las ordenes
@orders_bp.route('/')
def index():
    check = order_entry_required()
    if check:
        return check
    orders = WorkOrder.query.order_by(WorkOrder.created_at.desc()).all()
    return render_template('orders/index.html', orders=orders)

# crea una orden nueva
@orders_bp.route('/create', methods=['GET', 'POST'])
def create():
    check = order_entry_required()
    if check:
        return check
    cabinets = CabinetType.query.order_by(CabinetType.code).all()
    # traemos config para el maximo de slots
    from models import WarehouseConfig
    config = WarehouseConfig.query.first()
    error = None
    if request.method == 'POST':
        order_number = request.form['order_number']
        # verifica que el numero de orden no exista
        existing = WorkOrder.query.filter_by(order_number=order_number).first()
        if existing:
            error = f'Order number {order_number} already exists'
        else:
            # crea la orden
            new_order = WorkOrder(
                order_number=order_number,
                job_name=request.form.get('job_name') or None,
                lot_number=request.form.get('lot_number') or None,
                created_by=session['user_id'],
                status='pending'
            )
            db.session.add(new_order)
            db.session.flush()
            # agrega los gabinetes a la orden
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
            return redirect(url_for('orders.view', order_id=new_order.id))
    return render_template('orders/create.html', 
                           cabinets=cabinets, 
                           error=error,
                           config=config)

# ve una orden especifica
@orders_bp.route('/<int:order_id>')
def view(order_id):
    check = order_entry_required()
    if check:
        return check
    order = WorkOrder.query.get(order_id)
    return render_template('orders/view.html', order=order)

# cancela una orden
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

# elimina una orden permanentemente - solo admin
@orders_bp.route('/<int:order_id>/delete')
def delete(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] != 'admin':
        return redirect(url_for('dashboard'))
    order = WorkOrder.query.get(order_id)
    if order:
        # borra primero los items relacionados
        for item in order.items:
            PickItem.query.filter_by(order_item_id=item.id).delete()
        OrderItem.query.filter_by(work_order_id=order_id).delete()
        db.session.delete(order)
        db.session.commit()
    return redirect(url_for('orders.index'))

# 📄 Genera PDF del pick list
from flask import send_file
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

@orders_bp.route('/<int:order_id>/picklist/pdf')
def picklist_pdf(order_id):
    order = WorkOrder.query.get(order_id)
    if not order:
        return "Order not found", 404

    # Crear PDF en memoria
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, f"Pick List for Order {order.order_number}")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 70, f"Job: {order.job_name or ''} | Lot: {order.lot_number or ''}")
    c.drawString(50, height - 90, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Y empezamos a listar los items
    y = height - 120
    for item in order.items:
        c.drawString(50, y, f"Cabinet: {item.cabinet_type.name} | Slot: {item.slot}")
        y -= 20
        if y < 50:  # nueva página
            c.showPage()
            y = height - 50

    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name=f"picklist_{order.order_number}.pdf",
                     mimetype='application/pdf')