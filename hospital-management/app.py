"""
app.py - Flask entry point for the Hospital Management System.

Run:  python app.py      then open http://localhost:5000
"""
import calendar
import os
from datetime import date, timedelta

import mysql.connector
from flask import Flask, redirect, render_template, request, session, url_for

from config import SECRET_KEY
from db import close_db, query
from routes.auth import bp as auth_bp, login_required
from routes.admin import bp as admin_bp
from routes.patients import bp as patients_bp
from routes.appointments import bp as appointments_bp
from routes.visits import bp as visits_bp
from routes.billing import bp as billing_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # close the DB connection at the end of every request
    app.teardown_appcontext(close_db)

    # one blueprint per module (see routes/)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(visits_bp)
    app.register_blueprint(billing_bp)

    # ---------------- template helpers ----------------
    @app.template_filter('money')
    def money(value):
        """1234.5 -> Rs. 1,234.50"""
        return f"₹{(value or 0):,.2f}"

    @app.template_filter('time12')
    def time12(value):
        """MySQL TIME comes back as timedelta -> '10:30 AM'"""
        if value is None:
            return ''
        if isinstance(value, timedelta):
            total = int(value.total_seconds())
            h, m = total // 3600, (total % 3600) // 60
        else:
            h, m = value.hour, value.minute
        suffix = 'AM' if h < 12 else 'PM'
        return f"{(h % 12) or 12}:{m:02d} {suffix}"

    @app.template_filter('age')
    def age(dob):
        if not dob:
            return ''
        t = date.today()
        return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))

    @app.template_filter('initials')
    def initials(name):
        """'Dr. Anil Mehta' -> 'AM'"""
        words = [w for w in (name or '').split() if w.lower() not in ('dr.', 'dr')]
        return ''.join(w[0] for w in words[:2]).upper() or '?'

    # ---------------- pages ----------------
    @app.route('/')
    def index():
        return redirect(url_for('dashboard'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        role = session['role']
        if role == 'admin':
            data = admin_dashboard()
        elif role == 'doctor':
            data = doctor_dashboard(session['doctor_id'])
        else:
            data = receptionist_dashboard()
        data['cal'] = month_calendar(request.args.get('month'),
                                     session['doctor_id'] if role == 'doctor' else None)
        data['today_date'] = date.today()
        return render_template('dashboard.html', **data)

    # ---------------- friendly DB error page ----------------
    @app.errorhandler(mysql.connector.Error)
    def database_error(e):
        return render_template('error.html', error=e), 500

    return app


# ---------------------------------------------------------------------
# Dashboard data. Each stat card carries the SQL used, so it can be
# shown on screen during the viva (click "SQL" on a card).
# ---------------------------------------------------------------------
def card(label, sql, params=(), color='ice', money=False, url=None):
    row = query(sql, params, one=True)
    return {'label': label, 'value': row['value'], 'sql': sql.strip(),
            'color': color, 'money': money, 'url': url}


def names(sql, params=()):
    """Return a list of names (used for the avatar stacks on the big tiles)."""
    return [r['name'] for r in query(sql, params)]


def month_calendar(month_arg, doctor_id=None):
    """
    Build a Monday-first month grid. Days that have appointments are marked.
    SQL: COUNT(*) ... GROUP BY DAY(appointment_date)
    """
    today = date.today()
    try:
        year, month = (int(x) for x in month_arg.split('-'))
        first = date(year, month, 1)
    except (AttributeError, ValueError):
        first = today.replace(day=1)
    year, month = first.year, first.month

    sql = """SELECT DAY(appointment_date) AS d, COUNT(*) AS n
             FROM appointments
             WHERE YEAR(appointment_date) = %s AND MONTH(appointment_date) = %s
               AND status <> 'Cancelled'"""
    params = [year, month]
    if doctor_id:
        sql += " AND doctor_id = %s"
        params.append(doctor_id)
    sql += " GROUP BY DAY(appointment_date)"
    counts = {r['d']: r['n'] for r in query(sql, tuple(params))}

    weeks = []
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(year, month):
        weeks.append([{'date': d, 'in_month': d.month == month, 'today': d == today,
                       'count': counts.get(d.day, 0) if d.month == month else 0}
                      for d in week])
    prev_m = (first - timedelta(days=1)).replace(day=1)
    next_m = (first + timedelta(days=32)).replace(day=1)
    return {'title': first.strftime('%B %Y'), 'weeks': weeks,
            'prev': prev_m.strftime('%Y-%m'), 'next': next_m.strftime('%Y-%m'),
            'total': sum(counts.values())}


def admin_dashboard():
    cards = [
        card('Total patients', "SELECT COUNT(*) AS value FROM patients",
             color='ice', url=url_for('patients.patient_list')),
        card("Today's appointments",
             "SELECT COUNT(*) AS value FROM appointments\n"
             "WHERE appointment_date = CURDATE() AND status <> 'Cancelled'",
             color='gold'),
        card('Revenue collected', "SELECT COALESCE(SUM(amount), 0) AS value FROM payments",
             color='plum', money=True, url=url_for('billing.bill_list')),
    ]
    tiles = [
        {'title': 'Doctors', 'color': 'ice', 'url': url_for('admin.doctors'),
         'people': names("SELECT name FROM doctors ORDER BY doctor_id LIMIT 4"),
         'count': query("SELECT COUNT(*) AS n FROM doctors", one=True)['n'],
         'chip': f"{query('SELECT COUNT(*) AS n FROM departments', one=True)['n']} depts"},
        {'title': 'Patients', 'color': 'plum', 'url': url_for('patients.patient_list'),
         'people': names("SELECT name FROM patients ORDER BY patient_id DESC LIMIT 4"),
         'count': query("SELECT COUNT(*) AS n FROM patients", one=True)['n'],
         'chip': f"+{query('SELECT COUNT(*) AS n FROM patients WHERE DATE(created_at) = CURDATE()', one=True)['n']} today"},
    ]
    money_sql = """SELECT COALESCE(SUM(total), 0) AS billed,
       COALESCE(SUM(amount_paid), 0) AS collected
FROM bill_summary"""
    # JOIN + GROUP BY: appointments per department
    dept_sql = """SELECT dep.name, COUNT(a.appointment_id) AS appointments,
       SUM(a.status = 'Completed') AS completed
FROM departments dep
LEFT JOIN doctors d      ON d.department_id = dep.department_id
LEFT JOIN appointments a ON a.doctor_id = d.doctor_id
GROUP BY dep.department_id, dep.name
ORDER BY appointments DESC"""
    bills_sql = """SELECT bill_id, patient_name, doctor_name, total, status
FROM bill_summary
ORDER BY created_at DESC, bill_id DESC
LIMIT 4"""
    return {'subtitle': 'Here is your hospital today',
            'tiles': tiles, 'tiles_title': 'Your hospital', 'cards': cards,
            'money': query(money_sql, one=True), 'money_sql': money_sql,
            'dept_stats': query(dept_sql), 'dept_sql': dept_sql,
            'side_title': 'Recent bills', 'bills': query(bills_sql), 'side_sql': bills_sql,
            'search_url': url_for('patients.patient_list')}


def doctor_dashboard(doctor_id):
    cards = [
        # uses the doctor_patients VIEW
        card('My patients',
             "SELECT COUNT(DISTINCT patient_id) AS value\n"
             "FROM doctor_patients WHERE doctor_id = %s", (doctor_id,),
             color='ice', url=url_for('patients.my_patients')),
        card('Upcoming',
             "SELECT COUNT(*) AS value FROM appointments\n"
             "WHERE doctor_id = %s AND appointment_date > CURDATE()\n"
             "  AND status = 'Scheduled'", (doctor_id,),
             color='gold', url=url_for('appointments.appointment_list', status='Scheduled')),
        card('Seen this month',
             "SELECT COUNT(*) AS value FROM visits v\n"
             "JOIN appointments a ON a.appointment_id = v.appointment_id\n"
             "WHERE a.doctor_id = %s\n"
             "  AND YEAR(v.visit_date) = YEAR(CURDATE())\n"
             "  AND MONTH(v.visit_date) = MONTH(CURDATE())", (doctor_id,),
             color='plum'),
    ]
    today_sql = """SELECT a.appointment_id, a.appointment_time, a.reason, a.status,
       p.patient_id, p.name AS patient_name, p.gender, p.dob
FROM appointments a
JOIN patients p ON p.patient_id = a.patient_id
WHERE a.doctor_id = %s AND a.appointment_date = CURDATE()
  AND a.status <> 'Cancelled'
ORDER BY a.appointment_time"""
    today = query(today_sql, (doctor_id,))
    next_sql = """SELECT a.appointment_id, a.appointment_date, a.appointment_time, a.reason,
       p.patient_id, p.name AS patient_name, p.allergies
FROM appointments a
JOIN patients p ON p.patient_id = a.patient_id
WHERE a.doctor_id = %s AND a.status = 'Scheduled' AND a.appointment_date >= CURDATE()
ORDER BY a.appointment_date, a.appointment_time
LIMIT 1"""
    tiles = [
        {'title': 'My Patients', 'color': 'ice', 'url': url_for('patients.my_patients'),
         'people': names("SELECT name FROM doctor_patients WHERE doctor_id = %s ORDER BY patient_id DESC LIMIT 4", (doctor_id,)),
         'count': query("SELECT COUNT(DISTINCT patient_id) AS n FROM doctor_patients WHERE doctor_id = %s", (doctor_id,), one=True)['n'],
         'chip': 'view'},
        {'title': "Today's list", 'color': 'plum',
         'url': url_for('appointments.appointment_list', date=date.today().isoformat()),
         'people': [a['patient_name'] for a in today][:4], 'count': len(today),
         'chip': f"{sum(a['status'] == 'Completed' for a in today)}/{len(today)} done"},
    ]
    return {'subtitle': 'Your schedule and patients',
            'tiles': tiles, 'tiles_title': 'Your day', 'cards': cards,
            'next_appt': query(next_sql, (doctor_id,), one=True), 'next_sql': next_sql,
            'today_total': len(today), 'today_done': sum(a['status'] == 'Completed' for a in today),
            'side_title': "Today's appointments", 'today': today, 'side_sql': today_sql,
            'search_url': url_for('patients.my_patients')}


def receptionist_dashboard():
    cards = [
        card("Today's appointments",
             "SELECT COUNT(*) AS value FROM appointments\n"
             "WHERE appointment_date = CURDATE() AND status <> 'Cancelled'",
             color='ice', url=url_for('appointments.appointment_list', date=date.today().isoformat())),
        card('Pending bills', "SELECT COUNT(*) AS value FROM bills WHERE status = 'Pending'",
             color='gold', url=url_for('billing.bill_list', status='Pending')),
        card('Amount due',
             "SELECT COALESCE(SUM(balance), 0) AS value\n"
             "FROM bill_summary WHERE status = 'Pending'",
             color='plum', money=True, url=url_for('billing.bill_list', status='Pending')),
    ]
    tiles = [
        {'title': 'Register patient', 'color': 'ice', 'url': url_for('patients.patient_add'),
         'people': names("SELECT name FROM patients ORDER BY patient_id DESC LIMIT 4"),
         'count': query("SELECT COUNT(*) AS n FROM patients", one=True)['n'],
         'chip': 'new'},
        {'title': 'Book appointment', 'color': 'plum', 'url': url_for('appointments.book'),
         'people': names("SELECT name FROM doctors ORDER BY doctor_id LIMIT 4"),
         'count': query("SELECT COUNT(*) AS n FROM doctors", one=True)['n'],
         'chip': 'book'},
    ]
    today_sql = """SELECT a.appointment_id, a.appointment_time, a.status, a.reason,
       p.patient_id, p.name AS patient_name,
       d.name AS doctor_name, dep.name AS department_name
FROM appointments a
JOIN patients p      ON p.patient_id = a.patient_id
JOIN doctors d       ON d.doctor_id = a.doctor_id
JOIN departments dep ON dep.department_id = d.department_id
WHERE a.appointment_date = CURDATE()
ORDER BY a.appointment_time"""
    pending_sql = """SELECT bill_id, patient_name, doctor_name, total, balance, visit_date
FROM bill_summary
WHERE status = 'Pending'
ORDER BY visit_date
LIMIT 3"""
    money_sql = """SELECT COALESCE(SUM(total), 0) AS billed,
       COALESCE(SUM(amount_paid), 0) AS collected
FROM bill_summary"""
    return {'subtitle': 'Front desk overview',
            'tiles': tiles, 'tiles_title': 'Quick actions', 'cards': cards,
            'money': query(money_sql, one=True), 'money_sql': money_sql,
            'pending_bills': query(pending_sql), 'pending_sql': pending_sql,
            'side_title': "Today's appointments", 'today': query(today_sql), 'side_sql': today_sql,
            'search_url': url_for('patients.patient_list')}


app = create_app()

if __name__ == '__main__':
    # PORT can be changed, e.g. on macOS port 5000 is used by AirPlay
    app.run(debug=True, port=int(os.environ.get('PORT', 5000)))
