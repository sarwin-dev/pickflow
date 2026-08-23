from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from extensions import db
from models import Part, Inventory, CabinetType, PartTemplate, WarehouseConfig
from sqlalchemy import func

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


def supervisor_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None


@analytics_bp.route('/')
def index():
    check = supervisor_required()
    if check:
        return check

    # Resumen rápido para dashboard
    total_parts = Part.query.count()
    total_cabinets = CabinetType.query.count()

    # Contar partes críticas (< 1 mes stock)
    MONTHS = 4
    consumption = {}
    for cabinet in CabinetType.query.filter(CabinetType.annual_qty > 0).all():
        for tmpl in cabinet.parts:
            projected = cabinet.annual_qty * (MONTHS / 12) * tmpl.quantity
            consumption[tmpl.part_id] = consumption.get(tmpl.part_id, 0) + projected

    from sqlalchemy import func
    overflow = dict(
        db.session.query(Inventory.part_id, func.sum(Inventory.quantity))
        .filter(Inventory.is_active == False)
        .group_by(Inventory.part_id)
        .all()
    )

    critical_count = 0
    for part_id, consumed in consumption.items():
        monthly_avg = consumed / MONTHS
        stock = overflow.get(part_id, 0)
        months_remaining = (stock / monthly_avg) if monthly_avg > 0 else None
        if months_remaining is not None and months_remaining < 1:
            critical_count += 1

    return render_template('analytics/index.html',
                          total_parts=total_parts,
                          total_cabinets=total_cabinets,
                          critical_count=critical_count)


@analytics_bp.route('/parts')
def parts_analytics():
    check = supervisor_required()
    if check:
        return check

    # Selector de período: 1, 3, 4, 6, 12 meses (por defecto 4)
    months = request.args.get('months', 4, type=int)
    if months not in [1, 3, 4, 6, 12]:
        months = 4

    # Calcula consumo proyectado por parte
    consumption = {}
    for cabinet in CabinetType.query.all():
        if not cabinet.annual_qty:
            continue
        for tmpl in cabinet.parts:
            projected = cabinet.annual_qty * (months / 12) * tmpl.quantity
            consumption[tmpl.part_id] = consumption.get(tmpl.part_id, 0) + projected

    if not consumption:
        return render_template('analytics/parts.html', rows=[], months=months)

    # Stock actual en overflow
    overflow = dict(
        db.session.query(Inventory.part_id, func.sum(Inventory.quantity))
        .filter(Inventory.is_active == False)
        .group_by(Inventory.part_id)
        .all()
    )

    # Construye filas
    rows = []
    part_ids = list(consumption.keys())
    parts = {p.id: p for p in Part.query.filter(Part.id.in_(part_ids)).all()}

    for part_id, consumed in consumption.items():
        part = parts.get(part_id)
        if not part:
            continue
        monthly_avg = consumed / months
        stock = overflow.get(part_id, 0)
        months_remaining = (stock / monthly_avg) if monthly_avg > 0 else None
        rows.append({
            'part': part,
            'consumed': round(consumed),
            'monthly_avg': round(monthly_avg, 1),
            'stock': stock,
            'months_remaining': round(months_remaining, 1) if months_remaining is not None else None,
        })

    rows.sort(key=lambda r: r['consumed'], reverse=True)
    for i, row in enumerate(rows, 1):
        row['rank'] = i

    critical_count = sum(
        1 for r in rows
        if r['months_remaining'] is not None and r['months_remaining'] < 1
    )

    return render_template('analytics/parts.html', rows=rows, months=months,
                          critical_count=critical_count)


@analytics_bp.route('/parts/<int:part_id>')
def part_detail(part_id):
    check = supervisor_required()
    if check:
        return check

    part = Part.query.get_or_404(part_id)
    months = 4

    # Busca qué cabinet types usan esta parte
    templates = PartTemplate.query.filter_by(part_id=part_id).all()

    cabinet_data = []
    for tmpl in templates:
        cabinet = CabinetType.query.get(tmpl.cabinet_type_id)
        if cabinet and cabinet.annual_qty:
            projected = cabinet.annual_qty * (months / 12) * tmpl.quantity
            cabinet_data.append({
                'cabinet': cabinet,
                'qty_per_unit': tmpl.quantity,
                'projected': round(projected),
            })

    cabinet_data.sort(key=lambda x: x['projected'], reverse=True)

    # Stock actual
    overflow = Inventory.query.filter(
        Inventory.part_id == part_id,
        Inventory.is_active == False
    ).with_entities(func.sum(Inventory.quantity)).scalar() or 0

    return render_template('analytics/part_detail.html',
                          part=part,
                          cabinet_data=cabinet_data,
                          overflow_stock=overflow,
                          months=months)


@analytics_bp.route('/production-plan')
def production_plan():
    check = supervisor_required()
    if check:
        return check

    cabinets = CabinetType.query.order_by(CabinetType.name).all()
    months = 4

    # Para cada cabinet, calcula consumo proyectado
    for cabinet in cabinets:
        if cabinet.annual_qty:
            total_parts = sum(t.quantity for t in cabinet.parts)
            cabinet.projected_consumption = round(cabinet.annual_qty * (months / 12) * total_parts)
        else:
            cabinet.projected_consumption = 0

    return render_template('analytics/production_plan.html',
                          cabinets=cabinets,
                          months=months)


@analytics_bp.route('/production-plan/update', methods=['POST'])
def update_annual_qty():
    check = supervisor_required()
    if check:
        return jsonify({'error': 'unauthorized'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    updated = 0
    for cabinet_id_str, qty in data.items():
        try:
            cabinet_id = int(cabinet_id_str)
            cabinet = CabinetType.query.get(cabinet_id)
            if cabinet:
                cabinet.annual_qty = max(0, int(qty))
                updated += 1
        except (ValueError, TypeError):
            continue

    db.session.commit()
    return jsonify({'success': True, 'updated': updated})


@analytics_bp.route('/production-plan/simulate', methods=['POST'])
def simulate_production_plan():
    """Autocompletar annual_qty basado en tamaño del gabinete"""
    check = supervisor_required()
    if check:
        return jsonify({'error': 'unauthorized'}), 403

    cabinets = CabinetType.query.all()
    for cabinet in cabinets:
        w = cabinet.width or 0
        if w <= 9:
            cabinet.annual_qty = 150
        elif w <= 12:
            cabinet.annual_qty = 120
        elif w <= 15:
            cabinet.annual_qty = 100
        elif w <= 18:
            cabinet.annual_qty = 80
        elif w <= 21:
            cabinet.annual_qty = 60
        elif w <= 24:
            cabinet.annual_qty = 50
        else:
            cabinet.annual_qty = 36

    db.session.commit()
    return jsonify({'success': True, 'count': len(cabinets)})
