from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify

inventory_bp = Blueprint('inventory', __name__)

def logged_in():
    return 'logged_in' in session

from utils.supabase_client import get_supabase, get_settings

@inventory_bp.route('/inventory')
def index():
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    search   = request.args.get('search', '')
    category = request.args.get('category', '')
    query    = sb.table('inventory').select('*').order('product_id')
    if search:
        query = query.ilike('name', f'%{search}%')
    if category:
        query = query.eq('category', category)
    products   = query.execute().data
    threshold  = settings.get('low_stock_threshold', 10)
    return render_template('inventory.html',
        products=products, settings=settings,
        threshold=threshold, search=search, category=category)

@inventory_bp.route('/inventory/add', methods=['POST'])
def add():
    if not logged_in(): return redirect(url_for('auth.login'))
    sb   = get_supabase()
    data = {
        'product_id':      request.form.get('product_id').strip(),
        'name':            request.form.get('product_id').strip(),
        'category':        request.form.get('category', 'General').strip(),
        'stock_quantity':  int(request.form.get('stock_quantity', 0)),
        'price':           float(request.form.get('price', 0)),
        'low_stock_alert': int(request.form.get('low_stock_alert', 10)),
        'unit':            'pcs',
        'description':     request.form.get('description', '').strip(),
        'image_url':       ''
    }
    try:
        sb.table('inventory').insert(data).execute()
        flash(f"Product {data['product_id']} added successfully!", 'success')
    except Exception as e:
        flash(f'Error adding product: {e}', 'error')
    return redirect(url_for('inventory.index'))

@inventory_bp.route('/inventory/edit/<product_id>', methods=['POST'])
def edit(product_id):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb   = get_supabase()
    data = {
        'name':            product_id,
        'category':        request.form.get('category', 'General').strip(),
        'stock_quantity':  int(request.form.get('stock_quantity', 0)),
        'price':           float(request.form.get('price', 0)),
        'low_stock_alert': int(request.form.get('low_stock_alert', 10)),
        'unit':            'pcs',
        'description':     request.form.get('description', '').strip(),
    }
    try:
        sb.table('inventory').update(data).eq('product_id', product_id).execute()
        flash(f'Product {product_id} updated!', 'success')
    except Exception as e:
        flash(f'Error updating product: {e}', 'error')
    return redirect(url_for('inventory.index'))

@inventory_bp.route('/inventory/delete/<product_id>', methods=['POST'])
def delete(product_id):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb = get_supabase()
    try:
        sb.table('inventory').delete().eq('product_id', product_id).execute()
        flash(f'Product {product_id} deleted!', 'success')
    except Exception as e:
        flash(f'Error deleting product: {e}', 'error')
    return redirect(url_for('inventory.index'))

@inventory_bp.route('/inventory/get/<product_id>')
def get_product(product_id):
    if not logged_in(): return jsonify({'error': 'Unauthorized'}), 401
    sb  = get_supabase()
    res = sb.table('inventory').select('*').eq('product_id', product_id).single().execute()
    return jsonify(res.data)
