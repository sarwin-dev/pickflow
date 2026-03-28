from flask import Blueprint, render_template, session, redirect, url_for, request
from extensions import db
from models import WorkOrder, OrderItem, PickItem, User

supervision_bp = Blueprint('supervision', __name__, url_prefix='/supervision')

def supervisor_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None

@supervision_bp.route('/')
def index():
    check = supervisor_required()
    if check:
        return check

    status_filter = request.args.get('status', 'all')

    query = WorkOrder.query
    if status_filter in ['pending', 'in_progress', 'completed']:
        query = query.filter_by(status=status_filter)

    orders = query.order_by(WorkOrder.created_at.desc()).all()

    # calcula el progreso de cada orden
    order_stats = []
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

        order_stats.append({
            'order': order,
            'total': total,
            'picked': picked,
            'missing': missing,
            'percent': int((picked + missing) / total * 100) if total > 0 else 0
        })

    return render_template('supervision/index.html',
                           order_stats=order_stats,
                           status_filter=status_filter)
