import re
from flask import Blueprint, render_template, session, redirect, url_for, request
from extensions import db
from models import Part, Inventory

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')

def inventory_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor', 'warehouse']:
        return redirect(url_for('dashboard'))
    return None

def supervisor_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None

@inventory_bp.route('/')
def index():
    check = inventory_required()
    if check:
        return check

    search = request.args.get('search', '').strip()
    part_results = []

    if search:
        # normaliza el termino de busqueda: "toe33" -> "toe 33"
        normalized = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', search)
        normalized = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', normalized).strip()

        parts = Part.query.filter(Part.name.ilike(f'%{normalized}%')).order_by(Part.name).all()

        for part in parts:
            records = Inventory.query.filter_by(part_id=part.id).order_by(
                Inventory.is_active.desc(),
                Inventory.aisle, Inventory.bay, Inventory.shelf
            ).all()

            overflow_total = sum(r.quantity for r in records if not r.is_active)
            active_total = sum(r.quantity for r in records if r.is_active)

            # min_quantity viene de cualquier registro de la parte
            min_qty = records[0].min_quantity if records else 0

            if overflow_total == 0:
                status = 'out'
            elif overflow_total <= min_qty:
                status = 'low'
            else:
                status = 'ok'

            part_results.append({
                'part': part,
                'records': records,
                'overflow_total': overflow_total,
                'active_total': active_total,
                'min_qty': min_qty,
                'status': status,
            })

    return render_template('inventory/index.html',
                           part_results=part_results,
                           search=search)

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
    return redirect(url_for('inventory.index', search=request.form.get('search', '')))
