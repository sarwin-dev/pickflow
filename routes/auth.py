"""
Centralized authentication and permission checks for all routes.
Each function checks permissions and returns None if authorized,
or a redirect response if access is denied.

Usage:
    check = admin_required()
    if check:
        return check
"""

from flask import session, redirect, url_for


def admin_required():
    """Only admin role"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] != 'admin':
        return redirect(url_for('dashboard'))
    return None


def supervisor_required():
    """Admin and supervisor roles"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None


def inventory_required():
    """DEPRECATED: Use warehouse_supervisor_required() instead. Admin, supervisor, and warehouse roles"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor', 'warehouse']:
        return redirect(url_for('dashboard'))
    return None


def order_entry_required():
    """Admin, order_entry, and supervisor roles"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'order_entry', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None


def picker_required():
    """Admin, warehouse, and supervisor roles (for picking operations)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'warehouse', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None


def warehouse_required():
    """DEPRECATED: Use warehouse_supervisor_required() instead. Admin, warehouse, and supervisor roles (for receiving operations)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'warehouse', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None


def losses_required():
    """DEPRECATED: Use warehouse_supervisor_required() instead. Admin, supervisor, and warehouse roles (for loss reporting)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'supervisor', 'warehouse']:
        return redirect(url_for('dashboard'))
    return None


def warehouse_supervisor_required():
    """Admin, warehouse, and supervisor roles (central permission check)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_role'] not in ['admin', 'warehouse', 'supervisor']:
        return redirect(url_for('dashboard'))
    return None


# Compatibility aliases — migration in progress to warehouse_supervisor_required()
# These redirect old imports to the centralized permission check.
# Remove after updating all route files to use warehouse_supervisor_required() directly.
warehouse_required = warehouse_supervisor_required
inventory_required = warehouse_supervisor_required
losses_required = warehouse_supervisor_required
