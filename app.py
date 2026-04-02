import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from extensions import db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cabinets_secret_key_2024')

database_url = os.environ.get('DATABASE_URL', 'postgresql://cabinets_user:cabinets123@localhost/cabinets_db')
# Railway a veces entrega postgres:// en lugar de postgresql://
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# crea las tablas automaticamente al arrancar si no existen
# y crea el usuario admin inicial si la base de datos esta vacia
with app.app_context():
    try:
        import models  # importa todos los modelos antes de crear las tablas
        from werkzeug.security import generate_password_hash
        db.create_all()
        from sqlalchemy import text
        db.session.execute(text('ALTER TABLE cabinet_types ALTER COLUMN code TYPE VARCHAR(15)'))
        db.session.commit()
        indexes = [
            'CREATE INDEX IF NOT EXISTS ix_work_orders_status ON work_orders (status)',
            'CREATE INDEX IF NOT EXISTS ix_work_orders_created_by ON work_orders (created_by)',
            'CREATE INDEX IF NOT EXISTS ix_inventory_part_id ON inventory (part_id)',
            'CREATE INDEX IF NOT EXISTS ix_inventory_is_active ON inventory (is_active)',
            'CREATE INDEX IF NOT EXISTS ix_pick_items_order_item_id ON pick_items (order_item_id)',
            'CREATE INDEX IF NOT EXISTS ix_pick_items_part_template_id ON pick_items (part_template_id)',
            'CREATE INDEX IF NOT EXISTS ix_shopping_list_part_id ON shopping_list (part_id)',
        ]
        for idx in indexes:
            db.session.execute(text(idx))
        db.session.commit()
        from models import User, WarehouseConfig
        if User.query.count() == 0:
            admin = User(
                name='Admin',
                email='admin@pickflow.com',
                password=generate_password_hash('admin1234'),
                role='admin'
            )
            db.session.add(admin)
            db.session.add(WarehouseConfig())
            db.session.commit()
    except Exception as e:
        print(f'DB init error: {e}')

@app.route('/')
def inicio():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        from models import User
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = user.name
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid email or password'
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    from models import WorkOrder, Inventory
    from datetime import date
    role = session['user_role']
    stats = {}

    if role in ['admin', 'supervisor']:
        from models import ShoppingListItem
        today = date.today()
        stats['pending'] = WorkOrder.query.filter_by(status='pending').count()
        stats['in_progress'] = WorkOrder.query.filter_by(status='in_progress').count()
        stats['completed_today'] = WorkOrder.query.filter(
            WorkOrder.status == 'completed',
            db.func.date(WorkOrder.updated_at) == today
        ).count()
        stats['low_stock'] = Inventory.query.filter(
            Inventory.is_active == True,
            Inventory.quantity <= Inventory.min_quantity
        ).count()
        stats['on_the_way'] = ShoppingListItem.query.count()

    elif role == 'warehouse':
        stats['available'] = WorkOrder.query.filter(
            WorkOrder.status.in_(['pending', 'in_progress'])
        ).count()
        stats['in_progress'] = WorkOrder.query.filter_by(status='in_progress').count()

    elif role == 'order_entry':
        stats['my_orders'] = WorkOrder.query.filter_by(
            created_by=session['user_id']
        ).count()
        stats['pending'] = WorkOrder.query.filter_by(status='pending').count()

    return render_template('dashboard.html', stats=stats)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/reset', methods=['GET', 'POST'])
def reset_admin():
    if os.environ.get('RESET_MODE', '').lower() != 'true':
        return 'Not available.', 403
    from models import User
    from werkzeug.security import generate_password_hash
    error = None
    if request.method == 'POST':
        email = request.form['email']
        new_pw = request.form['new_password']
        user = User.query.filter_by(email=email).first()
        if not user:
            error = 'No user found with that email'
        else:
            user.password = generate_password_hash(new_pw)
            db.session.commit()
            return 'Password updated. <a href="/login">Login</a>', 200
    return render_template('reset_admin.html', error=error)

@app.route('/reset-demo')
def reset_demo():
    if os.environ.get('DEMO_MODE', '').lower() != 'true':
        return 'Not available.', 403
    from models import (User, WorkOrder, OrderItem, PickItem, Inventory,
                        ShoppingListItem, Loss, CabinetType, PartTemplate,
                        Part, Color, WarehouseConfig)
    from werkzeug.security import generate_password_hash
    # borra todo en orden para respetar las foreign keys
    PickItem.query.delete()
    ShoppingListItem.query.delete()
    Loss.query.delete()
    OrderItem.query.delete()
    WorkOrder.query.delete()
    Inventory.query.delete()
    PartTemplate.query.delete()
    Part.query.delete()
    CabinetType.query.delete()
    Color.query.delete()
    User.query.delete()
    WarehouseConfig.query.delete()
    db.session.commit()
    # recrea el admin y la config base
    db.session.add(User(
        name='Admin',
        email='admin@pickflow.com',
        password=generate_password_hash('admin1234'),
        role='admin'
    ))
    db.session.add(WarehouseConfig())
    db.session.commit()
    session.clear()
    return 'Demo reset complete. <a href="/login">Login</a>', 200

# ============================================
# REGISTRAMOS LOS BLUEPRINTS
# cada modulo se conecta a la app aqui
# ============================================
from routes.admin import admin_bp
app.register_blueprint(admin_bp)

from routes.receiving import receiving_bp
app.register_blueprint(receiving_bp)

from routes.orders import orders_bp
app.register_blueprint(orders_bp)

from routes.pick import pick_bp
app.register_blueprint(pick_bp)

from routes.supervision import supervision_bp
app.register_blueprint(supervision_bp)

from routes.inventory import inventory_bp
app.register_blueprint(inventory_bp)

from routes.losses import losses_bp
app.register_blueprint(losses_bp)

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    from models import User
    from werkzeug.security import generate_password_hash
    from flask import flash
    error = None
    if request.method == 'POST':
        current = request.form['current_password']
        new_pw = request.form['new_password']
        confirm = request.form['confirm_password']
        user = User.query.get(session['user_id'])
        if not check_password_hash(user.password, current):
            error = 'Current password is incorrect'
        elif new_pw != confirm:
            error = 'New passwords do not match'
        elif len(new_pw) < 6:
            error = 'New password must be at least 6 characters'
        else:
            user.password = generate_password_hash(new_pw)
            db.session.commit()
            flash('Password updated successfully', 'success')
            return redirect(url_for('dashboard'))
    return render_template('change_password.html', error=error)


# ============================================
# FLASK CLI COMMANDS
# ============================================

@app.cli.command('reset-password')
def reset_password_cmd():
    """Reset a user password from the command line. Usage: flask reset-password"""
    import getpass
    email = input('Email: ').strip()
    from models import User
    user = User.query.filter_by(email=email).first()
    if not user:
        print(f'No user found with email: {email}')
        return
    new_pw = getpass.getpass('New password: ')
    confirm = getpass.getpass('Confirm password: ')
    if new_pw != confirm:
        print('Passwords do not match.')
        return
    from werkzeug.security import generate_password_hash
    user.password = generate_password_hash(new_pw)
    db.session.commit()
    print(f'Password updated for {user.name} ({user.email})')


if __name__ == '__main__':
    app.run(debug=True)