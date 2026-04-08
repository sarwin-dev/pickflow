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
    code = db.Column(db.String(15), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=True)
    color = db.Column(db.String(50), nullable=True)
    is_custom = db.Column(db.Boolean, default=False)
    annual_qty = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    parts = db.relationship('PartTemplate', backref='cabinet', lazy=True, cascade='all, delete-orphan')

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

class Color(db.Model):
    __tablename__ = 'colors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    # codigo hex opcional para mostrar visualmente el color
    hex_code = db.Column(db.String(7), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  

class WorkOrder(db.Model):
    __tablename__ = 'work_orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    job_name = db.Column(db.String(100), nullable=True)
    lot_number = db.Column(db.String(50), nullable=True)
    scheduled_date = db.Column(db.Date, nullable=True)
    # color del trabajo - define que aisle visita el picker
    color_id = db.Column(db.Integer, db.ForeignKey('colors.id'), nullable=True)
    color = db.relationship('Color', backref='orders')
    status = db.Column(db.String(20), default='pending', index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)
    creator = db.relationship('User', backref='orders')

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('work_orders.id'), nullable=False)
    cabinet_type_id = db.Column(db.Integer, db.ForeignKey('cabinet_types.id'), nullable=False)
    slot = db.Column(db.Integer, nullable=False)
    cart = db.Column(db.Integer, nullable=False)
    # relacion con el gabinete
    cabinet = db.relationship('CabinetType', backref='order_items')
    # relacion con los picks de este slot
    picks = db.relationship('PickItem', backref='order_item', lazy=True)

class PickItem(db.Model):
    __tablename__ = 'pick_items'
    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'), nullable=False, index=True)
    part_template_id = db.Column(db.Integer, db.ForeignKey('part_templates.id'), nullable=False, index=True)
    is_picked = db.Column(db.Boolean, default=False)
    is_missing = db.Column(db.Boolean, default=False)
    picked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    picked_at = db.Column(db.DateTime, nullable=True)

class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    # ahora referencia a la parte maestra, no a part_template
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False, index=True)
    aisle = db.Column(db.String(5), nullable=True)
    bay = db.Column(db.String(5), nullable=True)
    shelf = db.Column(db.String(5), nullable=True)
    location = db.Column(db.String(5), nullable=True)
    quantity = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=False, index=True)
    min_quantity = db.Column(db.Integer, default=100)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    part = db.relationship('Part', backref='inventory_records')

class ShoppingListItem(db.Model):
    __tablename__ = 'shopping_list'
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False, index=True)
    quantity_needed = db.Column(db.Integer, default=1)
    notes = db.Column(db.String(200), nullable=True)
    added_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    ordered_at = db.Column(db.DateTime, nullable=True)
    part = db.relationship('Part', backref='shopping_items')
    requester = db.relationship('User', backref='shopping_items')

class Loss(db.Model):
    __tablename__ = 'losses'
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    comments = db.Column(db.Text, nullable=True)
    reported_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    part = db.relationship('Part', backref='losses')
    reporter = db.relationship('User', backref='losses')

class WarehouseConfig(db.Model):
    __tablename__ = 'warehouse_config'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='My Warehouse')
    total_aisles = db.Column(db.Integer, nullable=False, default=6)
    total_bays = db.Column(db.Integer, nullable=False, default=35)
    total_shelves = db.Column(db.Integer, nullable=False, default=6)
    total_locations = db.Column(db.Integer, nullable=False, default=4)
    active_shelves = db.Column(db.Integer, nullable=False, default=2)
    max_cart_slots = db.Column(db.Integer, nullable=False, default=24)
    # etiquetas dinamicas - cada empresa usa su propia terminologia
    label_aisle = db.Column(db.String(50), nullable=False, default='Aisle')
    label_bay = db.Column(db.String(50), nullable=False, default='Bay')
    label_shelf = db.Column(db.String(50), nullable=False, default='Shelf')
    label_location = db.Column(db.String(50), nullable=False, default='Location')
    # prefijos para los codigos - ej: A para Aisle, B para Bay
    prefix_aisle = db.Column(db.String(5), nullable=False, default='A')
    prefix_bay = db.Column(db.String(5), nullable=False, default='B')
    prefix_shelf = db.Column(db.String(5), nullable=False, default='S')
    prefix_location = db.Column(db.String(5), nullable=False, default='L')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    # numero maximo de slots por carrito
    max_cart_slots = db.Column(db.Integer, nullable=False, default=24)

class ReceivingLog(db.Model):
    """Registro histórico inmutable de cajas recibidas. Se purga automáticamente a los 7 días."""
    __tablename__ = 'receiving_log'
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    aisle = db.Column(db.String(5), nullable=True)
    bay = db.Column(db.String(5), nullable=True)
    shelf = db.Column(db.String(5), nullable=True)
    location = db.Column(db.String(5), nullable=True)
    is_active = db.Column(db.Boolean, default=False)
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    part = db.relationship('Part', backref='receiving_logs')
    receiver = db.relationship('User', backref='receiving_logs')