from flask import Blueprint, render_template, request, session, redirect, url_for
from utils.supabase_client import get_supabase, get_settings

orders_bp = Blueprint('orders', __name__)

def logged_in():
    return 'logged_in' in session

@orders_bp.route('/orders')
def index():
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    search   = request.args.get('search', '')
    query    = sb.table('bills').select('*').order('created_at', desc=True)
    if search:
        query = query.ilike('buyer_name', f'%{search}%')
    bills = query.execute().data
    return render_template('orders.html', bills=bills, settings=settings, search=search)

@orders_bp.route('/orders/<bill_number>')
def detail(bill_number):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    bill     = sb.table('bills').select('*').eq('bill_number', bill_number).single().execute().data
    items    = sb.table('bill_items').select('*').eq('bill_number', bill_number).execute().data
    return render_template('view_bill.html', bill=bill, items=items, settings=settings)
