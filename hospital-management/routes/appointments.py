"""
routes/appointments.py - book (via the book_appointment stored procedure),
list with filters, cancel.

Access:
  * receptionist : all appointments, book for any doctor
  * doctor       : only their own appointments, books for themselves
"""
from datetime import date, timedelta

import mysql.connector
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from db import execute, get_db, query
from routes.auth import role_required
from validators import required

bp = Blueprint('appointments', __name__, url_prefix='/appointments')

STATUSES = ['Scheduled', 'Completed', 'Cancelled']


def time_slots():
    """09:00 to 17:30 every 30 minutes -> ['09:00', '09:30', ...]"""
    slots, t = [], timedelta(hours=9)
    while t <= timedelta(hours=17, minutes=30):
        h, m = divmod(int(t.total_seconds()) // 60, 60)
        slots.append(f'{h:02d}:{m:02d}')
        t += timedelta(minutes=30)
    return slots


# ---------------------------------------------------------------------
# List with filters (date, doctor, status)
# ---------------------------------------------------------------------
@bp.route('/')
@role_required('doctor', 'receptionist')
def appointment_list():
    f_date = request.args.get('date', '')
    f_status = request.args.get('status', '')
    f_doctor = request.args.get('doctor_id', '')

    # doctors can only ever see their own appointments
    if session['role'] == 'doctor':
        f_doctor = str(session['doctor_id'])

    # build the WHERE clause from the chosen filters (values stay parameterized)
    where, params = [], []
    if f_date:
        where.append('a.appointment_date = %s')
        params.append(f_date)
    if f_status:
        where.append('a.status = %s')
        params.append(f_status)
    if f_doctor:
        where.append('a.doctor_id = %s')
        params.append(f_doctor)
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

    rows = query(
        f"""SELECT a.*, p.name AS patient_name, p.phone AS patient_phone,
                   d.name AS doctor_name, dep.name AS department_name, v.visit_id
            FROM appointments a
            JOIN patients p      ON p.patient_id = a.patient_id
            JOIN doctors d       ON d.doctor_id = a.doctor_id
            JOIN departments dep ON dep.department_id = d.department_id
            LEFT JOIN visits v   ON v.appointment_id = a.appointment_id
            {where_sql}
            ORDER BY a.appointment_date DESC, a.appointment_time""", tuple(params))

    doctors = query("SELECT doctor_id, name FROM doctors ORDER BY name")
    return render_template('appointments/list.html', appointments=rows, doctors=doctors,
                           statuses=STATUSES, f_date=f_date, f_status=f_status, f_doctor=f_doctor,
                           today=date.today())


# ---------------------------------------------------------------------
# Book appointment -> CALL book_appointment(...)
# ---------------------------------------------------------------------
@bp.route('/book', methods=['GET', 'POST'])
@role_required('doctor', 'receptionist')
def book():
    form = dict(request.form) if request.method == 'POST' else {
        'patient_id': request.args.get('patient_id', ''),
        'appointment_date': date.today().isoformat(),
    }
    if session['role'] == 'doctor':
        form['doctor_id'] = str(session['doctor_id'])

    if request.method == 'POST':
        errors = required(form, {'patient_id': 'Patient', 'doctor_id': 'Doctor',
                                 'appointment_date': 'Date', 'appointment_time': 'Time'})
        if not errors:
            cur = get_db().cursor()
            try:
                # The procedure checks everything inside a transaction.
                # The last argument is the OUT parameter (new appointment id).
                result = cur.callproc('book_appointment', (
                    int(form['patient_id']), int(form['doctor_id']),
                    form['appointment_date'], form['appointment_time'],
                    form.get('reason', '').strip() or None, 0))
                flash(f'Appointment booked (ID {result[5]}).', 'success')
                return redirect(url_for('appointments.appointment_list',
                                        date=form['appointment_date']))
            except mysql.connector.Error as e:
                # 1644 = SIGNAL from the procedure, 1062 = UNIQUE(doctor, date, time)
                if e.errno in (1644, 1062):
                    errors.append(e.msg if e.errno == 1644 else
                                  'This doctor already has an appointment at that date and time.')
                else:
                    raise
            finally:
                cur.close()
        for err in errors:
            flash(err, 'danger')

    patients = query("SELECT patient_id, name, phone FROM patients ORDER BY name")
    departments = query("SELECT department_id, name FROM departments ORDER BY name")
    doctors = query("""SELECT d.doctor_id, d.name, d.specialization, d.department_id, d.consultation_fee
                       FROM doctors d ORDER BY d.name""")
    # pre-select the department of the chosen doctor (for the doctor role / re-shown form)
    if form.get('doctor_id') and not form.get('department_id'):
        for d in doctors:
            if str(d['doctor_id']) == str(form['doctor_id']):
                form['department_id'] = str(d['department_id'])

    return render_template('appointments/book.html', form=form, patients=patients,
                           departments=departments, doctors=doctors, slots=time_slots(),
                           today=date.today().isoformat())


@bp.route('/booked-slots')
@role_required('doctor', 'receptionist')
def booked_slots():
    """Small JSON API used by the booking page to grey out taken slots."""
    # TIME '10:30:00' -> first 5 characters '10:30'
    rows = query("""SELECT LEFT(CAST(appointment_time AS CHAR), 5) AS t FROM appointments
                    WHERE doctor_id = %s AND appointment_date = %s""",
                 (request.args.get('doctor_id'), request.args.get('date')))
    return jsonify([r['t'] for r in rows])


# ---------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------
@bp.route('/<int:appointment_id>/cancel', methods=['POST'])
@role_required('doctor', 'receptionist')
def cancel(appointment_id):
    appt = query("SELECT * FROM appointments WHERE appointment_id = %s", (appointment_id,), one=True)
    if not appt:
        flash('Appointment not found.', 'danger')
    elif session['role'] == 'doctor' and appt['doctor_id'] != session['doctor_id']:
        flash('You can only cancel your own appointments.', 'danger')
    elif appt['status'] != 'Scheduled':
        flash(f"Only scheduled appointments can be cancelled (this one is {appt['status']}).", 'warning')
    else:
        execute("UPDATE appointments SET status = 'Cancelled' WHERE appointment_id = %s", (appointment_id,))
        flash('Appointment cancelled.', 'info')
    return redirect(request.referrer or url_for('appointments.appointment_list'))
