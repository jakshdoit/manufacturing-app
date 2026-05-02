from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.supabase_client import get_supabase, get_settings

settings_bp = Blueprint('settings', __name__)

def logged_in():
    return 'logged_in' in session

@settings_bp.route('/settings', methods=['GET', 'POST'])
def index():
    if not logged_in(): return redirect(url_for('auth.login'))
    sb = get_supabase()
    if request.method == 'POST':
        data = {
            'company_name':       request.form.get('company_name', '').strip(),
            'company_address':    request.form.get('company_address', '').strip(),
            'company_phone':      request.form.get('company_phone', '').strip(),
            'company_email':      request.form.get('company_email', '').strip(),
            'gst_number':         request.form.get('gst_number', '').strip(),
            'low_stock_threshold':int(request.form.get('low_stock_threshold', 10)),
            'currency_symbol':    request.form.get('currency_symbol', '₹').strip(),
            'tax_percent':        float(request.form.get('tax_percent', 18)),
        }
        new_password = request.form.get('new_password', '').strip()
        if new_password:
            data['app_password'] = new_password
        try:
            sb.table('app_settings').update(data).eq('id', 1).execute()
            flash('Settings saved successfully!', 'success')
        except Exception as e:
            flash(f'Error saving settings: {e}', 'error')
        return redirect(url_for('settings.index'))
    settings = get_settings()
    return render_template('settings.html', settings=settings)
