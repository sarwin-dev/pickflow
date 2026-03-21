from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash
from extensions import db
from models import User

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# funcion auxiliar - verifica que el usuario es admin
def admin_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] != 'admin':
        return redirect(url_for('dashboard'))
    return None

# ruta principal del modulo admin
@admin_bp.route('/')
def index():
    check = admin_required()
    if check:
        return check
    return render_template('admin/index.html')

# ============================================
# USERS - gestion de usuarios
# ============================================

# lista todos los usuarios
@admin_bp.route('/users')
def users():
    check = admin_required()
    if check:
        return check
    # trae todos los usuarios de la base de datos
    all_users = User.query.all()
    return render_template('admin/users.html', users=all_users)

# crea un usuario nuevo
@admin_bp.route('/users/create', methods=['GET', 'POST'])
def create_user():
    check = admin_required()
    if check:
        return check
    error = None
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        # verificamos que el email no exista ya
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

# elimina un usuario
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
# CABINET TYPES - gestion de tipos de gabinete
# ============================================
from models import CabinetType, PartTemplate

# lista todos los tipos de gabinete
@admin_bp.route('/cabinets')
def cabinets():
    check = admin_required()
    if check:
        return check
    all_cabinets = CabinetType.query.all()
    return render_template('admin/cabinets.html', cabinets=all_cabinets)

# crea un tipo de gabinete nuevo
@admin_bp.route('/cabinets/create', methods=['GET', 'POST'])
def create_cabinet():
    check = admin_required()
    if check:
        return check
    error = None
    if request.method == 'POST':
        new_cabinet = CabinetType(
            code=request.form['code'],
            name=request.form['name'],
            width=request.form['width'],
            height=request.form.get('height') or None,
            color=request.form.get('color'),
            is_custom=True if request.form.get('is_custom') else False
        )
        db.session.add(new_cabinet)
        db.session.commit()
        return redirect(url_for('admin.cabinet_parts', cabinet_id=new_cabinet.id))
    return render_template('admin/create_cabinet.html', error=error)

# ve y agrega partes a un gabinete
# ve y agrega partes a un gabinete
@admin_bp.route('/cabinets/<int:cabinet_id>/parts', methods=['GET', 'POST'])
def cabinet_parts(cabinet_id):
    check = admin_required()
    if check:
        return check
    cabinet = CabinetType.query.get(cabinet_id)
    # traemos la configuracion del warehouse para validar ubicaciones
    config = WarehouseConfig.query.first()
    if request.method == 'POST':
        new_part = PartTemplate(
            cabinet_type_id=cabinet_id,
            name=request.form['name'],
            quantity=request.form['quantity'],
            cart=request.form['cart'],
            is_optional=True if request.form.get('is_optional') else False,
            active_aisle=request.form.get('active_aisle') or None,
            active_bay=request.form.get('active_bay') or None,
            active_shelf=request.form.get('active_shelf') or None,
            active_location=request.form.get('active_location') or None,
            overflow_aisle=request.form.get('overflow_aisle') or None,
            overflow_bay=request.form.get('overflow_bay') or None,
            overflow_shelf=request.form.get('overflow_shelf') or None,
            overflow_location=request.form.get('overflow_location') or None,
        )
        db.session.add(new_part)
        db.session.commit()
        return redirect(url_for('admin.cabinet_parts', cabinet_id=cabinet_id))
    parts = PartTemplate.query.filter_by(cabinet_type_id=cabinet_id).all()
    return render_template('admin/cabinet_parts.html', 
                         cabinet=cabinet, 
                         parts=parts,
                         config=config)  # pasamos config al HTML

# elimina un tipo de gabinete
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

# elimina una parte de un gabinete
@admin_bp.route('/cabinets/<int:cabinet_id>/parts/delete/<int:part_id>')
def delete_part(cabinet_id, part_id):
    check = admin_required()
    if check:
        return check
    part = PartTemplate.query.get(part_id)
    if part:
        db.session.delete(part)
        db.session.commit()
    return redirect(url_for('admin.cabinet_parts', cabinet_id=cabinet_id))

# ============================================
# WAREHOUSE CONFIG - configuracion del warehouse
# ============================================
from models import WarehouseConfig

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
        from datetime import datetime
        config.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('admin.warehouse_config'))
    return render_template('admin/warehouse_config.html', config=config)