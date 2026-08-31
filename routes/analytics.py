from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from extensions import db
from models import Part, Inventory, CabinetType, PartTemplate, WarehouseConfig, WorkOrder, OrderItem
from sqlalchemy import func
from routes.auth import supervisor_required

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.route('/')
@supervisor_required
def index():
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
@supervisor_required
def parts_analytics():
    from datetime import datetime

    period_months = request.args.get('period_months', 1, type=int)
    period_months = max(1, min(24, period_months))

    def calcular_proyeccion():
        completed_orders = WorkOrder.query.filter(
            WorkOrder.status == 'completed',
            WorkOrder.is_simulated == False
        ).all()

        consumption_real = {}
        history_months_count = 0
        fuente = 'estimate'

        if completed_orders:
            fuente = 'history'
            oldest_order = min(o.created_at for o in completed_orders)
            newest_order = max(o.created_at for o in completed_orders)
            history_days = (newest_order - oldest_order).days
            history_months_count = max(history_days / 30.0, 1)

            for order in completed_orders:
                for item in order.items:
                    for part_template in item.cabinet.parts:
                        consumption_real[part_template.part_id] = consumption_real.get(
                            part_template.part_id, 0
                        ) + part_template.quantity

            for part_id in consumption_real:
                monthly_avg = consumption_real[part_id] / history_months_count
                consumption_real[part_id] = monthly_avg
        else:
            history_months_count = 0
            for cabinet in CabinetType.query.filter(CabinetType.annual_qty > 0).all():
                for tmpl in cabinet.parts:
                    monthly_avg = (cabinet.annual_qty / 12) * tmpl.quantity
                    consumption_real[tmpl.part_id] = consumption_real.get(tmpl.part_id, 0) + monthly_avg

        overflow = dict(
            db.session.query(Inventory.part_id, func.sum(Inventory.quantity))
            .filter(Inventory.is_active == False)
            .group_by(Inventory.part_id)
            .all()
        )

        rows = []
        part_ids = list(consumption_real.keys())
        parts = {p.id: p for p in Part.query.filter(Part.id.in_(part_ids)).all()}

        for part_id, monthly_avg in consumption_real.items():
            part = parts.get(part_id)
            if not part:
                continue
            proyeccion = monthly_avg * period_months
            stock = overflow.get(part_id, 0)
            cantidad_a_pedir = max(0, int(proyeccion - stock))

            rows.append({
                'part': part,
                'consumo_mensual': round(monthly_avg, 1),
                'proyeccion': round(proyeccion),
                'stock': stock,
                'cantidad_a_pedir': cantidad_a_pedir,
            })

        rows.sort(key=lambda r: r['proyeccion'], reverse=True)
        for i, row in enumerate(rows, 1):
            row['rank'] = i

        critical_count = sum(1 for r in rows if r['stock'] < r['consumo_mensual'])

        return rows, fuente, history_months_count, critical_count

    rows, fuente, history_months_count, critical_count = calcular_proyeccion()

    return render_template('analytics/parts.html', rows=rows, period_months=period_months,
                          fuente=fuente, history_months=history_months_count,
                          critical_count=critical_count)


@analytics_bp.route('/parts/<int:part_id>')
@supervisor_required
def part_detail(part_id):
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
@supervisor_required
def production_plan():
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
@supervisor_required
def update_annual_qty():
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
@supervisor_required
def simulate_production_plan():
    """Autocompletar annual_qty basado en tamaño del gabinete"""
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


@analytics_bp.route('/production-plan/calculate-from-history', methods=['POST'])
@supervisor_required
def calculate_from_history():
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    twelve_months_ago = now - timedelta(days=365)

    # Busca órdenes completadas (no simuladas) de últimos 12 meses
    completed_orders = WorkOrder.query.filter(
        WorkOrder.status == 'completed',
        WorkOrder.is_simulated == False,
        WorkOrder.created_at >= twelve_months_ago
    ).all()

    if not completed_orders:
        return jsonify({'success': True, 'orders_processed': 0, 'cabinets_updated': 0, 'message': 'No completed orders found in history'})

    # Calcula la antigüedad del historial en meses
    if completed_orders:
        oldest_order = min(o.created_at for o in completed_orders)
        history_days = (now - oldest_order).days
        history_months = max(history_days / 30.0, 1)  # mínimo 1 mes
    else:
        history_months = 1

    # Cuenta OrderItem por cabinet_type_id
    cabinet_counts = {}
    for order in completed_orders:
        for item in order.items:
            cabinet_id = item.cabinet_type_id
            cabinet_counts[cabinet_id] = cabinet_counts.get(cabinet_id, 0) + 1

    # Anualiza y actualiza CabinetType
    updated_count = 0
    for cabinet_id, count in cabinet_counts.items():
        cabinet = CabinetType.query.get(cabinet_id)
        if cabinet:
            annualized_qty = int((count / history_months) * 12)
            cabinet.annual_qty = annualized_qty
            updated_count += 1

    db.session.commit()

    return jsonify({
        'success': True,
        'orders_processed': len(completed_orders),
        'cabinets_updated': updated_count,
        'history_months': round(history_months, 1),
        'message': f'Calculated annual quantities from {len(completed_orders)} orders over {round(history_months, 1)} months'
    })
