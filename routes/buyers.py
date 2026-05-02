from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from utils.supabase_client import get_supabase, get_settings

buyers_bp = Blueprint('buyers', __name__)

def logged_in():
    return 'logged_in' in session

def next_buyer_number(sb):
    res = sb.table('buyers').select('id').order('id', desc=True).limit(1).execute()
    if res.data:
        return res.data[0]['id'] + 1
    return 1

@buyers_bp.route('/buyers')
def index():
    if not logged_in(): return redirect(url_for('auth.login'))
    sb       = get_supabase()
    settings = get_settings()
    search   = request.args.get('search', '')
    query    = sb.table('buyers').select('*').order('name')
    if search:
        query = query.ilike('name', f'%{search}%')
    buyers = query.execute().data
    return render_template('buyers.html', buyers=buyers, settings=settings, search=search)

@buyers_bp.route('/buyers/add', methods=['POST'])
def add():
    if not logged_in(): return redirect(url_for('auth.login'))
    sb   = get_supabase()
    name = request.form.get('name', '').strip()
    num  = next_buyer_number(sb)
    data = {
        'buyer_id': f"{name[:3].upper()}-{num}",
        'name':     name,
        'phone':    request.form.get('phone', '').strip(),
        'email':    request.form.get('email', '').strip(),
        'address':  request.form.get('address', '').strip(),
        'gst_number': '',
    }
    try:
        sb.table('buyers').insert(data).execute()
        flash(f"Buyer {name} added!", 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('buyers.index'))

@buyers_bp.route('/buyers/delete/<buyer_id>', methods=['POST'])
def delete(buyer_id):
    if not logged_in(): return redirect(url_for('auth.login'))
    sb = get_supabase()
    try:
        sb.table('buyers').delete().eq('buyer_id', buyer_id).execute()
        flash('Buyer deleted!', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    return redirect(url_for('buyers.index'))

@buyers_bp.route('/buyers/get/<buyer_id>')
def get_buyer(buyer_id):
    if not logged_in(): return jsonify({'error': 'Unauthorized'}), 401
    sb  = get_supabase()
    res = sb.table('buyers').select('*').eq('buyer_id', buyer_id).single().execute()
    return jsonify(res.data)
