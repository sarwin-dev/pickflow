import re
import json
import os
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from werkzeug.security import generate_password_hash
from extensions import db
from models import User, CabinetType, PartTemplate, Part, WarehouseConfig, Color, Inventory, ShoppingListItem, Loss, WorkOrder, OrderItem, PickItem
from routes.auth import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_required
def index():
    return render_template('admin/index.html')

# ============================================
# USERS
# ============================================

@admin_bp.route('/users')
@admin_required
def users():
    all_users = User.query.all()
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    error = None
    if request.method == 'POST':
        name = ' '.join(request.form['name'].strip().split()).title()
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        existing = User.query.filter_by(email=email).first()
        if existing:
            error = 'A user with that email already exists'
        else:
            new_user = User(
                name=name,
                email=email,
                password=generate_password_hash(password),
                role=role
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('admin.users'))
    return render_template('admin/create_user.html', error=error)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get(user_id)
    if session['user_role'] == 'supervisor' and user.role == 'admin':
        return redirect(url_for('admin.users'))
    error = None
    if request.method == 'POST':
        user.name = ' '.join(request.form['name'].strip().split()).title()
        user.email = request.form['email']
        if user.role != 'admin':
            user.role = request.form['role']
        new_password = request.form.get('password')
        if new_password:
            user.password = generate_password_hash(new_password)
        db.session.commit()
        return redirect(url_for('admin.users'))
    return render_template('admin/edit_user.html', user=user, error=error)

@admin_bp.route('/users/delete/<int:user_id>')
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin.users'))

# ============================================
# CABINET TYPES
# ============================================

@admin_bp.route('/cabinets')
@admin_required
def cabinets():
    from sqlalchemy import case
    all_cabinets = CabinetType.query.order_by(
        CabinetType.color,
        case((CabinetType.height == None, 0), else_=1),
        CabinetType.height,
        CabinetType.width
    ).all()
    color_map = {c.name: c.hex_code for c in Color.query.all()}
    return render_template('admin/cabinets.html', cabinets=all_cabinets, color_map=color_map)

@admin_bp.route('/cabinets/create', methods=['GET', 'POST'])
@admin_required
def create_cabinet():
    error = None
    if request.method == 'POST':
        cabinet_code = request.form['code'].strip()
        cabinet_name = ' '.join(re.sub(r'([a-zA-Z])(\d)', r'\1 \2', request.form['name'].strip()).split()).title()
        cabinet_color = request.form.get('color') or None
        existing = CabinetType.query.filter(
            CabinetType.code == cabinet_code,
            CabinetType.color == cabinet_color
        ).first()
        if existing:
            error = f'Cabinet "{cabinet_code}" with color "{cabinet_color or "No color"}" already exists.'
        else:
            new_cabinet = CabinetType(
                code=cabinet_code,
                name=cabinet_name,
                width=request.form['width'],
                height=request.form.get('height') or None,
                color=cabinet_color,
                is_custom=True if request.form.get('is_custom') else False
            )
            db.session.add(new_cabinet)
            db.session.commit()
            return redirect(url_for('admin.cabinet_parts', cabinet_id=new_cabinet.id))
    colors = Color.query.order_by(Color.name).all()
    return render_template('admin/create_cabinet.html', error=error, colors=colors)

@admin_bp.route('/cabinets/edit/<int:cabinet_id>', methods=['GET', 'POST'])
@admin_required
def edit_cabinet(cabinet_id):
    cabinet = CabinetType.query.get(cabinet_id)
    if request.method == 'POST':
        cabinet.code = request.form['code'].strip()
        cabinet.name = ' '.join(re.sub(r'([a-zA-Z])(\d)', r'\1 \2', request.form['name'].strip()).split()).title()
        cabinet.width = request.form['width']
        cabinet.height = request.form.get('height') or None
        cabinet.color = request.form.get('color') or None
        cabinet.is_custom = True if request.form.get('is_custom') else False
        db.session.commit()
        return redirect(url_for('admin.cabinets'))
    colors = Color.query.order_by(Color.name).all()
    return render_template('admin/edit_cabinet.html', cabinet=cabinet, colors=colors)

@admin_bp.route('/cabinets/<int:cabinet_id>/parts', methods=['GET', 'POST'])
@admin_required
def cabinet_parts(cabinet_id):
    cabinet = CabinetType.query.get(cabinet_id)
    config = WarehouseConfig.query.first()
    if request.method == 'POST':
        selected_ids = request.form.getlist('part_ids')
        for part_id in selected_ids:
            existing = PartTemplate.query.filter_by(cabinet_type_id=cabinet_id, part_id=part_id).first()
            if not existing:
                quantity = request.form.get(f'quantity_{part_id}', 1)
                cart = request.form.get(f'cart_{part_id}', 1)
                is_optional = False
                db.session.add(PartTemplate(
                    cabinet_type_id=cabinet_id,
                    part_id=int(part_id),
                    quantity=int(quantity),
                    cart=int(cart),
                    is_optional=is_optional,
                ))
        db.session.commit()
        return redirect(url_for('admin.cabinet_parts', cabinet_id=cabinet_id))
    from sqlalchemy import cast, Integer, nullslast
    templates = PartTemplate.query.join(Part).filter(
        PartTemplate.cabinet_type_id == cabinet_id
    ).order_by(
        nullslast(cast(Part.active_aisle, Integer)),
        nullslast(cast(Part.active_bay, Integer)),
        nullslast(cast(Part.active_shelf, Integer)),
        nullslast(cast(Part.active_location, Integer))
    ).all()
    used_part_ids = {t.part_id for t in templates}
    all_parts = Part.query.filter(Part.id.notin_(used_part_ids)).order_by(Part.name).all()
    if cabinet.color:
        available_parts = [p for p in all_parts if not any(p.name.endswith(c.name) for c in Color.query.all()) or p.name.endswith(cabinet.color)]
    else:
        available_parts = all_parts
    return render_template('admin/cabinet_parts.html',
                           cabinet=cabinet,
                           parts=templates,
                           available_parts=available_parts,
                           config=config)

@admin_bp.route('/cabinets/delete/<int:cabinet_id>')
@admin_required
def delete_cabinet(cabinet_id):
    cabinet = CabinetType.query.get(cabinet_id)
    if cabinet:
        db.session.delete(cabinet)
        db.session.commit()
    return redirect(url_for('admin.cabinets'))

@admin_bp.route('/cabinets/<int:cabinet_id>/annual-qty', methods=['POST'])
@admin_required
def set_annual_qty(cabinet_id):
    cabinet = CabinetType.query.get_or_404(cabinet_id)
    try:
        cabinet.annual_qty = max(0, int(request.json.get('annual_qty', 0)))
        db.session.commit()
        return jsonify({'success': True, 'annual_qty': cabinet.annual_qty})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@admin_bp.route('/cabinets/<int:cabinet_id>/parts/edit/<int:part_id>', methods=['POST'])
@admin_required
def edit_part(cabinet_id, part_id):
    template = PartTemplate.query.get(part_id)
    if template:
        template.quantity = int(request.form['quantity'])
        template.cart = int(request.form['cart'])
        template.is_optional = True if request.form.get('is_optional') else False
        part = template.part
        part.active_aisle = request.form.get('active_aisle') or None
        part.active_bay = request.form.get('active_bay') or None
        part.active_shelf = request.form.get('active_shelf') or None
        part.active_location = request.form.get('active_location') or None
        db.session.commit()
    return redirect(url_for('admin.cabinet_parts', cabinet_id=cabinet_id))

@admin_bp.route('/cabinets/<int:cabinet_id>/parts/delete/<int:part_id>')
@admin_required
def delete_part(cabinet_id, part_id):
    template = PartTemplate.query.get(part_id)
    if template:
        db.session.delete(template)
        db.session.commit()
    return redirect(url_for('admin.cabinet_parts', cabinet_id=cabinet_id))

# ============================================
# WAREHOUSE CONFIG
# ============================================

@admin_bp.route('/warehouse', methods=['GET', 'POST'])
@admin_required
def warehouse_config():
    config = WarehouseConfig.query.first()
    if request.method == 'POST':
        config.name = request.form['name']
        config.total_aisles = int(request.form['total_aisles'])
        config.total_bays = int(request.form['total_bays'])
        config.total_shelves = int(request.form['total_shelves'])
        config.total_locations = int(request.form['total_locations'])
        config.active_shelves = int(request.form['active_shelves'])
        config.max_cart_slots = int(request.form.get('max_cart_slots', 24))
        config.label_aisle = request.form.get('label_aisle', 'Aisle')
        config.label_bay = request.form.get('label_bay', 'Bay')
        config.label_shelf = request.form.get('label_shelf', 'Shelf')
        config.label_location = request.form.get('label_location', 'Location')
        config.prefix_aisle = request.form.get('prefix_aisle', 'A')
        config.prefix_bay = request.form.get('prefix_bay', 'B')
        config.prefix_shelf = request.form.get('prefix_shelf', 'S')
        config.prefix_location = request.form.get('prefix_location', 'L')
        from datetime import datetime
        config.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('admin.warehouse_config'))
    return render_template('admin/warehouse_config.html', config=config)

# ============================================
# PARTS MASTER
# ============================================

@admin_bp.route('/parts')
@admin_required
def parts():
    all_parts = Part.query.order_by(Part.name).all()
    config = WarehouseConfig.query.first()
    return render_template('admin/parts.html', parts=all_parts, config=config)

@admin_bp.route('/parts/create', methods=['GET', 'POST'])
@admin_required
def create_part():
    error = None
    if request.method == 'POST':
        raw = request.form['name'].strip()
        base_name = ' '.join(re.sub(r'([a-zA-Z])(\d)', r'\1 \2', raw).split()).title()
        color = request.form.get('color', '').strip()
        name = f'{base_name} {color}'.strip() if color else base_name
        aisle = request.form.get('active_aisle') or None
        bay = request.form.get('active_bay') or None
        shelf = request.form.get('active_shelf') or None
        location = request.form.get('active_location') or None
        existing_name = Part.query.filter(Part.name.ilike(name)).first()
        existing_loc = Part.query.filter_by(
            active_aisle=aisle, active_bay=bay,
            active_shelf=shelf, active_location=location
        ).first() if aisle and bay and shelf else None
        if existing_name:
            error = f'A part named "{name}" already exists'
        elif existing_loc:
            error = f'Location already used by "{existing_loc.name}"'
        else:
            new_part = Part(
                name=name,
                active_aisle=aisle,
                active_bay=bay,
                active_shelf=shelf,
                active_location=location,
            )
            db.session.add(new_part)
            db.session.commit()
            return redirect(url_for('admin.parts'))
    config = WarehouseConfig.query.first()
    colors = Color.query.order_by(Color.name).all()
    return render_template('admin/create_part.html', error=error, config=config, colors=colors)

@admin_bp.route('/parts/edit/<int:part_id>', methods=['POST'])
@admin_required
def edit_part_master(part_id):
    part = Part.query.get(part_id)
    if part:
        aisle = request.form.get('active_aisle') or None
        bay = request.form.get('active_bay') or None
        shelf = request.form.get('active_shelf') or None
        location = request.form.get('active_location') or None
        conflict = Part.query.filter(
            Part.id != part_id,
            Part.active_aisle == aisle,
            Part.active_bay == bay,
            Part.active_shelf == shelf,
            Part.active_location == location
        ).first() if aisle and bay and shelf else None
        if conflict:
            from flask import flash
            flash(f'Location already used by "{conflict.name}"', 'error')
            return redirect(url_for('admin.parts'))
        part.name = ' '.join(re.sub(r'([a-zA-Z])(\d)', r'\1 \2', request.form['name'].strip()).split()).title()
        part.active_aisle = aisle
        part.active_bay = bay
        part.active_shelf = shelf
        part.active_location = location
        db.session.commit()
    return redirect(url_for('admin.parts'))

@admin_bp.route('/parts/delete/<int:part_id>')
@admin_required
def delete_part_master(part_id):
    part = Part.query.get(part_id)
    if part:
        db.session.delete(part)
        db.session.commit()
    return redirect(url_for('admin.parts'))

# ============================================
# COLORS
# ============================================

@admin_bp.route('/colors')
@admin_required
def colors():
    all_colors = Color.query.order_by(Color.name).all()
    return render_template('admin/colors.html', colors=all_colors)

@admin_bp.route('/colors/create', methods=['POST'])
@admin_required
def create_color():
    name = ' '.join(request.form['name'].strip().split()).title()
    hex_code = request.form.get('hex_code') or None
    existing = Color.query.filter(Color.name.ilike(name)).first()
    if not existing:
        new_color = Color(name=name, hex_code=hex_code)
        db.session.add(new_color)
        db.session.commit()
    return redirect(url_for('admin.colors'))

@admin_bp.route('/colors/delete/<int:color_id>')
@admin_required
def delete_color(color_id):
    color = Color.query.get(color_id)
    if color:
        db.session.delete(color)
        db.session.commit()
    return redirect(url_for('admin.colors'))

@admin_bp.route('/demo')
@admin_required
def demo():
    seed_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'demo_seed.json')
    has_seed = os.path.exists(seed_path)
    return render_template('admin/demo.html', has_seed=has_seed)


@admin_bp.route('/demo/clear-all', methods=['POST'])
@admin_required
def demo_clear_all():
    db.session.execute(db.text("""
        TRUNCATE TABLE pick_items, order_items, work_orders,
                       shopping_list, losses, inventory,
                       part_templates, parts, cabinet_types,
                       colors, warehouse_config
        RESTART IDENTITY CASCADE
    """))
    db.session.execute(db.text("DELETE FROM users WHERE id != :admin_id"), {"admin_id": session['user_id']})
    db.session.commit()
    return jsonify({'ok': True})


@admin_bp.route('/demo/reset', methods=['POST'])
@admin_required
def demo_reset():
    seed_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'demo_seed.json')
    if not os.path.exists(seed_path):
        return jsonify({'error': 'demo_seed.json not found. Run export_demo_seed.py first.'}), 400

    with open(seed_path) as f:
        seed = json.load(f)

    # Limpiar en orden (foreign keys)
    Inventory.query.delete()
    PartTemplate.query.delete()
    Part.query.delete()
    CabinetType.query.delete()
    Color.query.delete()
    db.session.commit()

    # Restaurar Colors
    for c in seed['colors']:
        db.session.add(Color(name=c['name'], hex_code=c.get('hex_code')))
    db.session.flush()

    # Restaurar Parts
    part_map = {}
    for p in seed['parts']:
        obj = Part(
            name=p['name'], is_shared=p['is_shared'],
            active_aisle=p.get('active_aisle'), active_bay=p.get('active_bay'),
            active_shelf=p.get('active_shelf'), active_location=p.get('active_location'),
        )
        db.session.add(obj)
        db.session.flush()
        part_map[p['name']] = obj.id

    # Restaurar CabinetTypes + PartTemplates
    for ct in seed['cabinet_types']:
        obj = CabinetType(
            code=ct['code'], name=ct['name'],
            width=ct['width'], height=ct.get('height'),
            color=ct.get('color'), is_custom=ct.get('is_custom', False),
        )
        db.session.add(obj)
        db.session.flush()
        for pt in ct.get('part_templates', []):
            part_id = part_map.get(pt['part_name'])
            if part_id:
                db.session.add(PartTemplate(
                    cabinet_type_id=obj.id, part_id=part_id,
                    quantity=pt['quantity'], cart=pt['cart'],
                    is_optional=pt.get('is_optional', False),
                ))

    # Restaurar Warehouse Config
    if seed.get('warehouse_config'):
        from models import WarehouseConfig
        wc = WarehouseConfig.query.first()
        if not wc:
            cfg = seed['warehouse_config']
            db.session.add(WarehouseConfig(
                name=cfg.get('name', 'My Warehouse'),
                total_aisles=cfg['total_aisles'], total_bays=cfg['total_bays'],
                total_shelves=cfg['total_shelves'], total_locations=cfg['total_locations'],
                active_shelves=cfg['active_shelves'], max_cart_slots=cfg.get('max_cart_slots', 24),
                label_aisle=cfg.get('label_aisle', 'Aisle'), label_bay=cfg.get('label_bay', 'Bay'),
                label_shelf=cfg.get('label_shelf', 'Shelf'), label_location=cfg.get('label_location', 'Location'),
                prefix_aisle=cfg.get('prefix_aisle', 'A'), prefix_bay=cfg.get('prefix_bay', 'B'),
                prefix_shelf=cfg.get('prefix_shelf', 'S'), prefix_location=cfg.get('prefix_location', 'L'),
            ))

    # Restaurar registros activos
    active_count = 0
    for r in seed.get('active_inventory', []):
        part_id = part_map.get(r['part_name'])
        if part_id:
            db.session.add(Inventory(
                part_id=part_id,
                aisle=r['aisle'], bay=r['bay'],
                shelf=r['shelf'], location=r['location'],
                quantity=r['quantity'],
                min_quantity=r.get('min_quantity', 100),
                is_active=True,
            ))
            active_count += 1

    db.session.commit()

    return jsonify({
        'colors': len(seed['colors']),
        'cabinet_types': len(seed['cabinet_types']),
        'parts': len(seed['parts']),
        'active_records': active_count,
    })



@admin_bp.route('/demo/generate-order', methods=['POST'])
@admin_required
def demo_generate_order():
    import random

    # Word pools for generating subdivision-style job names (Southern US style)
    nature  = ['Silver', 'Copper', 'Iron', 'Cedar', 'Oak', 'Maple', 'Pine',
               'Willow', 'Sage', 'Amber', 'Golden', 'Granite', 'Jasper',
               'Laurel', 'Timber', 'Aspen', 'Birch', 'Magnolia', 'Pecan',
               'Palmetto', 'Hickory', 'Sycamore', 'Chestnut', 'Cottonwood']
    terrain = ['Ridge', 'Canyon', 'Trail', 'Bluff', 'Brook', 'Creek', 'Valley',
               'Glen', 'Cove', 'Hollow', 'Meadow', 'Springs', 'Crossing',
               'Landing', 'Bend', 'Estates', 'Heights', 'Hills', 'Falls',
               'Branch', 'Preserve', 'Chase', 'Pointe', 'Reserve', 'Run']

    # Keep generating names until we find one not already used
    existing_names = {o.job_name for o in WorkOrder.query.with_entities(WorkOrder.job_name).all()}
    for _ in range(50):
        job_name = f"{random.choice(nature)} {random.choice(terrain)}"
        if job_name not in existing_names:
            break

    # Lot: 3-digit number (100–999)
    lot_number = str(random.randint(100, 999))

    # Order number: "XXX.Y" — unique, Y is 0–9
    existing_orders = {o.order_number for o in WorkOrder.query.with_entities(WorkOrder.order_number).all()}
    for _ in range(200):
        order_number = f"{random.randint(100, 999)}.{random.randint(0, 9)}"
        if order_number not in existing_orders:
            break

    # Cap count at max_cart_slots so the edit page never overflows one cart
    from models import WarehouseConfig
    wc = WarehouseConfig.query.first()
    max_slots = wc.max_cart_slots if wc else 24

    # Build a map of color_name -> [cabinet_types] using only colors that actually have cabinets
    all_colors = Color.query.all()
    if not all_colors:
        return jsonify({'error': 'No colors found. Load demo data first.'}), 400

    color_cabinet_map = {}
    for c in all_colors:
        # Case-insensitive match to handle any capitalization differences in the DB
        cabs = CabinetType.query.filter(
            db.func.lower(CabinetType.color) == c.name.lower()
        ).all()
        if cabs:
            color_cabinet_map[c] = cabs

    if not color_cabinet_map:
        return jsonify({'error': 'No cabinet types with color assigned. Load demo data first.'}), 400

    # Pick a random color that actually has cabinets
    color = random.choice(list(color_cabinet_map.keys()))
    cabinets = color_cabinet_map[color]

    count = random.randint(min(8, max_slots), max_slots)
    chosen = random.choices(cabinets, k=count)

    # Get the admin user to assign as creator
    admin_user = User.query.filter_by(role='admin').first()

    wo = WorkOrder(
        order_number=order_number,
        job_name=job_name,
        lot_number=lot_number,
        color_id=color.id,
        status='pending',
        created_by=admin_user.id,
    )
    db.session.add(wo)
    db.session.flush()

    # All items on cart 1, sequential slots — count is already capped at max_slots above
    for slot, cabinet in enumerate(chosen, 1):
        db.session.add(OrderItem(
            work_order_id=wo.id,
            cabinet_type_id=cabinet.id,
            slot=slot,
            cart=1,
        ))

    db.session.commit()
    return jsonify({
        'success': True,
        'order_number': order_number,
        'job_name': job_name,
        'lot_number': lot_number,
        'color': color.name,
        'cabinets': count,
    })


@admin_bp.route('/demo/clear-orders', methods=['POST'])
def demo_clear_orders():
    # Verifica permisos (sin usar admin_required que usa redirect)
    if 'user_id' not in session or session['user_role'] != 'admin':
        return jsonify({'error': 'unauthorized'}), 403

    try:
        # Primero borra todos los PickItem (porque dependen de OrderItem)
        db.session.query(PickItem).delete()
        # Luego borra todos los OrderItem (porque dependen de WorkOrder)
        db.session.query(OrderItem).delete()
        # Finalmente borra todas las órdenes de trabajo
        deleted = db.session.query(WorkOrder).delete()
        db.session.commit()

        return jsonify({
            'success': True,
            'deleted': deleted,
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500

@admin_bp.route('/demo/simulate-orders', methods=['POST'])
def demo_simulate_orders():
    if 'user_id' not in session or session['user_role'] != 'admin':
        return jsonify({'error': 'unauthorized'}), 403

    import random
    from datetime import datetime, timedelta

    data = request.get_json()
    months = int(data.get('months', 1))
    if months < 1 or months > 12:
        return jsonify({'error': 'Months must be 1-12'}), 400

    config = WarehouseConfig.query.first()
    if not config:
        return jsonify({'error': 'Warehouse not configured'}), 400

    cabinets = CabinetType.query.filter(CabinetType.annual_qty > 0).all()
    if not cabinets:
        return jsonify({'error': 'No cabinet types with annual_qty set'}), 400

    colors = Color.query.all()
    if not colors:
        return jsonify({'error': 'No colors configured'}), 400

    # Calcula órdenes proyectadas en el período
    total_units_year = sum(c.annual_qty or 0 for c in cabinets)
    orders_this_period = max(1, int(total_units_year * (months / 12) / 4))  # ~4 units per order avg

    # Distribuye órdenes en los N meses
    order_dates = []
    now = datetime.utcnow()
    for _ in range(orders_this_period):
        random_days_back = random.randint(0, max(1, months * 30 - 1))
        date = now - timedelta(days=random_days_back)
        order_dates.append(date)

    total_parts_consumed = 0
    orders_created = 0

    try:
        # Limpia órdenes simuladas previas
        simulated_orders = WorkOrder.query.filter(WorkOrder.order_number.like('SIM-%')).all()
        for order in simulated_orders:
            # Borra PickItems primero
            for item in order.items:
                PickItem.query.filter_by(order_item_id=item.id).delete()
            # Borra OrderItems
            OrderItem.query.filter_by(work_order_id=order.id).delete()
        # Borra WorkOrders
        WorkOrder.query.filter(WorkOrder.order_number.like('SIM-%')).delete()
        db.session.flush()

        for order_date in order_dates:
            # Genera nombre único para orden simulada
            order_number = f"SIM-{order_date.strftime('%Y%m%d')}-{random.randint(10000, 99999)}"
            job_name = f"Simulated-{order_date.strftime('%m%d')}-{random.randint(100, 999)}"
            color = random.choice(colors)

            # Selecciona N cabinet types para esta orden (1-3 por orden)
            num_cabinets = random.randint(1, min(3, len(cabinets)))
            selected_cabinets = random.sample(cabinets, num_cabinets)

            order = WorkOrder(
                order_number=order_number,
                job_name=job_name,
                color_id=color.id,
                status='completed',
                created_by=session.get('user_id', 1),
                created_at=order_date,
                updated_at=order_date,
                is_simulated=False
            )
            db.session.add(order)
            db.session.flush()

            # Agrega cabinet types como items y consume partes
            for slot, cabinet in enumerate(selected_cabinets, 1):
                item = OrderItem(
                    work_order_id=order.id,
                    cabinet_type_id=cabinet.id,
                    slot=slot,
                    cart=1
                )
                db.session.add(item)
                db.session.flush()

                # Consume partes del inventario
                for part_template in cabinet.parts:
                    qty_to_consume = part_template.quantity
                    total_parts_consumed += qty_to_consume

                    # Resta del inventario overflow
                    overflow_records = Inventory.query.filter(
                        Inventory.part_id == part_template.part_id,
                        Inventory.is_active == False,
                        Inventory.quantity > 0
                    ).order_by(Inventory.id).all()

                    for record in overflow_records:
                        if qty_to_consume <= 0:
                            break
                        consume = min(qty_to_consume, record.quantity)
                        record.quantity -= consume
                        qty_to_consume -= consume

            orders_created += 1

        db.session.commit()
        return jsonify({
            'success': True,
            'orders_created': orders_created,
            'total_parts_consumed': total_parts_consumed
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/demo/clear-simulated-orders', methods=['POST'])
def demo_clear_simulated_orders():
    if 'user_id' not in session or session['user_role'] != 'admin':
        return jsonify({'error': 'unauthorized'}), 403

    try:
        # Busca órdenes simuladas
        simulated = WorkOrder.query.filter(WorkOrder.order_number.like('SIM-%')).all()
        count = len(simulated)

        for order in simulated:
            # Elimina picks de los items
            PickItem.query.filter(
                PickItem.order_item_id.in_(
                    db.session.query(OrderItem.id).filter_by(work_order_id=order.id)
                )
            ).delete()
            # Elimina items
            OrderItem.query.filter_by(work_order_id=order.id).delete()
            # Elimina orden
            db.session.delete(order)

        db.session.commit()
        return jsonify({
            'success': True,
            'orders_deleted': count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/demo/production-plan')
@admin_required
def production_plan():
    cabinets = CabinetType.query.order_by(CabinetType.name).all()
    months = 4
    for cabinet in cabinets:
        if cabinet.annual_qty:
            total_parts = sum(t.quantity for t in cabinet.parts)
            cabinet.projected_consumption = round(cabinet.annual_qty * (months / 12) * total_parts)
        else:
            cabinet.projected_consumption = 0
    return render_template('admin/production_plan.html', cabinets=cabinets, months=months)


@admin_bp.route('/demo/production-plan/update', methods=['POST'])
@admin_required
def update_annual_qty():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    updated = 0
    for cabinet_id_str, qty in data.items():
        try:
            cabinet_id = int(cabinet_id_str)
            cabinet = CabinetType.query.get(cabinet_id)
            if cabinet:
                cabinet.annual_qty = max(0, int(qty))
                updated += 1
        except (ValueError, TypeError):
            continue
    db.session.commit()
    return jsonify({'success': True, 'updated': updated})


@admin_bp.route('/setup-wizard', methods=['POST'])
@admin_required
def setup_wizard():
    data = request.get_json() or {}
    name = (data.get('company_name') or '').strip() or None

    try:
        total_aisles = int(data.get('total_aisles', 6))
        total_bays = int(data.get('total_bays', 35))
        total_shelves = int(data.get('total_shelves', 6))
        active_shelves = int(data.get('active_shelves', 2))
        total_locations = int(data.get('total_locations', 4))

        warehouse_config = WarehouseConfig.query.first()

        if warehouse_config:
            warehouse_config.name = name
            warehouse_config.total_aisles = total_aisles
            warehouse_config.total_bays = total_bays
            warehouse_config.total_shelves = total_shelves
            warehouse_config.active_shelves = active_shelves
            warehouse_config.total_locations = total_locations
        else:
            warehouse_config = WarehouseConfig(
                name=name,
                total_aisles=total_aisles,
                total_bays=total_bays,
                total_shelves=total_shelves,
                active_shelves=active_shelves,
                total_locations=total_locations
            )
            db.session.add(warehouse_config)

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
