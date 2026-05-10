from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from utils.supabase_client import get_supabase, get_settings
import uuid

portal_bp = Blueprint('portal', __name__)

def next_order_number(sb):
    res = sb.table('customer_orders').select('id').order('id', desc=True).limit(1).execute()
    if res.data:
        return res.data[0]['id'] + 1
    return 1001

@portal_bp.route('/portal')
def index():
    sb       = get_supabase()
    settings = get_settings()
    products = sb.table('inventory').select('*').gt('stock_quantity', 0).order('product_id').execute().data
    pop      = [p for p in products if p['category'] == 'POP']
    eco      = [p for p in products if p['category'] == 'Ecofriendly']
    return render_template('portal.html', pop=pop, eco=eco, settings=settings)

@portal_bp.route('/portal/submit', methods=['POST'])
def submit():
    sb            = get_supabase()
    customer_name  = request.form.get('customer_name', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    notes          = request.form.get('notes', '').strip()
    customer_address = request.form.get('customer_address', '').strip()
    product_ids    = request.form.getlist('product_id[]')
    quantities     = request.form.getlist('quantity[]')
    prices         = request.form.getlist('unit_price[]')

    if not customer_name or not customer_phone:
        flash('Please enter your name and phone number.', 'error')
        return redirect(url_for('portal.index'))

    if not product_ids:
        flash('Please add at least one product to your list.', 'error')
        return redirect(url_for('portal.index'))

    if len(customer_phone) != 10 or not customer_phone.isdigit():
        flash('Please enter a valid 10-digit phone number.', 'error')
        return redirect(url_for('portal.index'))

    order_number = str(next_order_number(sb))

    try:
        sb.table('customer_orders').insert({
            'order_number':   order_number,
            'customer_name':  customer_name,
            'customer_phone': customer_phone,
            'notes':          notes,
            'customer_address': customer_address,
            'status':         'pending'
        }).execute()

        for i, pid in enumerate(product_ids):
            qty   = int(quantities[i])
            price = float(prices[i])
            product = sb.table('inventory').select('*').eq('product_id', pid).single().execute().data
            sb.table('customer_order_items').insert({
                'order_number': order_number,
                'product_id':   pid,
                'product_name': pid,
                'quantity':     qty,
                'unit_price':   price,
                'total_price':  round(price * qty, 2)
            }).execute()

        return redirect(url_for('portal.success', order_number=order_number))
    except Exception as e:
        flash(f'Error submitting order: {e}', 'error')
        return redirect(url_for('portal.index'))

@portal_bp.route('/portal/success/<order_number>')
def success(order_number):
    sb       = get_supabase()
    settings = get_settings()
    order    = sb.table('customer_orders').select('*').eq('order_number', order_number).single().execute().data
    items    = sb.table('customer_order_items').select('*').eq('order_number', order_number).execute().data
    return render_template('portal_success.html', order=order, items=items, settings=settings)

@portal_bp.route('/qr-code')
def qr_code():
    settings = get_settings()
    return render_template('qr_code.html', settings=settings)
