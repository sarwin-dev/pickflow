"""
Centralized authentication and permission checks for all routes.
Each decorator checks permissions and returns the wrapped function if authorized,
or a redirect response if access is denied.
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


def inventory_required(f):
    """Decorator: Admin, supervisor, and warehouse roles"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session['user_role'] not in ['admin', 'supervisor', 'warehouse']:
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


def warehouse_required(f):
    """Decorator: Admin, warehouse, and supervisor roles (for receiving operations)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session['user_role'] not in ['admin', 'warehouse', 'supervisor']:
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def losses_required(f):
    """Decorator: Admin, supervisor, and warehouse roles (for loss reporting)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session['user_role'] not in ['admin', 'supervisor', 'warehouse']:
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function
