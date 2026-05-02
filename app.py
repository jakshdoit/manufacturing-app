from flask import Flask, session, redirect, url_for
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mfg-app-secret-2024')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

from routes.auth      import auth_bp
from routes.dashboard import dashboard_bp
from routes.inventory import inventory_bp
from routes.billing   import billing_bp
from routes.buyers    import buyers_bp
from routes.orders    import orders_bp
from routes.settings  import settings_bp
from routes.outstanding import outstanding_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(buyers_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(outstanding_bp)

@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('dashboard.index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
