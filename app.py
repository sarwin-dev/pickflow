from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from extensions import db

app = Flask(__name__)
app.secret_key = 'cabinets_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://cabinets_user:cabinets123@localhost/cabinets_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def inicio():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        from models import User
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = user.name
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid email or password'
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============================================
# REGISTRAMOS LOS BLUEPRINTS
# cada modulo se conecta a la app aqui
# ============================================
from routes.admin import admin_bp
app.register_blueprint(admin_bp)

from routes.receiving import receiving_bp
app.register_blueprint(receiving_bp)

from routes.orders import orders_bp
app.register_blueprint(orders_bp)

if __name__ == '__main__':
    app.run(debug=True)