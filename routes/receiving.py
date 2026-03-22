from flask import Blueprint, render_template, session, redirect, url_for, request
from extensions import db
from models import Inventory, PartTemplate, WarehouseConfig
from datetime import datetime

receiving_bp = Blueprint('receiving', __name__, url_prefix='/receiving')

def warehouse_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'warehouse', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None

# lista de recepciones recientes
@receiving_bp.route('/')
def index():
    check = warehouse_required()
    if check:
        return check
    # ultimas 50 recepciones ordenadas por fecha
    records = Inventory.query.order_by(
        Inventory.received_at.desc()
    ).limit(50).all()
    config = WarehouseConfig.query.first()
    parts = PartTemplate.query.order_by(PartTemplate.name).all()
    return render_template('receiving/index.html', 
                         records=records, 
                         config=config,
                         parts=parts)

# registra una caja nueva
@receiving_bp.route('/receive', methods=['POST'])
def receive():
    check = warehouse_required()
    if check:
        return check
    config = WarehouseConfig.query.first()
    part_id = request.form['part_id']
    quantity = int(request.form['quantity'])
    aisle = request.form.get('aisle')
    bay = request.form.get('bay')
    shelf = int(request.form.get('shelf', 0))
    location = request.form.get('location') or None
    # determina si es active o overflow segun el shelf
    is_active = shelf <= config.active_shelves
    new_record = Inventory(
        part_template_id=part_id,
        aisle=aisle,
        bay=bay,
        shelf=str(shelf),
        location=location,
        quantity=quantity,
        is_active=is_active,
        received_at=datetime.utcnow()
    )
    db.session.add(new_record)
    db.session.commit()
    return redirect(url_for('receiving.index'))

# descuenta unidades cuando se hace pulldown
@receiving_bp.route('/pulldown/<int:record_id>', methods=['POST'])
def pulldown(record_id):
    check = warehouse_required()
    if check:
        return check
    record = Inventory.query.get(record_id)
    quantity = int(request.form['quantity'])
    if record:
        record.quantity -= quantity
        record.updated_at = datetime.utcnow()
        if record.quantity <= 0:
            db.session.delete(record)
        db.session.commit()
    return redirect(url_for('receiving.index'))