"""
routes/admin.py - Departments, Doctors, Staff and Medicines (admin only).

Each section has: list, add, edit, delete.
* Delete is blocked by FOREIGN KEYS when a row is still referenced;
  we catch MySQL error 1451 and show a friendly message.
* Adding a doctor / staff member also creates the users row
  inside ONE transaction (both rows saved, or neither).
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from mysql.connector import IntegrityError
from werkzeug.security import generate_password_hash

from db import execute, query, transaction
from routes.auth import role_required
from validators import blank_to_none, int_error, money_error, phone_error, required

bp = Blueprint('admin', __name__, url_prefix='/admin')

FK_IN_USE = 1451      # MySQL: cannot delete a parent row (child rows exist)
DUPLICATE = 1062      # MySQL: duplicate value for a UNIQUE column


def friendly_duplicate(err):
    """Turn a MySQL duplicate-key message into plain English."""
    msg = str(err.msg)
    if 'username' in msg:
        return 'That username is already taken.'
    if 'email' in msg:
        return 'That email is already used by someone else.'
    if 'name' in msg:
        return 'An entry with that name already exists.'
    return 'That value already exists.'


def departments_list():
    return query("SELECT department_id, name FROM departments ORDER BY name")


# =====================================================================
# DEPARTMENTS
# =====================================================================
@bp.route('/departments')
@role_required('admin')
def departments():
    rows = query(
        """SELECT dep.*,
                  (SELECT COUNT(*) FROM doctors d WHERE d.department_id = dep.department_id) AS doctor_count,
                  (SELECT COUNT(*) FROM staff s   WHERE s.department_id = dep.department_id) AS staff_count
           FROM departments dep ORDER BY dep.name""")
    return render_template('admin/departments.html', departments=rows)


@bp.route('/departments/add', methods=['GET', 'POST'])
@bp.route('/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def department_form(dept_id=None):
    dept = query("SELECT * FROM departments WHERE department_id = %s", (dept_id,), one=True) if dept_id else {}
    if dept_id and not dept:
        flash('Department not found.', 'danger')
        return redirect(url_for('admin.departments'))

    if request.method == 'POST':
        f = request.form
        errors = required(f, {'name': 'Name'})
        if not errors:
            try:
                if dept_id:
                    execute("UPDATE departments SET name = %s, description = %s WHERE department_id = %s",
                            (f['name'].strip(), blank_to_none(f.get('description')), dept_id))
                    flash('Department updated.', 'success')
                else:
                    execute("INSERT INTO departments (name, description) VALUES (%s, %s)",
                            (f['name'].strip(), blank_to_none(f.get('description'))))
                    flash('Department added.', 'success')
                return redirect(url_for('admin.departments'))
            except IntegrityError as e:
                errors.append(friendly_duplicate(e) if e.errno == DUPLICATE else str(e.msg))
        for err in errors:
            flash(err, 'danger')
        dept = f

    return render_template('admin/department_form.html', dept=dept, editing=bool(dept_id))


@bp.route('/departments/<int:dept_id>/delete', methods=['POST'])
@role_required('admin')
def department_delete(dept_id):
    try:
        execute("DELETE FROM departments WHERE department_id = %s", (dept_id,))
        flash('Department deleted.', 'success')
    except IntegrityError as e:
        if e.errno == FK_IN_USE:
            flash('Cannot delete: this department still has doctors or staff. Move them first.', 'warning')
        else:
            raise
    return redirect(url_for('admin.departments'))


# =====================================================================
# DOCTORS
# =====================================================================
@bp.route('/doctors')
@role_required('admin')
def doctors():
    rows = query(
        """SELECT d.*, dep.name AS department_name, u.username
           FROM doctors d
           JOIN departments dep ON dep.department_id = d.department_id
           LEFT JOIN users u    ON u.doctor_id = d.doctor_id
           ORDER BY d.name""")
    return render_template('admin/doctors.html', doctors=rows)


def validate_person(f, need_login, login_label='Username'):
    errors = required(f, {'name': 'Name', 'phone': 'Phone', 'department_id': 'Department'})
    err = phone_error(f.get('phone'))
    if err:
        errors.append(err)
    if need_login:
        errors += required(f, {'username': login_label, 'password': 'Password'})
    if f.get('password') and len(f['password']) < 6:
        errors.append('Password must be at least 6 characters.')
    return errors


@bp.route('/doctors/add', methods=['GET', 'POST'])
@bp.route('/doctors/<int:doctor_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def doctor_form(doctor_id=None):
    doctor = {}
    if doctor_id:
        doctor = query("""SELECT d.*, u.username FROM doctors d
                          LEFT JOIN users u ON u.doctor_id = d.doctor_id
                          WHERE d.doctor_id = %s""", (doctor_id,), one=True)
        if not doctor:
            flash('Doctor not found.', 'danger')
            return redirect(url_for('admin.doctors'))

    if request.method == 'POST':
        f = request.form
        errors = validate_person(f, need_login=not doctor_id)
        errors += required(f, {'specialization': 'Specialization'})
        err = money_error(f.get('consultation_fee'), 'Consultation fee')
        if err:
            errors.append(err)

        if not errors:
            values = (f['name'].strip(), f['specialization'].strip(), f['phone'].strip(),
                      blank_to_none(f.get('email')), f['department_id'], f['consultation_fee'])
            try:
                with transaction() as cur:
                    if doctor_id:
                        cur.execute("""UPDATE doctors SET name=%s, specialization=%s, phone=%s, email=%s,
                                       department_id=%s, consultation_fee=%s WHERE doctor_id=%s""",
                                    values + (doctor_id,))
                        if f.get('password'):
                            cur.execute("UPDATE users SET password_hash = %s WHERE doctor_id = %s",
                                        (generate_password_hash(f['password']), doctor_id))
                    else:
                        # TRANSACTION: doctor row + login row together
                        cur.execute("""INSERT INTO doctors (name, specialization, phone, email,
                                       department_id, consultation_fee) VALUES (%s,%s,%s,%s,%s,%s)""",
                                    values)
                        new_id = cur.lastrowid
                        cur.execute("""INSERT INTO users (username, password_hash, role, doctor_id)
                                       VALUES (%s, %s, 'doctor', %s)""",
                                    (f['username'].strip(), generate_password_hash(f['password']), new_id))
                flash('Doctor saved.' if doctor_id else 'Doctor added with a login account.', 'success')
                return redirect(url_for('admin.doctors'))
            except IntegrityError as e:
                errors.append(friendly_duplicate(e) if e.errno == DUPLICATE else str(e.msg))

        for err in errors:
            flash(err, 'danger')
        doctor = dict(f, username=doctor.get('username') or f.get('username'))

    return render_template('admin/doctor_form.html', doctor=doctor, editing=bool(doctor_id),
                           departments=departments_list())


@bp.route('/doctors/<int:doctor_id>/delete', methods=['POST'])
@role_required('admin')
def doctor_delete(doctor_id):
    try:
        # TRANSACTION: remove the login, then the doctor. If the doctor has
        # appointments/patients the FK blocks it and the login is restored.
        with transaction() as cur:
            cur.execute("DELETE FROM users WHERE doctor_id = %s", (doctor_id,))
            cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        flash('Doctor deleted.', 'success')
    except IntegrityError as e:
        if e.errno == FK_IN_USE:
            flash('Cannot delete: this doctor has appointments or registered patients.', 'warning')
        else:
            raise
    return redirect(url_for('admin.doctors'))


# =====================================================================
# STAFF
# =====================================================================
@bp.route('/staff')
@role_required('admin')
def staff():
    rows = query(
        """SELECT s.*, dep.name AS department_name, u.username
           FROM staff s
           JOIN departments dep ON dep.department_id = s.department_id
           LEFT JOIN users u    ON u.staff_id = s.staff_id
           ORDER BY s.name""")
    return render_template('admin/staff.html', staff=rows)


@bp.route('/staff/add', methods=['GET', 'POST'])
@bp.route('/staff/<int:staff_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def staff_form(staff_id=None):
    member = {}
    if staff_id:
        member = query("""SELECT s.*, u.username FROM staff s
                          LEFT JOIN users u ON u.staff_id = s.staff_id
                          WHERE s.staff_id = %s""", (staff_id,), one=True)
        if not member:
            flash('Staff member not found.', 'danger')
            return redirect(url_for('admin.staff'))

    if request.method == 'POST':
        f = request.form
        errors = validate_person(f, need_login=False)
        errors += required(f, {'role_title': 'Role'})
        err = money_error(f.get('salary') or '0', 'Salary')
        if err:
            errors.append(err)
        # login is optional for staff (only receptionists need one)
        wants_login = bool(f.get('username', '').strip())
        if wants_login and not member.get('username') and not f.get('password'):
            errors.append('Enter a password for the new login.')

        if not errors:
            values = (f['name'].strip(), f['role_title'].strip(), f['phone'].strip(),
                      blank_to_none(f.get('email')), f['department_id'], f.get('salary') or 0)
            try:
                with transaction() as cur:
                    if staff_id:
                        cur.execute("""UPDATE staff SET name=%s, role_title=%s, phone=%s, email=%s,
                                       department_id=%s, salary=%s WHERE staff_id=%s""",
                                    values + (staff_id,))
                        sid = staff_id
                    else:
                        cur.execute("""INSERT INTO staff (name, role_title, phone, email, department_id, salary)
                                       VALUES (%s,%s,%s,%s,%s,%s)""", values)
                        sid = cur.lastrowid

                    if member.get('username'):
                        if f.get('password'):
                            cur.execute("UPDATE users SET password_hash = %s WHERE staff_id = %s",
                                        (generate_password_hash(f['password']), sid))
                    elif wants_login:
                        cur.execute("""INSERT INTO users (username, password_hash, role, staff_id)
                                       VALUES (%s, %s, 'receptionist', %s)""",
                                    (f['username'].strip(), generate_password_hash(f['password']), sid))
                flash('Staff member saved.', 'success')
                return redirect(url_for('admin.staff'))
            except IntegrityError as e:
                errors.append(friendly_duplicate(e) if e.errno == DUPLICATE else str(e.msg))

        for err in errors:
            flash(err, 'danger')
        member = dict(f, username=member.get('username') or f.get('username'),
                      has_login=bool(member.get('username')))
    else:
        member = dict(member or {}, has_login=bool(member.get('username')) if member else False)

    return render_template('admin/staff_form.html', member=member, editing=bool(staff_id),
                           departments=departments_list())


@bp.route('/staff/<int:staff_id>/delete', methods=['POST'])
@role_required('admin')
def staff_delete(staff_id):
    with transaction() as cur:
        cur.execute("DELETE FROM users WHERE staff_id = %s", (staff_id,))
        cur.execute("DELETE FROM staff WHERE staff_id = %s", (staff_id,))
    flash('Staff member deleted.', 'success')
    return redirect(url_for('admin.staff'))


# =====================================================================
# MEDICINES
# =====================================================================
@bp.route('/medicines')
@role_required('admin')
def medicines():
    q = request.args.get('q', '').strip()
    rows = query(
        """SELECT m.*, (SELECT COUNT(*) FROM prescription_items pi
                        WHERE pi.medicine_id = m.medicine_id) AS times_prescribed
           FROM medicines m
           WHERE m.name LIKE %s
           ORDER BY m.name""", (f'%{q}%',))
    return render_template('admin/medicines.html', medicines=rows, q=q)


@bp.route('/medicines/add', methods=['GET', 'POST'])
@bp.route('/medicines/<int:medicine_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def medicine_form(medicine_id=None):
    med = query("SELECT * FROM medicines WHERE medicine_id = %s", (medicine_id,), one=True) if medicine_id else {}
    if medicine_id and not med:
        flash('Medicine not found.', 'danger')
        return redirect(url_for('admin.medicines'))

    if request.method == 'POST':
        f = request.form
        errors = required(f, {'name': 'Name', 'unit_price': 'Unit price', 'stock': 'Stock'})
        for err in (money_error(f.get('unit_price'), 'Unit price'), int_error(f.get('stock'), 'Stock')):
            if err:
                errors.append(err)
        if not errors:
            values = (f['name'].strip(), blank_to_none(f.get('manufacturer')), f['unit_price'], f['stock'])
            try:
                if medicine_id:
                    execute("""UPDATE medicines SET name=%s, manufacturer=%s, unit_price=%s, stock=%s
                               WHERE medicine_id=%s""", values + (medicine_id,))
                else:
                    execute("""INSERT INTO medicines (name, manufacturer, unit_price, stock)
                               VALUES (%s,%s,%s,%s)""", values)
                flash('Medicine saved.', 'success')
                return redirect(url_for('admin.medicines'))
            except IntegrityError as e:
                errors.append(friendly_duplicate(e) if e.errno == DUPLICATE else str(e.msg))
        for err in errors:
            flash(err, 'danger')
        med = f

    return render_template('admin/medicine_form.html', med=med, editing=bool(medicine_id))


@bp.route('/medicines/<int:medicine_id>/delete', methods=['POST'])
@role_required('admin')
def medicine_delete(medicine_id):
    try:
        execute("DELETE FROM medicines WHERE medicine_id = %s", (medicine_id,))
        flash('Medicine deleted.', 'success')
    except IntegrityError as e:
        if e.errno == FK_IN_USE:
            flash('Cannot delete: this medicine appears in prescriptions.', 'warning')
        else:
            raise
    return redirect(url_for('admin.medicines'))
