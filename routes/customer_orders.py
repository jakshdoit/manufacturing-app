from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
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
    # Just redirect to billing page pre-filled — staff sets payment method there
    return redirect(url_for('billing.index', from_order=order_number))

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

@customer_orders_bp.route('/customer-orders/api/pending')
def api_pending():
    if not logged_in(): return jsonify({'error': 'unauthorized'}), 401
    sb = get_supabase()
    orders = sb.table('customer_orders').select('*').eq('status', 'pending').order('created_at', desc=True).execute().data
    return jsonify({'orders': orders, 'count': len(orders)})
