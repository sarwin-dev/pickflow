from flask import Blueprint, render_template, session, redirect, url_for, request
from extensions import db
from models import WorkOrder, OrderItem, PickItem
from datetime import date as date_type
from sqlalchemy import nullslast
from routes.auth import supervisor_required

supervision_bp = Blueprint('supervision', __name__, url_prefix='/supervision')

@supervision_bp.route('/')
def index():
    check = supervisor_required()
    if check:
        return check

    status_filter = request.args.get('status', 'all')

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
                           status_filter=status_filter)
