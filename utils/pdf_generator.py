from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable, Image,
    KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import io, requests

PAGE_W, PAGE_H = A4
L_MARGIN = R_MARGIN = 15 * mm
CONTENT_W = PAGE_W - L_MARGIN - R_MARGIN

COL_W = [10*mm, 75*mm, 38*mm, 22*mm, 35*mm]

def _style(name, size=9, font='Helvetica', align=TA_LEFT, color=colors.black, leading=None):
    return ParagraphStyle(
        name,
        fontSize=size,
        fontName=font,
        alignment=align,
        textColor=color,
        leading=leading or size * 1.35,
    )

def generate_bill_pdf(bill, items, settings):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=R_MARGIN, leftMargin=L_MARGIN,
        topMargin=12*mm, bottomMargin=15*mm
    )

    elements = []

    s_company = _style('company', size=11, font='Helvetica-Bold')
    s_invoice = _style('invoice', size=22, font='Helvetica-Bold', align=TA_RIGHT)
    s_label   = _style('label',   size=9,  font='Helvetica-Bold')
    s_normal  = _style('normal',  size=9)
    s_th      = _style('th',      size=9,  font='Helvetica-Bold', align=TA_LEFT)
    s_th_r    = _style('th_r',    size=9,  font='Helvetica-Bold', align=TA_RIGHT)
    s_th_c    = _style('th_c',    size=9,  font='Helvetica-Bold', align=TA_CENTER)
    s_td      = _style('td',      size=9)
    s_td_r    = _style('td_r',    size=9,  align=TA_RIGHT)
    s_td_c    = _style('td_c',    size=9,  align=TA_CENTER)
    s_td_bold = _style('td_bold', size=9,  font='Helvetica-Bold', align=TA_RIGHT)
    s_section = _style('section', size=13, font='Helvetica-Bold', align=TA_CENTER)

    company_name  = settings.get('company_name', 'My Company')
    company_phone = settings.get('company_phone', '')
    logo_url      = settings.get('company_logo_url', '')

    logo_cell = ''
    if logo_url:
        try:
            r = requests.get(logo_url, timeout=5)
            img_buf = io.BytesIO(r.content)
            logo_cell = Image(img_buf, width=35*mm, height=20*mm)
        except Exception:
            logo_cell = Paragraph(f"<b>{company_name}</b><br/>{company_phone}", s_company)
    else:
        logo_cell = Paragraph(f"<b>{company_name}</b><br/>{company_phone}", s_company)

    header_table = Table(
        [[logo_cell, Paragraph('INVOICE', s_invoice)]],
        colWidths=[CONTENT_W * 0.45, CONTENT_W * 0.55]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=5))

    status   = 'UNPAID' if float(bill.get('balance_payment') or 0) > 0 else 'PAID'
    date_str = str(bill.get('created_at', ''))[:10]
    try:
        from datetime import datetime
        date_str = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d-%b-%Y')
    except Exception:
        pass

    bill_number = bill.get('bill_number', '')

    customer_para = Paragraph(
        f"<b>Customer details</b><br/>"
        f"{bill.get('buyer_name', '')}<br/>"
        f"{bill.get('buyer_address', '')}<br/>"
        f"{bill.get('buyer_phone', '')}",
        s_normal
    )
    order_para = Paragraph(
        f"<b>Order No.:</b> {str(bill_number).zfill(5)}<br/>"
        f"<b>Order Date:</b> {date_str}<br/>"
        f"<b>Order Status:</b> {status}",
        s_normal
    )

    info_table = Table(
        [[customer_para, order_para]],
        colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5]
    )
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN',  (1, 0), (1, 0),  'LEFT'),
    ]))
    elements.append(Spacer(1, 4*mm))
    elements.append(info_table)
    elements.append(Spacer(1, 5*mm))

    elements.append(Paragraph('Order Items', s_section))
    elements.append(Spacer(1, 3*mm))

    table_data = [[
        Paragraph('#',              s_th_c),
        Paragraph('Particulars',    s_th),
        Paragraph('Unit Price (Rs)', s_th_r),
        Paragraph('Qty',            s_th_c),
        Paragraph('Total (Rs)',     s_th_r),
    ]]

    total_qty = 0
    net_total = 0.0

    for i, item in enumerate(items, 1):
        qty         = int(item.get('quantity', 0))
        unit_price  = float(item.get('unit_price', 0))
        total_price = float(item.get('total_price', 0))
        total_qty  += qty
        net_total  += total_price

        table_data.append([
            Paragraph(str(i),               s_td_c),
            Paragraph(str(item.get('product_name', '')), s_td),
            Paragraph(f"{unit_price:,.2f}", s_td_r),
            Paragraph(str(qty),             s_td_c),
            Paragraph(f"{total_price:,.2f}", s_td_r),
        ])

    items_table = Table(table_data, colWidths=COL_W, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#f0f0f0')),
        ('LINEBELOW',     (0, 0), (-1, 0),  0.8, colors.black),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 3),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('LINEBELOW',     (0, 1), (-1, -1), 0.25, colors.HexColor('#dddddd')),
        ('BOX',           (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(items_table)
    elements.append(Spacer(1, 4*mm))

    advance   = float(bill.get('advance_payment') or 0)
    balance   = float(bill.get('balance_payment') or net_total)
    final_net = float(bill.get('final_amount') or bill.get('subtotal') or net_total)

    bal_color = colors.red if balance > 0 else colors.HexColor('#1a7a1a')

    totals_data = [
        [
            Paragraph(f"<b>Total Qty: {total_qty}</b>", s_label),
            Paragraph('Net Total', s_label),
            Paragraph(f"Rs {final_net:,.2f}", s_td_bold),
        ],
        [
            Paragraph('', s_normal),
            Paragraph('Paid', s_label),
            Paragraph(f"Rs {advance:,.2f}", s_td_bold),
        ],
        [
            Paragraph('', s_normal),
            Paragraph('Balance Due', _style('bal', size=9, font='Helvetica-Bold', color=bal_color)),
            Paragraph(f"Rs {balance:,.2f}", _style('balamt', size=9, font='Helvetica-Bold', align=TA_RIGHT, color=bal_color)),
        ],
    ]

    totals_table = Table(
        totals_data,
        colWidths=[CONTENT_W * 0.45, CONTENT_W * 0.30, CONTENT_W * 0.25]
    )
    totals_table.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 3),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
        ('LINEABOVE',     (0, 0), (-1, 0),  0.8, colors.black),
        ('LINEBELOW',     (0, -1),(-1, -1), 0.8, colors.black),
        ('ALIGN',         (2, 0), (2, -1),  'RIGHT'),
        ('BOX',           (1, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
    ]))

    elements.append(KeepTogether(totals_table))

    footer_msg = settings.get('pdf_footer', '')
    if footer_msg:
        elements.append(Spacer(1, 6*mm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(footer_msg, _style('footer', size=8, align=TA_CENTER, color=colors.HexColor('#666666'))))

    doc.build(elements)
    buffer.seek(0)
    return buffer
