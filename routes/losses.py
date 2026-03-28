import re
from io import BytesIO
from flask import Blueprint, render_template, session, redirect, url_for, request, send_file
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

@losses_bp.route('/pdf')
def pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor']:
        return redirect(url_for('dashboard'))

    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch

    losses = Loss.query.order_by(Loss.reported_at.desc()).all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)

    styles_title = ParagraphStyle('title', fontSize=16, fontName='Helvetica-Bold', spaceAfter=4)
    styles_sub   = ParagraphStyle('sub',   fontSize=10, fontName='Helvetica', spaceAfter=2, textColor=colors.grey)

    elements = []
    elements.append(Paragraph('LOSS & DAMAGE REPORT', styles_title))
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%m/%d/%Y %I:%M %p')} · Total records: {len(losses)}",
        styles_sub))
    elements.append(Spacer(1, 0.2*inch))

    # cabecera de la tabla
    table_data = [['Date', 'Part', 'Qty', 'Reason', 'Comments', 'Reported By']]

    for loss in losses:
        table_data.append([
            loss.reported_at.strftime('%m/%d/%Y') if loss.reported_at else '—',
            loss.part.name if loss.part else '—',
            str(loss.quantity),
            loss.reason or '—',
            loss.comments or '—',
            loss.reporter.name if loss.reporter else '—',
        ])

    col_widths = [0.9*inch, 1.4*inch, 0.4*inch, 1.5*inch, 2.1*inch, 1.2*inch]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,0), colors.HexColor('#1e1b4b')),
        ('TEXTCOLOR',   (0,0), (-1,0), colors.white),
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,-1), 8),
        ('PADDING',     (0,0), (-1,-1), 5),
        ('BACKGROUND',  (0,1), (-1,-1), colors.white),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9fafb')]),
        ('GRID',        (0,0), (-1,-1), 0.4, colors.HexColor('#e5e7eb')),
        ('VALIGN',      (0,0), (-1,-1), 'TOP'),
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
