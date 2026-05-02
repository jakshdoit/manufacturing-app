from flask import Blueprint, render_template, request, session, redirect, url_for, flash, send_file
from utils.supabase_client import get_supabase, get_settings
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import io

outstanding_bp = Blueprint('outstanding', __name__)

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
                'bill_number':  b.get('bill_number'),
                'buyer_name':   b.get('buyer_name'),
                'buyer_phone':  b.get('buyer_phone'),
                'total_amount': float(b.get('final_amount') or 0),
                'advance_paid': float(b.get('advance_payment') or 0),
                'balance_due':  balance,
                'date':         str(b.get('created_at',''))[:10],
                'payment_method': b.get('payment_method','')
            })
    return render_template('outstanding.html',
        outstanding=outstanding,
        settings=settings
    )

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
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('outstanding.index'))

@outstanding_bp.route('/outstanding/receipt/<bill_number>')
def receipt(bill_number):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    bill     = sb.table('bills').select('*').eq('bill_number', bill_number).single().execute().data
    items    = sb.table('bill_items').select('*').eq('bill_number', bill_number).execute().data

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               rightMargin=15*mm, leftMargin=15*mm,
                               topMargin=12*mm, bottomMargin=15*mm)
    elements = []

    bold14  = ParagraphStyle('b14', fontSize=14, fontName='Helvetica-Bold')
    bold12  = ParagraphStyle('b12', fontSize=12, fontName='Helvetica-Bold')
    center  = ParagraphStyle('c',   fontSize=20, fontName='Helvetica-Bold', alignment=TA_CENTER)
    normal  = ParagraphStyle('n',   fontSize=10, fontName='Helvetica')
    right   = ParagraphStyle('r',   fontSize=12, fontName='Helvetica-Bold', alignment=TA_RIGHT)
    small   = ParagraphStyle('s',   fontSize=9,  fontName='Helvetica')

    company = settings.get('company_name', 'Siddhi Arts')
    phone   = settings.get('company_phone', '')
    address = settings.get('company_address', '')

    # Header
    header = Table([[
        Paragraph(f"<b>{company}</b><br/>{phone}<br/>{address}", bold12),
        Paragraph('PAYMENT RECEIPT', center)
    ]], colWidths=[80*mm, 100*mm])
    header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elements.append(header)
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=6))

    # Bill & Buyer info
    date_str = str(bill.get('created_at',''))[:10]
    elements.append(Spacer(1, 4*mm))
    info = Table([[
        Paragraph(f"<b>Received From:</b> {bill.get('buyer_name','')}<br/>"
                  f"<b>Phone:</b> {bill.get('buyer_phone','')}<br/>"
                  f"<b>Address:</b> {bill.get('buyer_address','')}", normal),
        Paragraph(f"<b>Receipt No.:</b> {str(bill_number).zfill(5)}<br/>"
                  f"<b>Date:</b> {date_str}<br/>"
                  f"<b>Payment:</b> {bill.get('payment_method','Cash')}", normal)
    ]], colWidths=[90*mm, 90*mm])
    info.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(info)
    elements.append(Spacer(1, 6*mm))

    # Items table
    col_widths = [10*mm, 70*mm, 35*mm, 25*mm, 35*mm]
    table_data = [[
        Paragraph('#',              ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER)),
        Paragraph('Particulars',    ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold')),
        Paragraph('Unit Price',     ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
        Paragraph('Qty',            ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER)),
        Paragraph('Total',          ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
    ]]
    total_qty = 0
    for i, item in enumerate(items, 1):
        qty = int(item.get('quantity', 0))
        total_qty += qty
        table_data.append([
            Paragraph(str(i),                                     ParagraphStyle('td', fontSize=9, fontName='Helvetica', alignment=TA_CENTER)),
            Paragraph(str(item.get('product_name','')),           ParagraphStyle('td', fontSize=9, fontName='Helvetica')),
            Paragraph(f"Rs.{float(item.get('unit_price',0)):,.2f}", ParagraphStyle('td', fontSize=9, fontName='Helvetica', alignment=TA_RIGHT)),
            Paragraph(str(qty),                                   ParagraphStyle('td', fontSize=9, fontName='Helvetica', alignment=TA_CENTER)),
            Paragraph(f"Rs.{float(item.get('total_price',0)):,.2f}", ParagraphStyle('td', fontSize=9, fontName='Helvetica', alignment=TA_RIGHT)),
        ])

    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('FONTNAME',       (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0,0), (-1,-1), 9),
        ('BOTTOMPADDING',  (0,0), (-1,-1), 4),
        ('TOPPADDING',     (0,0), (-1,-1), 4),
        ('LINEBELOW',      (0,0), (-1,0),  0.5, colors.black),
        ('LINEBELOW',      (0,1), (-1,-1), 0.3, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('ALIGN',          (0,0), (0,-1),  'CENTER'),
        ('ALIGN',          (2,0), (2,-1),  'RIGHT'),
        ('ALIGN',          (3,0), (3,-1),  'CENTER'),
        ('ALIGN',          (4,0), (4,-1),  'RIGHT'),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 6*mm))

    # Totals
    total   = float(bill.get('final_amount') or 0)
    advance = float(bill.get('advance_payment') or 0)
    balance = float(bill.get('balance_payment') or 0)

    totals = Table([
        ['', '', f'TOTAL QTY: {total_qty}', '', f'NET TOTAL   Rs.{total:,.2f}'],
        ['', '', '',                         '', f'PAID           Rs.{advance:,.2f}'],
        ['', '', '',                         '', f'BALANCE     Rs.{balance:,.2f}'],
    ], colWidths=col_widths)
    totals.setStyle(TableStyle([
        ('FONTNAME',     (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0), (-1,-1), 9),
        ('ALIGN',        (4,0), (4,-1),  'RIGHT'),
        ('LINEABOVE',    (0,0), (-1,0),  0.5, colors.black),
        ('TOPPADDING',   (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0), (-1,-1), 3),
        ('TEXTCOLOR',    (4,2), (4,2),   colors.red),
    ]))
    elements.append(totals)
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph(settings.get('pdf_footer', 'Thank you for your business!'),
                               ParagraphStyle('footer', fontSize=8, fontName='Helvetica', alignment=TA_CENTER)))

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf',
                     download_name=f'Receipt-{bill_number}.pdf', as_attachment=True)
