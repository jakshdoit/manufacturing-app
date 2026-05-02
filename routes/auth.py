from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.supabase_client import get_settings

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        settings = get_settings()
        correct  = settings.get('app_password', 'admin123')
        if password == correct:
            session['logged_in'] = True
            return redirect(url_for('dashboard.index'))
        else:
            flash('Incorrect password. Try again.', 'error')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
