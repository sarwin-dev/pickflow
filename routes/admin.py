import re
import json
import os
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from werkzeug.security import generate_password_hash
from extensions import db
from models import User, CabinetType, PartTemplate, Part, WarehouseConfig, Color, Inventory

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] != 'admin':
        return redirect(url_for('dashboard'))
    return None

@admin_bp.route('/')
def index():
    check = admin_required()
    if check:
        return check
    return render_template('admin/index.html')

# ============================================
# USERS
# ============================================

@admin_bp.route('/users')
def users():
    check = admin_required()
    if check:
        return check
    all_users = User.query.all()
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
def create_user():
    check = admin_required()
    if check:
        return check
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
def edit_user(user_id):
    check = admin_required()
    if check:
        return check
    user = User.query.get(user_id)
    if session['user_role'] == 'supervisor' and user.role == 'admin':
        return redirect(url_for('admin.users'))
    error = None
    if request.method == 'POST':
        user.name = ' '.join(request.form['name'].strip().split()).title()
        user.email = request.form['email']
        user.role = request.form['role']
        new_password = request.form.get('password')
        if new_password:
            user.password = generate_password_hash(new_password)
        db.session.commit()
        return redirect(url_for('admin.users'))
    return render_template('admin/edit_user.html', user=user, error=error)

@admin_bp.route('/users/delete/<int:user_id>')
def delete_user(user_id):
    check = admin_required()
    if check:
        return check
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin.users'))

# ============================================
# CABINET TYPES
# ============================================

@admin_bp.route('/cabinets')
def cabinets():
    check = admin_required()
    if check:
        return check
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
def create_cabinet():
    check = admin_required()
    if check:
        return check
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
def edit_cabinet(cabinet_id):
    check = admin_required()
    if check:
        return check
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
def cabinet_parts(cabinet_id):
    check = admin_required()
    if check:
        return check
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
def delete_cabinet(cabinet_id):
    check = admin_required()
    if check:
        return check
    cabinet = CabinetType.query.get(cabinet_id)
    if cabinet:
        db.session.delete(cabinet)
        db.session.commit()
    return redirect(url_for('admin.cabinets'))

@admin_bp.route('/cabinets/<int:cabinet_id>/parts/edit/<int:part_id>', methods=['POST'])
def edit_part(cabinet_id, part_id):
    check = admin_required()
    if check:
        return check
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
def delete_part(cabinet_id, part_id):
    check = admin_required()
    if check:
        return check
    template = PartTemplate.query.get(part_id)
    if template:
        db.session.delete(template)
        db.session.commit()
    return redirect(url_for('admin.cabinet_parts', cabinet_id=cabinet_id))

# ============================================
# WAREHOUSE CONFIG
# ============================================

@admin_bp.route('/warehouse', methods=['GET', 'POST'])
def warehouse_config():
    check = admin_required()
    if check:
        return check
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
def parts():
    check = admin_required()
    if check:
        return check
    all_parts = Part.query.order_by(Part.name).all()
    config = WarehouseConfig.query.first()
    return render_template('admin/parts.html', parts=all_parts, config=config)

@admin_bp.route('/parts/create', methods=['GET', 'POST'])
def create_part():
    check = admin_required()
    if check:
        return check
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
def edit_part_master(part_id):
    check = admin_required()
    if check:
        return check
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
def delete_part_master(part_id):
    check = admin_required()
    if check:
        return check
    part = Part.query.get(part_id)
    if part:
        db.session.delete(part)
        db.session.commit()
    return redirect(url_for('admin.parts'))

# ============================================
# COLORS
# ============================================

@admin_bp.route('/colors')
def colors():
    check = admin_required()
    if check:
        return check
    all_colors = Color.query.order_by(Color.name).all()
    return render_template('admin/colors.html', colors=all_colors)

@admin_bp.route('/colors/create', methods=['POST'])
def create_color():
    check = admin_required()
    if check:
        return check
    name = ' '.join(request.form['name'].strip().split()).title()
    hex_code = request.form.get('hex_code') or None
    existing = Color.query.filter(Color.name.ilike(name)).first()
    if not existing:
        new_color = Color(name=name, hex_code=hex_code)
        db.session.add(new_color)
        db.session.commit()
    return redirect(url_for('admin.colors'))

@admin_bp.route('/colors/delete/<int:color_id>')
def delete_color(color_id):
    check = admin_required()
    if check:
        return check
    color = Color.query.get(color_id)
    if color:
        db.session.delete(color)
        db.session.commit()
    return redirect(url_for('admin.colors'))

@admin_bp.route('/demo')
def demo():
    check = admin_required()
    if check:
        return check
    seed_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'demo_seed.json')
    has_seed = os.path.exists(seed_path)
    return render_template('admin/demo.html', has_seed=has_seed)


@admin_bp.route('/demo/reset', methods=['POST'])
def demo_reset():
    check = admin_required()
    if check:
        return jsonify({'error': 'unauthorized'}), 403

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
        cfg = seed['warehouse_config']
        if wc:
            wc.total_aisles    = cfg['total_aisles']
            wc.total_bays      = cfg['total_bays']
            wc.total_shelves   = cfg['total_shelves']
            wc.total_locations = cfg['total_locations']
            wc.active_shelves  = cfg['active_shelves']
        else:
            db.session.add(WarehouseConfig(**cfg))

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