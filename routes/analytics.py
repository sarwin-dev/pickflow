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

    critical_count = 0

    return render_template('analytics/index.html',
                          total_parts=total_parts,
                          total_cabinets=total_cabinets,
                          critical_count=critical_count)


@analytics_bp.route('/parts')
@supervisor_required
def parts_analytics():
    from datetime import datetime, timedelta

    period_months = request.args.get('period_months', 1, type=int)
    period_months = max(1, min(24, period_months))

    history_months = request.args.get('history_months', 3, type=int)
    history_months = max(1, min(24, history_months))

    def calcular_proyeccion():
        now = datetime.utcnow()
        history_start = now - timedelta(days=history_months * 30)

        real_orders = WorkOrder.query.filter(
            WorkOrder.status == 'completed',
            WorkOrder.is_simulated == False,
            WorkOrder.created_at >= history_start
        ).all()

        simulated_orders = WorkOrder.query.filter(
            WorkOrder.status == 'completed',
            WorkOrder.is_simulated == True,
            WorkOrder.created_at >= history_start
        ).all()

        consumption_real = {}
        fuente = 'estimate'
        orders_to_use = []

        if real_orders:
            fuente = 'real'
            orders_to_use = real_orders
        elif simulated_orders:
            fuente = 'simulated'
            orders_to_use = simulated_orders

        if orders_to_use:
            for order in orders_to_use:
                for item in order.items:
                    for part_template in item.cabinet.parts:
                        consumption_real[part_template.part_id] = consumption_real.get(
                            part_template.part_id, 0
                        ) + part_template.quantity

            for part_id in consumption_real:
                monthly_avg = consumption_real[part_id] / history_months
                consumption_real[part_id] = monthly_avg
        else:
            pass

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

        return rows, fuente, critical_count

    rows, fuente, critical_count = calcular_proyeccion()

    return render_template('analytics/parts.html', rows=rows, period_months=period_months,
                          history_months=history_months, fuente=fuente,
                          critical_count=critical_count)


@analytics_bp.route('/parts/<int:part_id>')
@supervisor_required
def part_detail(part_id):
    part = Part.query.get_or_404(part_id)
    months = 4

    # Busca qué cabinet types usan esta parte
    templates = PartTemplate.query.filter_by(part_id=part_id).all()

    cabinet_data = []

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
