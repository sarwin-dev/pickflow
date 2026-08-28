from flask import Blueprint, render_template, session, redirect, url_for, request
from extensions import db
from models import WorkOrder, OrderItem, PickItem
from datetime import date as date_type, datetime
from sqlalchemy import nullslast, func, or_
from routes.auth import supervisor_required

supervision_bp = Blueprint('supervision', __name__, url_prefix='/supervision')

@supervision_bp.route('/')
def index():
    check = supervisor_required()
    if check:
        return check

    status_filter = request.args.get('status', 'all')

    total_active = WorkOrder.query.filter(
        or_(WorkOrder.status == 'pending', WorkOrder.status == 'in_progress')
    ).count()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = WorkOrder.query.filter(
        WorkOrder.status == 'completed',
        WorkOrder.updated_at >= today_start
    ).count()

    active_orders = WorkOrder.query.filter(
        or_(WorkOrder.status == 'pending', WorkOrder.status == 'in_progress')
    ).all()
    active_order_ids = [o.id for o in active_orders]
    total_missing = db.session.query(func.count(PickItem.id)).join(OrderItem).filter(
        OrderItem.work_order_id.in_(active_order_ids),
        PickItem.is_missing == True
    ).scalar() or 0

    query = WorkOrder.query
    if status_filter in ['pending', 'in_progress', 'completed']:
        query = query.filter_by(status=status_filter)

    orders = query.order_by(
        nullslast(WorkOrder.scheduled_date.asc()),
        WorkOrder.created_at.asc()
    ).all()

    # calcula el progreso de cada orden
    grouped = {}
    for order in orders:
        total = PickItem.query.join(OrderItem).filter(
            OrderItem.work_order_id == order.id
        ).count()
        picked = PickItem.query.join(OrderItem).filter(
            OrderItem.work_order_id == order.id,
            PickItem.is_picked == True
        ).count()
        missing = PickItem.query.join(OrderItem).filter(
            OrderItem.work_order_id == order.id,
            PickItem.is_missing == True
        ).count()

        stat = {
            'order': order,
            'total': total,
            'picked': picked,
            'missing': missing,
            'percent': int((picked + missing) / total * 100) if total > 0 else 0
        }
        grouped.setdefault(order.scheduled_date, []).append(stat)

    date_groups = sorted(grouped.items(), key=lambda x: (x[0] is None, x[0] or date_type.max))

    return render_template('supervision/index.html',
                           date_groups=date_groups,
                           status_filter=status_filter,
                           total_active=total_active,
                           completed_today=completed_today,
                           total_missing=total_missing)
