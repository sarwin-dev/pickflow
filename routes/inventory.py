import re
from io import BytesIO
from flask import Blueprint, render_template, session, redirect, url_for, request, send_file, flash
from extensions import db
from models import Part, Inventory, ShoppingListItem, WarehouseConfig
from datetime import datetime
from sqlalchemy import cast, Integer, nullslast

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


def build_part_item(part):
    records = Inventory.query.filter_by(part_id=part.id).order_by(
        Inventory.is_active.desc(),
        cast(Inventory.aisle,    Integer),
        cast(Inventory.bay,      Integer),
        cast(Inventory.shelf,    Integer),
        nullslast(cast(Inventory.location, Integer))
    ).all()
    overflow_total = sum(r.quantity for r in records if not r.is_active)
    active_total   = sum(r.quantity for r in records if r.is_active)
    min_qty        = records[0].min_quantity if records else 0
    if overflow_total == 0:
        status = 'out'
    elif overflow_total <= min_qty:
        status = 'low'
    else:
        status = 'ok'
    in_list = ShoppingListItem.query.filter_by(part_id=part.id).first() is not None
    needs_pulldown = active_total == 0 and overflow_total > 0
    return {
        'part': part, 'records': records,
        'overflow_total': overflow_total, 'active_total': active_total,
        'min_qty': min_qty, 'status': status, 'in_list': in_list,
        'needs_pulldown': needs_pulldown,
    }

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

    if True:
        if search:
            normalized = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', search)
            normalized = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', normalized).strip()
            parts = Part.query.filter(Part.name.ilike(f'%{normalized}%')).order_by(Part.name).all()
        else:
            parts = Part.query.order_by(Part.name).all()

        for part in parts:
            item = build_part_item(part)
            if filter_mode == 'low' and item['status'] == 'ok':
                continue
            if filter_mode == 'low' and item['in_list']:
                continue
            part_results.append(item)

        # partes que necesitan pulldown primero
        part_results.sort(key=lambda x: (not x['needs_pulldown'], x['part'].name))

    shopping_count = ShoppingListItem.query.count()

    pending_loc_edit = session.get('pending_loc_edit')
    return render_template('inventory/index.html',
                           part_results=part_results,
                           search=search,
                           filter_mode=filter_mode,
                           shopping_count=shopping_count,
                           pending_loc_edit=pending_loc_edit)

@inventory_bp.route('/update-location/<int:record_id>', methods=['POST'])
def update_location(record_id):
    check = inventory_required()
    if check:
        return check

    record = Inventory.query.get_or_404(record_id)
    config = WarehouseConfig.query.first()

    new_aisle        = request.form.get('aisle', '').strip()
    new_bay          = request.form.get('bay', '').strip()
    new_shelf        = int(request.form.get('shelf', 0))
    new_location     = request.form.get('location', '').strip() or None
    new_quantity     = int(request.form.get('quantity', record.quantity))
    back             = request.form.get('back', url_for('inventory.index'))
    loc_confirmed    = request.form.get('loc_confirmed') == '1'

    # valida rango total de shelves
    if new_shelf < 1 or new_shelf > config.total_shelves:
        flash(f'Shelf must be between 1 and {config.total_shelves}.', 'error')
        return redirect(back)

    # verifica conflicto con cualquier otro registro en esa ubicacion
    if not loc_confirmed:
        conflict = Inventory.query.filter(
            Inventory.aisle    == new_aisle,
            Inventory.bay      == new_bay,
            Inventory.shelf    == str(new_shelf),
            Inventory.location == new_location,
            Inventory.id       != record_id
        ).first()
        if conflict:
            loc = f'A{int(new_aisle):02d}.B{int(new_bay):02d}.S{new_shelf:02d}'
            if new_location:
                loc += f'.L{int(new_location):02d}'
            other = conflict.part.name if conflict.part_id != record.part_id else f'another box of "{record.part.name}"'
            session['pending_loc_edit'] = {
                'record_id': record_id,
                'aisle': new_aisle, 'bay': new_bay,
                'shelf': str(new_shelf), 'location': new_location,
                'quantity': new_quantity,
                'loc': loc,
                'other': other,
                'back': back,
            }
            return redirect(back)

    was_active  = record.is_active
    now_active  = new_shelf <= config.active_shelves

    record.aisle     = new_aisle
    record.bay       = new_bay
    record.shelf     = str(new_shelf)
    record.location  = new_location
    record.quantity  = new_quantity
    record.is_active = now_active

    part = Part.query.get(record.part_id)
    if part:
        if now_active:
            # la caja esta ahora en zona activa — actualiza la ubicacion maestra
            part.active_aisle    = new_aisle
            part.active_bay      = new_bay
            part.active_shelf    = str(new_shelf)
            part.active_location = new_location
        elif was_active and not now_active:
            # la caja se movio de activa a overflow — limpia la ubicacion maestra
            part.active_aisle    = None
            part.active_bay      = None
            part.active_shelf    = None
            part.active_location = None

    db.session.commit()
    session.pop('pending_loc_edit', None)
    flash('Updated.', 'success')
    return redirect(back)


@inventory_bp.route('/clear-pending-edit')
def clear_pending_edit():
    session.pop('pending_loc_edit', None)
    return '', 204


@inventory_bp.route('/delete-record/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    check = inventory_required()
    if check:
        return check
    record = Inventory.query.get_or_404(record_id)
    back = request.form.get('back', url_for('inventory.index'))
    # si era la caja activa, limpia la ubicacion maestra
    if record.is_active:
        part = Part.query.get(record.part_id)
        if part:
            part.active_aisle = part.active_bay = part.active_shelf = part.active_location = None
    db.session.delete(record)
    db.session.commit()
    flash('Record deleted.', 'success')
    return redirect(back)


@inventory_bp.route('/depleted/<int:record_id>', methods=['POST'])
def depleted(record_id):
    check = inventory_required()
    if check:
        return check
    record = Inventory.query.get_or_404(record_id)
    part_id = record.part_id
    db.session.delete(record)
    db.session.commit()
    if request.headers.get('HX-Request'):
        part = Part.query.get(part_id)
        item = build_part_item(part)
        return render_template('inventory/partials/part_card.html', item=item,
                               search='', filter_mode='')
    flash('Active box marked as depleted and removed.', 'success')
    back = request.form.get('next', url_for('inventory.index'))
    return redirect(back)


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
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch

    items = ShoppingListItem.query.order_by(ShoppingListItem.added_at).all()
    navy   = colors.HexColor('#1e1b4b')
    light  = colors.HexColor('#f9fafb')
    border = colors.HexColor('#e5e7eb')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)

    title_s = ParagraphStyle('t', fontSize=15, fontName='Helvetica-Bold', textColor=navy, spaceAfter=2)
    meta_s  = ParagraphStyle('m', fontSize=9,  fontName='Helvetica', textColor=colors.HexColor('#6b7280'), spaceAfter=10)

    elements = [
        Paragraph('REORDER LIST', title_s),
        Paragraph(f"Generated: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}  ·  {len(items)} item(s)", meta_s),
    ]

    table_data = [['#', 'Part', 'Qty Needed', 'Requested By', 'Date']]
    for i, item in enumerate(items, 1):
        table_data.append([
            str(i),
            item.part.name if item.part else '—',
            str(item.quantity_needed),
            item.requester.name if item.requester else '—',
            item.added_at.strftime('%m/%d/%Y') if item.added_at else '—',
        ])

    t = Table(table_data, colWidths=[0.4*inch, 2.8*inch, 1.0*inch, 1.8*inch, 1.0*inch], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), navy),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('PADDING',    (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light]),
        ('GRID',       (0,0), (-1,-1), 0.4, border),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',      (0,0), (0,-1), 'CENTER'),
        ('ALIGN',      (2,0), (2,-1), 'CENTER'),
        ('FONTNAME',   (2,1), (2,-1), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)

    filename = f"ReorderList_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(buffer, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)
