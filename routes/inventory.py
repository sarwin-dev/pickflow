from flask import Blueprint, render_template, session, redirect, url_for, request
from extensions import db
from models import Part, Inventory

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')

def supervisor_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None

@inventory_bp.route('/')
def index():
    check = supervisor_required()
    if check:
        return check

    search = request.args.get('search', '').strip()
    filter_status = request.args.get('filter', 'all')

    parts_query = Part.query.order_by(Part.name)
    if search:
        parts_query = parts_query.filter(Part.name.ilike(f'%{search}%'))

    parts = parts_query.all()

    stock_list = []
    for part in parts:
        active_qty = sum(r.quantity for r in part.inventory_records if r.is_active)
        overflow_qty = sum(r.quantity for r in part.inventory_records if not r.is_active)
        total_qty = active_qty + overflow_qty

        # min_quantity viene del registro activo si existe
        active_record = next((r for r in part.inventory_records if r.is_active), None)
        min_qty = active_record.min_quantity if active_record else 0

        if total_qty == 0:
            status = 'out'
        elif overflow_qty <= min_qty:
            status = 'low'
        else:
            status = 'ok'

        stock_list.append({
            'part': part,
            'active_qty': active_qty,
            'overflow_qty': overflow_qty,
            'total_qty': total_qty,
            'min_qty': min_qty,
            'status': status,
        })

    if filter_status == 'low':
        stock_list = [s for s in stock_list if s['status'] in ['low', 'out']]
    elif filter_status == 'out':
        stock_list = [s for s in stock_list if s['status'] == 'out']

    # ordena: primero out, luego low, luego ok
    order_map = {'out': 0, 'low': 1, 'ok': 2}
    stock_list.sort(key=lambda x: order_map[x['status']])

    low_count = sum(1 for s in stock_list if s['status'] in ['low', 'out'])

    return render_template('inventory/index.html',
                           stock_list=stock_list,
                           search=search,
                           filter_status=filter_status,
                           low_count=low_count)

@inventory_bp.route('/set-min/<int:part_id>', methods=['POST'])
def set_min(part_id):
    check = supervisor_required()
    if check:
        return check

    min_qty = int(request.form.get('min_qty', 0))
    records = Inventory.query.filter_by(part_id=part_id).all()
    for record in records:
        record.min_quantity = min_qty
    db.session.commit()

    return redirect(url_for('inventory.index',
                            search=request.form.get('search', ''),
                            filter=request.form.get('filter', 'all')))
