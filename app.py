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

if __name__ == '__main__':
    app.run(debug=True)