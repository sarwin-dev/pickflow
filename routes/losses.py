import re
from flask import Blueprint, render_template, session, redirect, url_for, request
from extensions import db
from models import Loss, Part
from datetime import datetime

losses_bp = Blueprint('losses', __name__, url_prefix='/losses')

def losses_required():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor', 'warehouse']:
        return redirect(url_for('dashboard'))
    return None

@losses_bp.route('/')
def index():
    check = losses_required()
    if check:
        return check

    losses = Loss.query.order_by(Loss.reported_at.desc()).limit(100).all()
    parts = Part.query.order_by(Part.name).all()
    return render_template('losses/index.html', losses=losses, parts=parts)

@losses_bp.route('/report', methods=['POST'])
def report():
    check = losses_required()
    if check:
        return check

    part_id = request.form.get('part_id')
    part_name_raw = request.form.get('part_name', '').strip()

    if not part_id and not part_name_raw:
        return redirect(url_for('losses.index'))

    if not part_id:
        formatted = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', part_name_raw)
        formatted = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', formatted)
        part_name = ' '.join(formatted.split()).title()
        part = Part.query.filter(Part.name.ilike(part_name)).first()
        if not part:
            part = Part(name=part_name)
            db.session.add(part)
            db.session.flush()
        part_id = part.id

    quantity = int(request.form.get('quantity', 1))
    reason = request.form.get('reason', '').strip() or None
    comments = request.form.get('comments', '').strip() or None

    new_loss = Loss(
        part_id=part_id,
        quantity=quantity,
        reason=reason,
        comments=comments,
        reported_by=session['user_id'],
        reported_at=datetime.utcnow()
    )
    db.session.add(new_loss)
    db.session.commit()
    return redirect(url_for('losses.index'))

@losses_bp.route('/delete/<int:loss_id>')
def delete(loss_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor']:
        return redirect(url_for('dashboard'))
    loss = Loss.query.get(loss_id)
    if loss:
        db.session.delete(loss)
        db.session.commit()
    return redirect(url_for('losses.index'))
