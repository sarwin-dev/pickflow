import re
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from extensions import db
from models import Inventory, WarehouseConfig, Part
from datetime import datetime

receiving_bp = Blueprint('receiving', __name__, url_prefix='/receiving')

def warehouse_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'warehouse', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None

@receiving_bp.route('/')
def index():
    check = warehouse_required()
    if check:
        return check
    config = WarehouseConfig.query.first()
    parts = Part.query.order_by(Part.name).all()
    pending = session.get('pending_receive')
    return render_template('receiving/index.html',
                           config=config,
                           parts=parts,
                           pending=pending)

@receiving_bp.route('/receive', methods=['POST'])
def receive():
    check = warehouse_required()
    if check:
        return check
    
    # acepta part_id (seleccion del autocomplete) o part_name (texto libre)
    part_id = request.form.get('part_id')
    part_name_raw = request.form.get('part_name', '').strip()

    if not part_id and not part_name_raw:
        return redirect(url_for('receiving.index'))

    if not part_id:
        # formatea el nombre: separa letras de numeros, title case
        formatted = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', part_name_raw)
        formatted = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', formatted)
        part_name = ' '.join(formatted.split()).title()
        # busca la parte o la crea si no existe
        part = Part.query.filter(Part.name.ilike(part_name)).first()
        if not part:
            part = Part(name=part_name)
            db.session.add(part)
            db.session.flush()
        part_id = part.id

    config = WarehouseConfig.query.first()
    quantity = int(request.form['quantity'])
    receiving_type = request.form.get('receiving_type', 'overflow')
    location = request.form.get('location') or None

    if receiving_type == 'direct':
        # busca la parte maestra para obtener su ubicacion activa
        part = Part.query.get(part_id)
        # busca si ya hay un registro activo para esta parte
        existing = Inventory.query.filter_by(
            part_id=part_id,
            is_active=True
        ).first()
        if existing:
            # suma la cantidad al registro activo existente
            existing.quantity += quantity
            existing.updated_at = datetime.utcnow()
        else:
            # crea nuevo registro activo con ubicacion de la parte maestra
            new_record = Inventory(
                part_id=part_id,
                aisle=part.active_aisle,
                bay=part.active_bay,
                shelf=part.active_shelf,
                location=part.active_location,
                quantity=quantity,
                is_active=True,
                received_at=datetime.utcnow()
            )
            db.session.add(new_record)
    else:
        # overflow normal - pide ubicacion nueva
        aisle = request.form.get('aisle')
        bay = request.form.get('bay')
        shelf = int(request.form.get('shelf', 0))
        is_active = shelf <= config.active_shelves
        stack_confirmed = request.form.get('stack_confirmed') == '1'

        # verifica que la ubicacion no este ocupada por una parte diferente
        conflict = Inventory.query.filter(
            Inventory.aisle == aisle,
            Inventory.bay == bay,
            Inventory.shelf == str(shelf),
            Inventory.location == location,
            Inventory.part_id != int(part_id)
        ).first()
        if conflict:
            flash(
                f'Location A{int(aisle):02d}.B{int(bay):02d}.S{int(shelf):02d} '
                f'is already occupied by "{conflict.part.name}". '
                f'Choose a different location or pull down the existing box first.',
                'error'
            )
            return redirect(url_for('receiving.index'))

        # verifica si ya hay una caja de la misma parte en esa ubicacion
        same_part_same_loc = Inventory.query.filter(
            Inventory.aisle == aisle,
            Inventory.bay == bay,
            Inventory.shelf == str(shelf),
            Inventory.location == location,
            Inventory.part_id == int(part_id)
        ).first()

        if same_part_same_loc and not stack_confirmed:
            loc_str = f"A{int(aisle):02d}.B{int(bay):02d}.S{int(shelf):02d}"
            if location:
                loc_str += f".L{int(location):02d}"
            # guarda los datos pendientes en sesion para el formulario de confirmacion
            session['pending_receive'] = {
                'part_id': str(part_id),
                'part_name': Part.query.get(int(part_id)).name,
                'quantity': quantity,
                'aisle': aisle,
                'bay': bay,
                'shelf': str(shelf),
                'location': location,
                'loc_str': loc_str,
                'existing_qty': same_part_same_loc.quantity,
            }
            return redirect(url_for('receiving.index'))

        # crea siempre un nuevo registro separado (cada caja tiene su propio pulldown)
        new_record = Inventory(
            part_id=part_id,
            aisle=aisle,
            bay=bay,
            shelf=str(shelf),
            location=location,
            quantity=quantity,
            is_active=is_active,
            received_at=datetime.utcnow()
        )
        db.session.add(new_record)
        session.pop('pending_receive', None)

    db.session.commit()
    return redirect(url_for('receiving.index'))

@receiving_bp.route('/pulldown/<int:record_id>', methods=['POST'])
def pulldown(record_id):
    check = warehouse_required()
    if check:
        return check
    record = Inventory.query.get(record_id)
    if record:
        db.session.delete(record)
        db.session.commit()
    next_url = request.form.get('next') or url_for('receiving.index')
    return redirect(next_url)