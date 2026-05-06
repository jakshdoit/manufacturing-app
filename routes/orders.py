from flask import Blueprint, render_template, request, session, redirect, url_for
from utils.supabase_client import get_supabase, get_settings

orders_bp = Blueprint('orders', __name__)

def logged_in():
    return 'logged_in' in session

@orders_bp.route('/orders')
def index():
    if not logged_in(): return redirect(url_for('auth.login'))
    sb        = get_supabase()
    settings  = get_settings()
    search    = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')

    query = sb.table('bills').select('*').order('created_at', desc=True)

    if search:
        query = query.ilike('buyer_name', f'%{search}%')
    if date_from:
        query = query.gte('created_at', f'{date_from}T00:00:00')
    if date_to:
        query = query.lte('created_at', f'{date_to}T23:59:59')

    bills = query.execute().data

    for b in bills:
        b['final_amount']    = float(b.get('final_amount') or 0)
        b['subtotal']        = float(b.get('subtotal') or 0)
        b['tax_amount']      = float(b.get('tax_amount') or 0)
        b['discount']        = float(b.get('discount') or 0)

    return render_template('orders.html',
        bills=bills, settings=settings,
        search=search, date_from=date_from, date_to=date_to)

@orders_bp.route('/orders/<bill_number>')
def detail(bill_number):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    bill     = sb.table('bills').select('*').eq('bill_number', bill_number).single().execute().data
    items    = sb.table('bill_items').select('*').eq('bill_number', bill_number).execute().data
    return render_template('view_bill.html', bill=bill, items=items, settings=settings)
