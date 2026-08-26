import re
from io import BytesIO
from flask import Blueprint, render_template, session, redirect, url_for, request, send_file
from extensions import db
from models import Loss, Part
from datetime import datetime
from routes.auth import losses_required

losses_bp = Blueprint('losses', __name__, url_prefix='/losses')

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

@losses_bp.route('/pdf')
def pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor']:
        return redirect(url_for('dashboard'))

    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
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

    elements = [
        Paragraph('LOSS & DAMAGE REPORT', title_s),
        Paragraph(f"Generated: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}  ·  Total records: {len(losses)}", meta_s),
    ]

    table_data = [['Part', 'Qty', 'Reason / Comments', 'Reported By', 'Date']]
    for loss in losses:
        reason = loss.reason or '—'
        if loss.comments:
            reason += f"\n{loss.comments}"
        table_data.append([
            loss.part.name if loss.part else '—',
            f"-{loss.quantity}",
            reason,
            loss.reporter.name if loss.reporter else '—',
            loss.reported_at.strftime('%m/%d/%Y') if loss.reported_at else '—',
        ])

    t = Table(table_data, colWidths=[1.8*inch, 0.5*inch, 2.8*inch, 1.3*inch, 1.1*inch], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), navy),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('PADDING',    (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light]),
        ('GRID',       (0,0), (-1,-1), 0.4, border),
        ('VALIGN',     (0,0), (-1,-1), 'TOP'),
        ('TEXTCOLOR',  (1,1), (1,-1), red),
        ('FONTNAME',   (1,1), (1,-1), 'Helvetica-Bold'),
        ('ALIGN',      (1,0), (1,-1), 'CENTER'),
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)

    filename = f"LossReport_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(buffer, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)

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
