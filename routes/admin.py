import re
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash
from extensions import db
from models import User, CabinetType, PartTemplate, Part, WarehouseConfig, Color

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
    all_cabinets = CabinetType.query.order_by(CabinetType.color, CabinetType.width).all()
    color_map = {c.name: c.hex_code for c in Color.query.all()}
    return render_template('admin/cabinets.html', cabinets=all_cabinets, color_map=color_map)

@admin_bp.route('/cabinets/create', methods=['GET', 'POST'])
def create_cabinet():
    check = admin_required()
    if check:
        return check
    error = None
    if request.method == 'POST':
        raw_code = request.form['code'].strip()
        formatted_code = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', raw_code)
        cabinet_code = ' '.join(formatted_code.split()).title()
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
                name=request.form['name'],
                width=request.form['width'],
                height=request.form.get('height') or None,
                color=cabinet_color,
                is_custom=True if request.form.get('is_custom') else False
            )
            db.session.add(new_cabinet)
            db.session.commit()
            return redirect(url_for('admin.cabinet_parts', cabinet_id=new_cabinet.id))
    from models import Color
    colors = Color.query.order_by(Color.name).all()
    return render_template('admin/create_cabinet.html', error=error, colors=colors)

@admin_bp.route('/cabinets/edit/<int:cabinet_id>', methods=['GET', 'POST'])
def edit_cabinet(cabinet_id):
    check = admin_required()
    if check:
        return check
    cabinet = CabinetType.query.get(cabinet_id)
    if request.method == 'POST':
        raw_code = request.form['code'].strip()
        formatted_code = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', raw_code)
        cabinet.code = ' '.join(formatted_code.split()).title()
        cabinet.name = ' '.join(request.form['name'].strip().split()).title()
        cabinet.width = request.form['width']
        cabinet.height = request.form.get('height') or None
        cabinet.color = request.form.get('color') or None
        cabinet.is_custom = True if request.form.get('is_custom') else False
        db.session.commit()
        return redirect(url_for('admin.cabinets'))
    from models import Color
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
        # normaliza el nombre - title case, separa letras de numeros y limpia espacios
        raw_name = request.form['name'].strip()
        formatted = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', raw_name)
        part_name = ' '.join(formatted.split()).title()
        # busca si la parte ya existe en la tabla maestra
        existing_part = Part.query.filter(Part.name.ilike(part_name)).first()
        if existing_part:
            part = existing_part
            if request.form.get('active_aisle'):
                part.active_aisle = request.form.get('active_aisle')
                part.active_bay = request.form.get('active_bay')
                part.active_shelf = request.form.get('active_shelf')
                part.active_location = request.form.get('active_location') or None
                db.session.commit()
        else:
            part = Part(
                name=part_name,
                is_shared=True if request.form.get('is_shared') else False,
                active_aisle=request.form.get('active_aisle') or None,
                active_bay=request.form.get('active_bay') or None,
                active_shelf=request.form.get('active_shelf') or None,
                active_location=request.form.get('active_location') or None,
            )
            db.session.add(part)
            db.session.flush()
        new_template = PartTemplate(
            cabinet_type_id=cabinet_id,
            part_id=part.id,
            quantity=request.form['quantity'],
            cart=request.form['cart'],
            is_optional=True if request.form.get('is_optional') else False,
        )
        db.session.add(new_template)
        db.session.commit()
        return redirect(url_for('admin.cabinet_parts', cabinet_id=cabinet_id))
    parts = PartTemplate.query.filter_by(cabinet_type_id=cabinet_id).all()
    return render_template('admin/cabinet_parts.html',
                           cabinet=cabinet,
                           parts=parts,
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
# COLORS
# ============================================

@admin_bp.route('/colors')
def colors():
    check = admin_required()
    if check:
        return check
    all_colors = Color.query.order_by(Color.name).all()
    form_name = session.pop('color_prefill_name', '')
    form_hex = session.pop('color_prefill_hex', '#ffffff')
    return render_template('admin/colors.html', colors=all_colors,
                           form_name=form_name, form_hex=form_hex)

@admin_bp.route('/colors/create', methods=['POST'])
def create_color():
    check = admin_required()
    if check:
        return check
    name = ' '.join(request.form['name'].strip().split()).title()
    hex_code = request.form.get('hex_code') or None
    existing = Color.query.filter(Color.name.ilike(name)).first()
    if existing:
        flash(f'"{name}" already exists.', 'error')
        session['color_prefill_name'] = name
        session['color_prefill_hex'] = hex_code
        return redirect(url_for('admin.colors'))
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