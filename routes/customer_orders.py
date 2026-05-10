from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.supabase_client import get_supabase, get_settings

customer_orders_bp = Blueprint('customer_orders', __name__)

def logged_in():
    return 'logged_in' in session

@customer_orders_bp.route('/customer-orders')
def index():
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    status   = request.args.get('status', 'pending')
    orders   = sb.table('customer_orders').select('*').eq('status', status).order('created_at', desc=True).execute().data
    return render_template('customer_orders.html', orders=orders, settings=settings, status=status)

@customer_orders_bp.route('/customer-orders/<order_number>')
def detail(order_number):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    order    = sb.table('customer_orders').select('*').eq('order_number', order_number).single().execute().data
    items    = sb.table('customer_order_items').select('*').eq('order_number', order_number).execute().data
    return render_template('customer_order_detail.html', order=order, items=items, settings=settings)

@customer_orders_bp.route('/customer-orders/convert/<order_number>', methods=['POST'])
def convert_to_bill(order_number):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()

    order    = sb.table('customer_orders').select('*').eq('order_number', order_number).single().execute().data
    items    = sb.table('customer_order_items').select('*').eq('order_number', order_number).execute().data

    # Get next bill number
    res = sb.table('bills').select('id').order('id', desc=True).limit(1).execute()
    bill_number = str(res.data[0]['id'] + 1) if res.data else '1001'

    subtotal = sum(float(i['total_price']) for i in items)

    try:
        # Create buyer if not exists
        buyer_res = sb.table('buyers').select('*').eq('phone', order['customer_phone']).execute()
        if buyer_res.data:
            buyer_id = buyer_res.data[0]['buyer_id']
        else:
            bres = sb.table('buyers').select('id').order('id', desc=True).limit(1).execute()
            num  = bres.data[0]['id'] + 1 if bres.data else 1
            buyer_id = f"{order['customer_name'][:3].upper()}-{num}"
            sb.table('buyers').insert({
                'buyer_id': buyer_id,
                'name':     order['customer_name'],
                'phone':    order['customer_phone'],
                'address':  '',
                'email':    '',
                'gst_number': ''
            }).execute()

        # Create bill
        sb.table('bills').insert({
            'bill_number':     bill_number,
            'buyer_id':        buyer_id,
            'buyer_name':      order['customer_name'],
            'buyer_phone':     order['customer_phone'],
            'buyer_address':   '',
            'buyer_gst':       '',
            'subtotal':        subtotal,
            'discount':        0,
            'tax_percent':     0,
            'tax_amount':      0,
            'final_amount':    subtotal,
            'advance_payment': 0,
            'balance_payment': subtotal,
            'payment_method':  'Cash',
            'notes':           order.get('notes', ''),
            'status':          'paid'
        }).execute()

        # Create bill items + deduct stock
        for item in items:
            sb.table('bill_items').insert({
                'bill_number':  bill_number,
                'product_id':   item['product_id'],
                'product_name': item['product_name'],
                'quantity':     item['quantity'],
                'unit':         'pcs',
                'unit_price':   item['unit_price'],
                'total_price':  item['total_price']
            }).execute()

            product = sb.table('inventory').select('*').eq('product_id', item['product_id']).single().execute().data
            new_stock = max(0, product['stock_quantity'] - item['quantity'])
            sb.table('inventory').update({'stock_quantity': new_stock}).eq('product_id', item['product_id']).execute()

        # Mark order as converted
        sb.table('customer_orders').update({'status': 'converted'}).eq('order_number', order_number).execute()

        flash(f'Order #{order_number} converted to Bill #{bill_number} successfully!', 'success')
        return redirect(url_for('billing.view_bill', bill_number=bill_number))

    except Exception as e:
        flash(f'Error converting order: {e}', 'error')
        return redirect(url_for('customer_orders.detail', order_number=order_number))

@customer_orders_bp.route('/customer-orders/cancel/<order_number>', methods=['POST'])
def cancel(order_number):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb = get_supabase()
    try:
        sb.table('customer_orders').update({'status': 'cancelled'}).eq('order_number', order_number).execute()
        flash(f'Order #{order_number} cancelled.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('customer_orders.index'))

from flask import jsonify

@customer_orders_bp.route('/customer-orders/api/pending')
def api_pending():
    if not logged_in(): return jsonify({'error': 'unauthorized'}), 401
    sb = get_supabase()
    orders = sb.table('customer_orders').select('*').eq('status', 'pending').order('created_at', desc=True).execute().data
    return jsonify({'orders': orders, 'count': len(orders)})
