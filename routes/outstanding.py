from flask import Blueprint, render_template, request, session, redirect, url_for, flash, send_file
from utils.supabase_client import get_supabase, get_settings
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import io

outstanding_bp = Blueprint('outstanding', __name__)

PAGE_W, PAGE_H = A4
L_MARGIN = R_MARGIN = 15 * mm
CONTENT_W = PAGE_W - L_MARGIN - R_MARGIN
COL_W = [10*mm, 75*mm, 38*mm, 22*mm, 35*mm]

def _style(name, size=9, font='Helvetica', align=TA_LEFT, color=colors.black):
    return ParagraphStyle(name, fontSize=size, fontName=font, alignment=align,
                          textColor=color, leading=size * 1.35)

def logged_in():
    return 'logged_in' in session

@outstanding_bp.route('/outstanding')
def index():
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    bills    = sb.table('bills').select('*').execute().data
    outstanding = []
    for b in bills:
        balance = float(b.get('balance_payment') or 0)
        if balance > 0:
            outstanding.append({
                'bill_number':    b.get('bill_number'),
                'buyer_name':     b.get('buyer_name'),
                'buyer_phone':    b.get('buyer_phone'),
                'total_amount':   float(b.get('final_amount') or 0),
                'advance_paid':   float(b.get('advance_payment') or 0),
                'balance_due':    balance,
                'date':           str(b.get('created_at',''))[:10],
                'payment_method': b.get('payment_method','')
            })
    return render_template('outstanding.html', outstanding=outstanding, settings=settings)

@outstanding_bp.route('/outstanding/settle/<bill_number>', methods=['POST'])
def settle(bill_number):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb     = get_supabase()
    amount = float(request.form.get('amount', 0))
    try:
        bill        = sb.table('bills').select('*').eq('bill_number', bill_number).single().execute().data
        advance     = float(bill.get('advance_payment') or 0)
        total       = float(bill.get('final_amount') or 0)
        new_advance = advance + amount
        new_balance = max(0, total - new_advance)
        sb.table('bills').update({
            'advance_payment': new_advance,
            'balance_payment': new_balance
        }).eq('bill_number', bill_number).execute()
        flash(f'Payment of Rs.{amount:,.2f} recorded for Bill #{bill_number}!', 'success')
        return redirect(url_for('outstanding.settlement_receipt',
                                bill_number=bill_number,
                                this_payment=amount))
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('outstanding.index'))

@outstanding_bp.route('/outstanding/settlement-receipt/<bill_number>')
def settlement_receipt(bill_number):
    if not logged_in(): return redirect(url_for('auth.login'))
    this_payment = float(request.args.get('this_payment', 0))
    sb       = get_supabase()
    settings = get_settings()
    bill     = sb.table('bills').select('*').eq('bill_number', bill_number).single().execute().data
    items    = sb.table('bill_items').select('*').eq('bill_number', bill_number).execute().data
    return render_template('settlement_receipt.html',
                           bill=bill, items=items, settings=settings,
                           bill_number=bill_number, this_payment=this_payment)

@outstanding_bp.route('/outstanding/settlement-receipt-pdf/<bill_number>')
def settlement_receipt_pdf(bill_number):
    if not logged_in(): return redirect(url_for('auth.login'))
    this_payment = float(request.args.get('this_payment', 0))
    sb       = get_supabase()
    settings = get_settings()
    bill     = sb.table('bills').select('*').eq('bill_number', bill_number).single().execute().data
    items    = sb.table('bill_items').select('*').eq('bill_number', bill_number).execute().data
    buffer   = _generate_settlement_pdf(bill, items, settings, this_payment)
    return send_file(buffer, mimetype='application/pdf',
                     download_name=f'Settlement-{bill_number}.pdf', as_attachment=True)

@outstanding_bp.route('/outstanding/receipt/<bill_number>')
def receipt(bill_number):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    bill     = sb.table('bills').select('*').eq('bill_number', bill_number).single().execute().data
    items    = sb.table('bill_items').select('*').eq('bill_number', bill_number).execute().data
    buffer   = _generate_settlement_pdf(bill, items, settings, this_payment=None)
    return send_file(buffer, mimetype='application/pdf',
                     download_name=f'Receipt-{bill_number}.pdf', as_attachment=True)

def _generate_settlement_pdf(bill, items, settings, this_payment=None):
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               rightMargin=R_MARGIN, leftMargin=L_MARGIN,
                               topMargin=12*mm, bottomMargin=15*mm)
    elements = []
    company = settings.get('company_name', 'Siddhi Arts')
    phone   = settings.get('company_phone', '')
    header = Table([[
        Paragraph(f"<b>{company}</b><br/>{phone}", _style('co', size=11, font='Helvetica-Bold')),
        Paragraph('PAYMENT RECEIPT', _style('title', size=20, font='Helvetica-Bold', align=TA_RIGHT))
    ]], colWidths=[CONTENT_W * 0.45, CONTENT_W * 0.55])
    header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elements.append(header)
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=5))
    date_str = str(bill.get('created_at',''))[:10]
    try:
        from datetime import datetime
        date_str = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d-%b-%Y')
    except:
        pass
    bill_number = bill.get('bill_number', '')
    info = Table([[
        Paragraph(f"<b>Received From:</b> {bill.get('buyer_name','')}<br/><b>Phone:</b> {bill.get('buyer_phone','')}<br/><b>Address:</b> {bill.get('buyer_address','')}", _style('info', size=9)),
        Paragraph(f"<b>Receipt No.:</b> {str(bill_number).zfill(5)}<br/><b>Date:</b> {date_str}<br/><b>Payment:</b> {bill.get('payment_method','Cash')}", _style('order', size=9))
    ]], colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5])
    info.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(Spacer(1, 4*mm))
    elements.append(info)
    elements.append(Spacer(1, 5*mm))
    elements.append(Paragraph('Order Items', _style('sec', size=13, font='Helvetica-Bold', align=TA_CENTER)))
    elements.append(Spacer(1, 3*mm))
    table_data = [[
        Paragraph('#',           _style('th_c',  size=9, font='Helvetica-Bold', align=TA_CENTER)),
        Paragraph('Particulars', _style('th',    size=9, font='Helvetica-Bold')),
        Paragraph('Unit Price',  _style('th_r',  size=9, font='Helvetica-Bold', align=TA_RIGHT)),
        Paragraph('Qty',         _style('th_c2', size=9, font='Helvetica-Bold', align=TA_CENTER)),
        Paragraph('Total',       _style('th_r2', size=9, font='Helvetica-Bold', align=TA_RIGHT)),
    ]]
    total_qty = 0
    for i, item in enumerate(items, 1):
        qty         = int(item.get('quantity', 0))
        unit_price  = float(item.get('unit_price', 0))
        total_price = float(item.get('total_price', 0))
        total_qty  += qty
        table_data.append([
            Paragraph(str(i),                            _style('td_c',  size=9, align=TA_CENTER)),
            Paragraph(str(item.get('product_name', '')), _style('td',    size=9)),
            Paragraph(f"Rs.{unit_price:,.2f}",           _style('td_r',  size=9, align=TA_RIGHT)),
            Paragraph(str(qty),                          _style('td_c2', size=9, align=TA_CENTER)),
            Paragraph(f"Rs.{total_price:,.2f}",          _style('td_r2', size=9, align=TA_RIGHT)),
        ])
    items_table = Table(table_data, colWidths=COL_W, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  colors.HexColor('#f0f0f0')),
        ('LINEBELOW',     (0,0), (-1,0),  0.8, colors.black),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 3),
        ('RIGHTPADDING',  (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('LINEBELOW',     (0,1), (-1,-1), 0.25, colors.HexColor('#dddddd')),
        ('BOX',           (0,0), (-1,-1), 0.5, colors.black),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 4*mm))
    total      = float(bill.get('final_amount') or 0)
    total_paid = float(bill.get('advance_payment') or 0)
    balance    = float(bill.get('balance_payment') or 0)
    bal_color  = colors.red if balance > 0 else colors.HexColor('#1a7a1a')
    totals_rows = [
        [Paragraph(f"<b>Total Qty: {total_qty}</b>", _style('tql', size=9, font='Helvetica-Bold')),
         Paragraph('Net Total', _style('ntl', size=9, font='Helvetica-Bold')),
         Paragraph(f"Rs. {total:,.2f}", _style('ntr', size=9, font='Helvetica-Bold', align=TA_RIGHT))],
        [Paragraph('', _style('e1', size=9)),
         Paragraph('Total Paid', _style('pl', size=9, font='Helvetica-Bold')),
         Paragraph(f"Rs. {total_paid:,.2f}", _style('pr', size=9, font='Helvetica-Bold', align=TA_RIGHT))],
    ]
    if this_payment is not None:
        totals_rows.append([
            Paragraph('', _style('e2', size=9)),
            Paragraph('This Payment', _style('tpl', size=9, font='Helvetica-Bold', color=colors.HexColor('#e91e8c'))),
            Paragraph(f"Rs. {this_payment:,.2f}", _style('tpr', size=9, font='Helvetica-Bold', align=TA_RIGHT, color=colors.HexColor('#e91e8c'))),
        ])
    totals_rows.append([
        Paragraph('', _style('e3', size=9)),
        Paragraph('Balance Due', _style('bl', size=9, font='Helvetica-Bold', color=bal_color)),
        Paragraph(f"Rs. {balance:,.2f}", _style('br', size=9, font='Helvetica-Bold', align=TA_RIGHT, color=bal_color)),
    ])
    totals_table = Table(totals_rows, colWidths=[CONTENT_W*0.45, CONTENT_W*0.30, CONTENT_W*0.25])
    totals_table.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 3),
        ('RIGHTPADDING',  (0,0), (-1,-1), 3),
        ('LINEABOVE',     (0,0), (-1,0),  0.8, colors.black),
        ('LINEBELOW',     (0,-1),(-1,-1), 0.8, colors.black),
        ('ALIGN',         (2,0), (2,-1),  'RIGHT'),
        ('BOX',           (1,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
    ]))
    elements.append(KeepTogether(totals_table))
    footer = settings.get('pdf_footer', 'Thank you for your business!')
    if footer:
        elements.append(Spacer(1, 6*mm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(footer, _style('footer', size=8, align=TA_CENTER, color=colors.HexColor('#666666'))))
    doc.build(elements)
    buffer.seek(0)
    return buffer
