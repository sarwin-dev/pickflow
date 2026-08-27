import re
from io import BytesIO
from flask import Blueprint, render_template, session, redirect, url_for, request, send_file
from extensions import db
from models import Loss, Part
from datetime import datetime, timedelta
from routes.auth import losses_required
from sqlalchemy import func

losses_bp = Blueprint('losses', __name__, url_prefix='/losses')

@losses_bp.route('/')
def index():
    check = losses_required()
    if check:
        return check

    period = request.args.get('period', 'all')
    category = request.args.get('category', '')

    query = Loss.query
    now = datetime.utcnow()

    if period == 'today':
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(Loss.reported_at >= today_start)
    elif period == 'week':
        week_ago = now - timedelta(days=7)
        query = query.filter(Loss.reported_at >= week_ago)
    elif period == 'month':
        month_ago = now - timedelta(days=30)
        query = query.filter(Loss.reported_at >= month_ago)

    if category:
        query = query.filter(Loss.category == category)

    losses = query.order_by(Loss.reported_at.desc()).limit(100).all()
    parts = Part.query.order_by(Part.name).all()

    summary_by_category = {}
    for cat in ['damage', 'lost', 'expired', 'defect']:
        total = db.session.query(func.sum(Loss.quantity)).filter(Loss.category == cat).scalar() or 0
        summary_by_category[cat] = total

    top_parts_query = db.session.query(
        Part.name,
        func.sum(Loss.quantity).label('total_qty')
    ).join(Loss).group_by(Part.id, Part.name).order_by(func.sum(Loss.quantity).desc()).limit(5).all()
    top_parts = [{'name': name, 'quantity': qty} for name, qty in top_parts_query]

    return render_template('losses/index.html',
                           losses=losses,
                           parts=parts,
                           summary_by_category=summary_by_category,
                           top_parts=top_parts,
                           period=period,
                           category=category)

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
            return redirect(url_for('losses.index'))
        part_id = part.id

    quantity = int(request.form.get('quantity', 1))
    reason = request.form.get('reason', '').strip() or None
    category = request.form.get('category', '').strip() or None
    comments = request.form.get('comments', '').strip() or None

    new_loss = Loss(
        part_id=part_id,
        quantity=quantity,
        reason=reason,
        category=category,
        comments=comments,
        reported_by=session['user_id'],
        reported_at=datetime.utcnow()
    )
    db.session.add(new_loss)
    db.session.commit()
    return redirect(url_for('losses.index'))

@losses_bp.route('/pdf')
def pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor']:
        return redirect(url_for('dashboard'))

    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch

    losses = Loss.query.order_by(Loss.reported_at.desc()).all()
    navy  = colors.HexColor('#1e1b4b')
    light = colors.HexColor('#f9fafb')
    border= colors.HexColor('#e5e7eb')
    red   = colors.HexColor('#dc2626')

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)

    title_s = ParagraphStyle('t', fontSize=15, fontName='Helvetica-Bold', textColor=navy, spaceAfter=2)
    meta_s  = ParagraphStyle('m', fontSize=9,  fontName='Helvetica', textColor=colors.HexColor('#6b7280'), spaceAfter=10)
    summary_title_s = ParagraphStyle('st', fontSize=12, fontName='Helvetica-Bold', textColor=navy, spaceAfter=8)

    elements = [
        Paragraph('LOSS & DAMAGE REPORT', title_s),
        Paragraph(f"Generated: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}  ·  Total records: {len(losses)}", meta_s),
    ]

    table_data = [['Part', 'Qty', 'Category', 'Reason / Comments', 'Reported By', 'Date']]
    for loss in losses:
        reason = loss.reason or '—'
        if loss.comments:
            reason += f"\n{loss.comments}"
        table_data.append([
            loss.part.name if loss.part else '—',
            f"-{loss.quantity}",
            loss.category or '—',
            reason,
            loss.reporter.name if loss.reporter else '—',
            loss.reported_at.strftime('%m/%d/%Y') if loss.reported_at else '—',
        ])

    t = Table(table_data, colWidths=[1.5*inch, 0.4*inch, 0.8*inch, 2.3*inch, 1.0*inch, 1.0*inch], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), navy),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 7),
        ('PADDING',    (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light]),
        ('GRID',       (0,0), (-1,-1), 0.4, border),
        ('VALIGN',     (0,0), (-1,-1), 'TOP'),
        ('TEXTCOLOR',  (1,1), (1,-1), red),
        ('FONTNAME',   (1,1), (1,-1), 'Helvetica-Bold'),
        ('ALIGN',      (1,0), (1,-1), 'CENTER'),
    ]))
    elements.append(t)

    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph('Summary by Category', summary_title_s))

    summary_data = [['Category', 'Total Qty']]
    for cat in ['damage', 'lost', 'expired', 'defect']:
        total = db.session.query(func.sum(Loss.quantity)).filter(Loss.category == cat).scalar() or 0
        summary_data.append([cat.capitalize(), str(total)])

    summary_table = Table(summary_data, colWidths=[2.0*inch, 1.0*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), navy),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('PADDING',    (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light]),
        ('GRID',       (0,0), (-1,-1), 0.4, border),
        ('ALIGN',      (0,0), (-1,-1), 'LEFT'),
        ('ALIGN',      (1,0), (1,-1), 'CENTER'),
    ]))
    elements.append(summary_table)

    doc.build(elements)
    buffer.seek(0)

    filename = f"LossReport_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(buffer, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)

@losses_bp.route('/edit/<int:loss_id>', methods=['GET', 'POST'])
def edit(loss_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor']:
        return redirect(url_for('dashboard'))

    loss = Loss.query.get(loss_id)
    if not loss:
        return redirect(url_for('losses.index'))

    if request.method == 'POST':
        loss.quantity = int(request.form.get('quantity', loss.quantity))
        loss.category = request.form.get('category', '').strip() or None
        loss.reason = request.form.get('reason', '').strip() or None
        loss.comments = request.form.get('comments', '').strip() or None
        db.session.commit()
        return redirect(url_for('losses.index'))

    return render_template('losses/edit.html', loss=loss)

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
