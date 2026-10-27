"""
routes/auth.py - login, logout and the access-control decorators.

Session keys stored after login:
    user_id, username, role, doctor_id, staff_id, display_name
"""
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from db import query

bp = Blueprint('auth', __name__)


# ---------------------------------------------------------------------
# Decorators used on every protected route
# ---------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    """Example: @role_required('admin', 'receptionist')"""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in first.', 'warning')
                return redirect(url_for('auth.login'))
            if session.get('role') not in roles:
                flash('You do not have permission to open that page.', 'danger')
                return redirect(url_for('dashboard'))
            return view(*args, **kwargs)
        return wrapped
    return decorator


# ---------------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------------
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # LEFT JOINs fetch the doctor's or staff member's name for the navbar
        user = query(
            """SELECT u.user_id, u.username, u.password_hash, u.role,
                      u.doctor_id, u.staff_id,
                      d.name AS doctor_name, s.name AS staff_name
               FROM users u
               LEFT JOIN doctors d ON d.doctor_id = u.doctor_id
               LEFT JOIN staff   s ON s.staff_id  = u.staff_id
               WHERE u.username = %s""",
            (username,), one=True)

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['doctor_id'] = user['doctor_id']
            session['staff_id'] = user['staff_id']
            session['display_name'] = user['doctor_name'] or user['staff_name'] or 'Administrator'
            flash(f"Welcome, {session['display_name']}!", 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
