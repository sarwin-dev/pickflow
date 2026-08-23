import re
import random
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from extensions import db
from models import Inventory, WarehouseConfig, Part, ReceivingLog
from datetime import datetime
from routes.inventory import build_part_item

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
    if not config:
        flash('Warehouse is not configured yet. Load demo data or set up the warehouse first.', 'error')
        return redirect(url_for('dashboard'))
    parts = Part.query.order_by(Part.name).all()
    pending = session.get('pending_receive')
    records = ReceivingLog.query.order_by(ReceivingLog.received_at.asc()).limit(50).all()
    return render_template('receiving/index.html',
                           config=config,
                           parts=parts,
                           pending=pending,
                           records=records)

@receiving_bp.route('/receive', methods=['POST'])
def receive():
    check = warehouse_required()
    if check:
        return check

    # Requiere part_id (seleccionado del autocomplete — no acepta part_name)
    part_id = request.form.get('part_id')

    if not part_id:
        flash('Part not found. Please go to Admin → Parts to register it first.', 'error')
        return redirect(url_for('receiving.index'))

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
        stack_confirmed = request.form.get('stack_confirmed') == '1'

        # overflow siempre es overflow, independientemente del numero de shelf
        is_active = False

        # valida que el shelf este en el rango de overflow
        if shelf < 1 or shelf <= config.active_shelves:
            flash(
                f'Shelf {shelf} is an active (pick) shelf. '
                f'Overflow boxes must go to shelves {config.active_shelves + 1}–{config.total_shelves}. '
                f'Use "Direct to Active" if this box goes straight to the pick shelf.',
                'error'
            )
            return redirect(url_for('receiving.index'))
        if shelf > config.total_shelves:
            flash(
                f'Shelf {shelf} does not exist. This warehouse has {config.total_shelves} shelves total '
                f'({config.active_shelves} active, {config.total_shelves - config.active_shelves} overflow).',
                'error'
            )
            return redirect(url_for('receiving.index'))

        # Verifica que la ubicación no esté ocupada por una parte diferente
        conflict = Inventory.query.filter(
            Inventory.aisle == aisle,
            Inventory.bay == bay,
            Inventory.shelf == str(shelf),
            Inventory.location == location,
            Inventory.part_id != int(part_id)
        ).first()
        if conflict:
            flash(
                f'This location is already in use by "{conflict.part.name}" '
                f'({conflict.quantity} units). Please choose a different location.',
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

    # escribe en el log historico (se purga a los 7 dias)
    log_aisle = aisle if receiving_type != 'direct' else part.active_aisle
    log_bay   = bay   if receiving_type != 'direct' else part.active_bay
    log_shelf = str(shelf) if receiving_type != 'direct' else part.active_shelf
    log_loc   = location  if receiving_type != 'direct' else part.active_location
    db.session.add(ReceivingLog(
        part_id=int(part_id),
        quantity=quantity,
        aisle=log_aisle,
        bay=log_bay,
        shelf=log_shelf,
        location=log_loc,
        is_active=(receiving_type == 'direct'),
        received_by=session.get('user_id'),
    ))
    db.session.commit()
    session.pop('pending_receive', None)
    return redirect(url_for('receiving.index'))

@receiving_bp.route('/pulldown/<int:record_id>', methods=['POST'])
def pulldown(record_id):
    check = warehouse_required()
    if check:
        return check
    record = Inventory.query.get(record_id)
    if not record:
        next_url = request.form.get('next') or url_for('receiving.index')
        return redirect(next_url)

    part = Part.query.get(record.part_id)

    if part and part.active_aisle:
        # obtiene la cantidad de la caja de overflow que se va a bajar
        overflow_quantity = record.quantity

        # busca el registro en la active location (siempre existe para esta parte)
        active_record = Inventory.query.filter_by(
            part_id=part.id,
            aisle=part.active_aisle,
            bay=part.active_bay,
            shelf=part.active_shelf,
            location=part.active_location,
            is_active=True
        ).first()

        if active_record:
            # actualiza la cantidad en la active location (reemplaza o suma)
            active_record.quantity = overflow_quantity
            active_record.updated_at = datetime.utcnow()
        else:
            # crea un nuevo registro en la active location (en caso de que no exista)
            active_record = Inventory(
                part_id=part.id,
                aisle=part.active_aisle,
                bay=part.active_bay,
                shelf=part.active_shelf,
                location=part.active_location,
                quantity=overflow_quantity,
                is_active=True,
                received_at=datetime.utcnow()
            )
            db.session.add(active_record)

        # borra el registro de overflow (ya no existe esa caja en esa ubicación)
        db.session.delete(record)

        # desactiva is_on_hold si estaba marcada
        if part.is_on_hold:
            part.is_on_hold = False

        db.session.commit()
        if request.headers.get('HX-Request'):
            item = build_part_item(part)
            return render_template('inventory/partials/part_card.html', item=item,
                                   search='', filter_mode='')
        flash(f'Box pulled down to active location A{part.active_aisle} B{part.active_bay} S{part.active_shelf}.', 'success')
    else:
        flash('Box cannot be pulled down. No active location defined for this part — set it in Admin > Parts.', 'error')

    next_url = request.form.get('next') or url_for('receiving.index')
    return redirect(next_url)


@receiving_bp.route('/demo-reset-min', methods=['POST'])
def demo_reset_min():
    check = warehouse_required()
    if check:
        return jsonify({'error': 'unauthorized'}), 403
    updated = Inventory.query.filter(Inventory.min_quantity != 100).update({'min_quantity': 100})
    db.session.commit()
    return jsonify({'updated': updated})


@receiving_bp.route('/demo-clear', methods=['POST'])
def demo_clear():
    check = warehouse_required()
    if check:
        return jsonify({'error': 'unauthorized'}), 403
    deleted = Inventory.query.filter_by(is_active=False).delete()
    db.session.commit()
    return jsonify({'deleted': deleted})


@receiving_bp.route('/demo-fill', methods=['POST'])
def demo_fill():
    check = warehouse_required()
    if check:
        return jsonify({'error': 'unauthorized'}), 403

    config = WarehouseConfig.query.first()
    if not config:
        return jsonify({'error': 'No warehouse config'}), 400

    parts = Part.query.all()
    if not parts:
        return jsonify({'error': 'No parts in system'}), 400

    # Ubicaciones libres en overflow
    occupied = set()
    for r in Inventory.query.filter_by(is_active=False).all():
        if r.aisle and r.bay and r.shelf:
            occupied.add((r.aisle, r.bay, r.shelf, r.location or ''))

    free_slots = []
    for aisle in range(1, config.total_aisles + 1):
        for bay in range(1, config.total_bays + 1):
            for shelf in range(config.active_shelves + 1, config.total_shelves + 1):
                if config.total_locations > 0:
                    for loc in range(1, config.total_locations + 1):
                        key = (str(aisle), str(bay), str(shelf), str(loc))
                        if key not in occupied:
                            free_slots.append((str(aisle), str(bay), str(shelf), str(loc)))
                else:
                    key = (str(aisle), str(bay), str(shelf), '')
                    if key not in occupied:
                        free_slots.append((str(aisle), str(bay), str(shelf), None))

    if not free_slots:
        return jsonify({'filled': 0, 'full': True})

    # Distribuir partes en round-robin shuffleado para que todas aparezcan
    random.shuffle(parts)
    part_cycle = (parts * (len(free_slots) // len(parts) + 1))[:len(free_slots)]
    random.shuffle(part_cycle)

    for (aisle, bay, shelf, loc), part in zip(free_slots, part_cycle):
        qty = random.choice([90, 100, 120])
        db.session.add(Inventory(
            part_id=part.id,
            aisle=aisle, bay=bay, shelf=shelf,
            location=loc,
            quantity=qty, is_active=False,
        ))

    db.session.commit()

    total_slots = config.total_aisles * config.total_bays * (config.total_shelves - config.active_shelves)
    if config.total_locations > 0:
        total_slots *= config.total_locations
    full = (len(occupied) + len(free_slots)) >= total_slots

    return jsonify({'filled': len(free_slots), 'full': full})