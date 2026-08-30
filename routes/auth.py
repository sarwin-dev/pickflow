"""
Centralized authentication and permission decorators for all routes.
Each decorator checks permissions and redirects if access is denied,
or allows the route to execute if authorized.

Usage:
    @admin_required
    def my_route():
        return render_template('admin.html')

    @supervisor_required
    @receiving_bp.route('/receiving')
    def receiving():
        return render_template('receiving.html')
"""

from functools import wraps
from flask import session, redirect, url_for


def admin_required(f):
    """Decorator: Only admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session['user_role'] != 'admin':
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def supervisor_required(f):
    """Decorator: Admin and supervisor roles"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session['user_role'] not in ['admin', 'supervisor']:
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def order_entry_required(f):
    """Decorator: Admin, order_entry, and supervisor roles"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session['user_role'] not in ['admin', 'order_entry', 'supervisor']:
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def picker_required(f):
    """Decorator: Admin, warehouse, and supervisor roles (for picking operations)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session['user_role'] not in ['admin', 'warehouse', 'supervisor']:
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def warehouse_supervisor_required(f):
    """Decorator: Admin, warehouse, and supervisor roles (central permission check)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session['user_role'] not in ['admin', 'warehouse', 'supervisor']:
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function
