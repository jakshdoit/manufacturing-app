from flask import Blueprint, render_template, session, redirect, url_for
from utils.supabase_client import get_supabase, get_settings

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    products = sb.table('inventory').select('*').execute()
    total_products = len(products.data)
    threshold  = settings.get('low_stock_threshold', 10)
    low_stock  = [p for p in products.data if p['stock_quantity'] <= threshold]
    bills = sb.table('bills').select('*').order('created_at', desc=True).execute()
    total_bills  = len(bills.data)
    recent_bills = bills.data[:5]
    for b in recent_bills:
        b['final_amount'] = float(b.get('final_amount') or 0)
    return render_template('dashboard.html',
        settings=settings,
        total_products=total_products,
        low_stock=low_stock,
        total_bills=total_bills,
        recent_bills=recent_bills,
        threshold=threshold
    )
