from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import Image
import io, requests

def generate_bill_pdf(bill, items, settings):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=15*mm, leftMargin=15*mm,
                            topMargin=12*mm, bottomMargin=15*mm)

    elements = []

    # Styles
    bold14   = ParagraphStyle('b14',  fontSize=14, fontName='Helvetica-Bold')
    bold12   = ParagraphStyle('b12',  fontSize=12, fontName='Helvetica-Bold')
    bold10   = ParagraphStyle('b10',  fontSize=10, fontName='Helvetica-Bold')
    normal9  = ParagraphStyle('n9',   fontSize=9,  fontName='Helvetica')
    normal10 = ParagraphStyle('n10',  fontSize=10, fontName='Helvetica')
    right12  = ParagraphStyle('r12',  fontSize=12, fontName='Helvetica-Bold', alignment=TA_RIGHT)
    center14 = ParagraphStyle('c14',  fontSize=20, fontName='Helvetica-Bold', alignment=TA_CENTER)

    company_name    = settings.get('company_name', 'My Company')
    company_phone   = settings.get('company_phone', '')
    company_address = settings.get('company_address', '')
    logo_url        = settings.get('company_logo_url', '')

    # ── HEADER: Logo left, INVOICE right ──
    logo_cell = ''
    if logo_url:
        try:
            r = requests.get(logo_url, timeout=5)
            img_buf = io.BytesIO(r.content)
            logo_cell = Image(img_buf, width=35*mm, height=20*mm)
        except:
            logo_cell = Paragraph(f"<b>{company_name}</b><br/>{company_phone}", bold12)
    else:
        logo_cell = Paragraph(f"<b>{company_name}</b><br/>{company_phone}", bold12)

    header_table = Table(
        [[logo_cell, Paragraph('INVOICE', center14)]],
        colWidths=[80*mm, 100*mm]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN',  (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',   (1,0), (1,0),   'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=6))

    # ── CUSTOMER + ORDER INFO ──
    status = 'UNPAID' if float(bill.get('balance_payment') or 0) > 0 else 'PAID'

    bill_number = bill.get('bill_number', '')
    date_str    = str(bill.get('created_at', ''))[:10]
    try:
        from datetime import datetime
        date_str = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d-%b-%Y')
    except:
        pass

    customer_info = f"""<b>Customer details</b><br/>
{bill.get('buyer_name','')}<br/>
{bill.get('buyer_address','')}.{bill.get('buyer_phone','')}"""

    order_info = f"""<b>Order No.:</b> {str(bill_number).zfill(5)}<br/>
<b>Order Date:</b> {date_str}<br/>
<b>Order Status:</b> {status}"""

    info_table = Table(
        [[Paragraph(customer_info, normal10), Paragraph(order_info, normal10)]],
        colWidths=[90*mm, 90*mm]
    )
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN',  (1,0), (1,0),  'RIGHT'),
    ]))
    elements.append(Spacer(1, 4*mm))
    elements.append(info_table)
    elements.append(Spacer(1, 6*mm))

    # ── ORDER ITEMS TITLE ──
    elements.append(Paragraph('Order items', ParagraphStyle('oi', fontSize=14, fontName='Helvetica-Bold', alignment=TA_CENTER)))
    elements.append(Spacer(1, 4*mm))

    # ── ITEMS TABLE ──
    col_widths = [10*mm, 70*mm, 35*mm, 25*mm, 35*mm]
    table_data = [[
        Paragraph('#',              ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER)),
        Paragraph('Particulars',    ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold')),
        Paragraph('Unit price (₹)', ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
        Paragraph('Quantity',       ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER)),
        Paragraph('Total (₹)',      ParagraphStyle('th', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
    ]]

    total_qty = 0
    for i, item in enumerate(items, 1):
        qty       = int(item.get('quantity', 0))
        total_qty += qty
        table_data.append([
            Paragraph(str(i),                                          ParagraphStyle('td',  fontSize=9, fontName='Helvetica', alignment=TA_CENTER)),
            Paragraph(str(item.get('product_name', '')),               ParagraphStyle('td',  fontSize=9, fontName='Helvetica')),
            Paragraph(f"{float(item.get('unit_price',0)):,.2f}",       ParagraphStyle('tdr', fontSize=9, fontName='Helvetica', alignment=TA_RIGHT)),
            Paragraph(str(qty),                                        ParagraphStyle('tdc', fontSize=9, fontName='Helvetica', alignment=TA_CENTER)),
            Paragraph(f"{float(item.get('total_price',0)):,.2f}",      ParagraphStyle('tdr', fontSize=9, fontName='Helvetica', alignment=TA_RIGHT)),
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

    # ── TOTALS ──
    net_total = float(bill.get('final_amount') or bill.get('subtotal') or 0)
    advance   = float(bill.get('advance_payment') or 0)
    balance   = float(bill.get('balance_payment') or net_total)

    totals_data = [
        ['', '', f'TOTAL QTY: {total_qty}', '', f'NET TOTAL (₹) {net_total:,.2f}'],
        ['', '', '',                         '', f'PAID (₹) {advance:,.2f}'],
        ['', '', '',                         '', f'BALANCE (₹) {balance:,.2f}'],
    ]
    totals_table = Table(totals_data, colWidths=col_widths)
    totals_table.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('ALIGN',       (2,0), (2,0),   'LEFT'),
        ('ALIGN',       (4,0), (4,-1),  'RIGHT'),
        ('LINEABOVE',   (0,0), (-1,0),  0.5, colors.black),
        ('TOPPADDING',  (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
    ]))
    elements.append(totals_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer
