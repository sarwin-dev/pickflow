from extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CabinetType(db.Model):
    __tablename__ = 'cabinet_types'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=True)
    color = db.Column(db.String(50), nullable=True)
    is_custom = db.Column(db.Boolean, default=False)
    parts = db.relationship('PartTemplate', backref='cabinet', lazy=True)

# tabla maestra de partes - cada parte existe una sola vez
class Part(db.Model):
    __tablename__ = 'parts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # indica si la parte es compartida entre varios tipos de gabinete
    # ejemplo: B Side L es compartida, B Back 24 no
    is_shared = db.Column(db.Boolean, default=False)
    # ubicacion activa en el almacen - shelves 1 y 2
    active_aisle = db.Column(db.String(5), nullable=True)
    active_bay = db.Column(db.String(5), nullable=True)
    active_shelf = db.Column(db.String(5), nullable=True)
    active_location = db.Column(db.String(5), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# vincula partes maestras con tipos de gabinete
class PartTemplate(db.Model):
    __tablename__ = 'part_templates'
    id = db.Column(db.Integer, primary_key=True)
    cabinet_type_id = db.Column(db.Integer, db.ForeignKey('cabinet_types.id'), nullable=False)
    # referencia a la parte maestra
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    cart = db.Column(db.Integer, nullable=False)
    is_optional = db.Column(db.Boolean, default=False)
    # relacion con la parte maestra
    part = db.relationship('Part', backref='templates')

class WorkOrder(db.Model):
    __tablename__ = 'work_orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('work_orders.id'), nullable=False)
    cabinet_type_id = db.Column(db.Integer, db.ForeignKey('cabinet_types.id'), nullable=False)
    slot = db.Column(db.Integer, nullable=False)
    cart = db.Column(db.Integer, nullable=False)

class PickItem(db.Model):
    __tablename__ = 'pick_items'
    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'), nullable=False)
    part_template_id = db.Column(db.Integer, db.ForeignKey('part_templates.id'), nullable=False)
    is_picked = db.Column(db.Boolean, default=False)
    picked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    picked_at = db.Column(db.DateTime, nullable=True)

class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    # ahora referencia a la parte maestra, no a part_template
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    aisle = db.Column(db.String(5), nullable=True)
    bay = db.Column(db.String(5), nullable=True)
    shelf = db.Column(db.String(5), nullable=True)
    location = db.Column(db.String(5), nullable=True)
    quantity = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=False)
    min_quantity = db.Column(db.Integer, default=10)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    part = db.relationship('Part', backref='inventory_records')

class Loss(db.Model):
    __tablename__ = 'losses'
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    reported_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)

class WarehouseConfig(db.Model):
    __tablename__ = 'warehouse_config'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='My Warehouse')
    total_aisles = db.Column(db.Integer, nullable=False, default=6)
    total_bays = db.Column(db.Integer, nullable=False, default=35)
    total_shelves = db.Column(db.Integer, nullable=False, default=6)
    total_locations = db.Column(db.Integer, nullable=False, default=4)
    active_shelves = db.Column(db.Integer, nullable=False, default=2)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)