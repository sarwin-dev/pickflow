import re
from io import BytesIO
from flask import Blueprint, render_template, session, redirect, url_for, request, send_file
from extensions import db
from models import Part, Inventory, ShoppingListItem
from datetime import datetime

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
    filter_mode = request.args.get('filter', '')
    part_results = []

    if search or filter_mode == 'low':
        if search:
            normalized = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', search)
            normalized = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', normalized).strip()
            parts = Part.query.filter(Part.name.ilike(f'%{normalized}%')).order_by(Part.name).all()
        else:
            parts = Part.query.order_by(Part.name).all()

        for part in parts:
            records = Inventory.query.filter_by(part_id=part.id).order_by(
                Inventory.is_active.desc(),
                Inventory.aisle, Inventory.bay, Inventory.shelf
            ).all()

            overflow_total = sum(r.quantity for r in records if not r.is_active)
            active_total = sum(r.quantity for r in records if r.is_active)
            min_qty = records[0].min_quantity if records else 0

            if overflow_total == 0:
                status = 'out'
            elif overflow_total <= min_qty:
                status = 'low'
            else:
                status = 'ok'

            if filter_mode == 'low' and status == 'ok':
                continue

            in_list = ShoppingListItem.query.filter_by(part_id=part.id).first() is not None

            # en modo low, ocultar partes que ya estan en el reorder list
            if filter_mode == 'low' and in_list:
                continue

            part_results.append({
                'part': part,
                'records': records,
                'overflow_total': overflow_total,
                'active_total': active_total,
                'min_qty': min_qty,
                'status': status,
                'in_list': in_list,
            })

    shopping_count = ShoppingListItem.query.count()

    return render_template('inventory/index.html',
                           part_results=part_results,
                           search=search,
                           filter_mode=filter_mode,
                           shopping_count=shopping_count)

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
                            filter=request.form.get('filter', '')))

# ============================================
# SHOPPING LIST
# ============================================

@inventory_bp.route('/shopping/add/<int:part_id>', methods=['POST'])
def shopping_add(part_id):
    check = supervisor_required()
    if check:
        return check
    existing = ShoppingListItem.query.filter_by(part_id=part_id).first()
    if not existing:
        quantity = int(request.form.get('quantity_needed', 1))
        notes = request.form.get('notes', '').strip() or None
        item = ShoppingListItem(
            part_id=part_id,
            quantity_needed=quantity,
            notes=notes,
            added_by=session['user_id'],
            added_at=datetime.utcnow()
        )
        db.session.add(item)
        db.session.commit()
    # regresa a donde venia
    return redirect(request.referrer or url_for('inventory.index', filter='low'))

@inventory_bp.route('/shopping/')
def shopping_list():
    check = supervisor_required()
    if check:
        return check
    items = ShoppingListItem.query.order_by(ShoppingListItem.added_at.desc()).all()
    return render_template('inventory/shopping_list.html', items=items)

@inventory_bp.route('/shopping/update/<int:item_id>', methods=['POST'])
def shopping_update(item_id):
    check = supervisor_required()
    if check:
        return check
    item = ShoppingListItem.query.get(item_id)
    if item:
        item.quantity_needed = int(request.form.get('quantity_needed', 1))
        item.notes = request.form.get('notes', '').strip() or None
        db.session.commit()
    return redirect(url_for('inventory.shopping_list'))

@inventory_bp.route('/shopping/remove/<int:item_id>')
def shopping_remove(item_id):
    check = supervisor_required()
    if check:
        return check
    item = ShoppingListItem.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('inventory.shopping_list'))

@inventory_bp.route('/shopping/clear')
def shopping_clear():
    check = supervisor_required()
    if check:
        return check
    ShoppingListItem.query.delete()
    db.session.commit()
    return redirect(url_for('inventory.shopping_list'))

@inventory_bp.route('/shopping/pdf')
def shopping_pdf():
    check = supervisor_required()
    if check:
        return check

    import io
    from weasyprint import HTML

    items = ShoppingListItem.query.order_by(ShoppingListItem.added_at).all()
    html_string = render_template('inventory/shopping_pdf.html', items=items, now=datetime.now())
    pdf_bytes = HTML(string=html_string).write_pdf()

    filename = f"ReorderList_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf',
                     as_attachment=True, download_name=filename)
