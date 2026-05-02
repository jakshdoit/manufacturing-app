from flask import Blueprint, render_template, request, session, redirect, url_for, flash, send_file
from utils.supabase_client import get_supabase, get_settings
from utils.pdf_generator import generate_bill_pdf

billing_bp = Blueprint('billing', __name__)

def logged_in():
    return 'logged_in' in session

def next_bill_number(sb):
    res = sb.table('bills').select('id').order('id', desc=True).limit(1).execute()
    if res.data:
        return res.data[0]['id'] + 1
    return 1001

def next_buyer_number(sb):
    res = sb.table('buyers').select('id').order('id', desc=True).limit(1).execute()
    if res.data:
        return res.data[0]['id'] + 1
    return 1

@billing_bp.route('/billing')
def index():
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    products = sb.table('inventory').select('*').order('product_id').execute().data
    buyers   = sb.table('buyers').select('*').order('name').execute().data
    return render_template('billing.html', products=products, buyers=buyers, settings=settings)

@billing_bp.route('/billing/create', methods=['POST'])
def create():
    if not logged_in(): return redirect(url_for('auth.login'))
    sb            = get_supabase()
    settings      = get_settings()
    buyer_name    = request.form.get('buyer_name', '').strip()
    buyer_phone   = request.form.get('buyer_phone', '').strip()
    buyer_address = request.form.get('buyer_address', '').strip()
    buyer_id      = request.form.get('buyer_id', '').strip()
    advance       = float(request.form.get('advance_payment', 0))
    payment       = request.form.get('payment_method', 'Cash')
    notes         = request.form.get('notes', '').strip()
    product_ids   = request.form.getlist('product_id[]')
    quantities    = request.form.getlist('quantity[]')
    prices        = request.form.getlist('unit_price[]')

    if not buyer_name or not product_ids:
        flash('Buyer name and at least one product are required.', 'error')
        return redirect(url_for('billing.index'))

    # Auto-save new buyer if not selected from existing
    if not buyer_id:
        try:
            num      = next_buyer_number(sb)
            buyer_id = f"{buyer_name[:3].upper()}-{num}"
            sb.table('buyers').insert({
                'buyer_id': buyer_id,
                'name':     buyer_name,
                'phone':    buyer_phone,
                'address':  buyer_address,
                'email':    '',
                'gst_number': ''
            }).execute()
        except Exception:
            buyer_id = None

    subtotal    = sum(float(prices[i]) * int(quantities[i]) for i in range(len(product_ids)))
    balance     = round(subtotal - advance, 2)
    bill_number = str(next_bill_number(sb))

    bill_data = {
        'bill_number':     bill_number,
        'buyer_id':        buyer_id or None,
        'buyer_name':      buyer_name,
        'buyer_phone':     buyer_phone,
        'buyer_address':   buyer_address,
        'buyer_gst':       '',
        'subtotal':        subtotal,
        'discount':        0,
        'tax_percent':     0,
        'tax_amount':      0,
        'final_amount':    subtotal,
        'advance_payment': advance,
        'balance_payment': balance,
        'payment_method':  payment,
        'notes':           notes,
        'status':          'paid'
    }

    # Check stock and collect warnings
    stock_warnings = []
    for i, pid in enumerate(product_ids):
        qty = int(quantities[i])
        try:
            product = sb.table('inventory').select('*').eq('product_id', pid).single().execute().data
            available = int(product.get('stock_quantity', 0))
            if qty > available:
                stock_warnings.append(f"Product {pid}: requested {qty}, only {available} in stock.")
        except:
            pass
    for w in stock_warnings:
        flash(f'⚠️ Stock warning — {w}', 'warning')

    try:
        sb.table('bills').insert(bill_data).execute()
        for i, pid in enumerate(product_ids):
            qty     = int(quantities[i])
            price   = float(prices[i])
            product = sb.table('inventory').select('*').eq('product_id', pid).single().execute().data
            sb.table('bill_items').insert({
                'bill_number':  bill_number,
                'product_id':   pid,
                'product_name': pid,
                'quantity':     qty,
                'unit':         'pcs',
                'unit_price':   price,
                'total_price':  round(price * qty, 2)
            }).execute()
            new_stock = max(0, product['stock_quantity'] - qty)
            sb.table('inventory').update({'stock_quantity': new_stock}).eq('product_id', pid).execute()
        flash(f'Bill #{bill_number} created successfully!', 'success')
        return redirect(url_for('billing.view_bill', bill_number=bill_number))
    except Exception as e:
        flash(f'Error creating bill: {e}', 'error')
        return redirect(url_for('billing.index'))

@billing_bp.route('/billing/bill/<bill_number>')
def view_bill(bill_number):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    bill     = sb.table('bills').select('*').eq('bill_number', bill_number).single().execute().data
    items    = sb.table('bill_items').select('*').eq('bill_number', bill_number).execute().data
    return render_template('view_bill.html', bill=bill, items=items, settings=settings)

@billing_bp.route('/billing/print/<bill_number>')
def print_bill(bill_number):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    bill     = sb.table('bills').select('*').eq('bill_number', bill_number).single().execute().data
    items    = sb.table('bill_items').select('*').eq('bill_number', bill_number).execute().data
    pdf      = generate_bill_pdf(bill, items, settings)
    return send_file(pdf, mimetype='application/pdf',
                     download_name=f'Bill-{bill_number}.pdf', as_attachment=True)
