"""
routes/patients.py - patient list/search, add/edit form, profile with
visit history, and the doctor's "My Patients" page.

Access:
  * list / profile      : admin, doctor, receptionist
  * add / edit          : receptionist (all patients), doctor (own patients)
  * My Patients         : doctor only (uses the doctor_patients VIEW)
"""
from collections import defaultdict

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from db import execute, query
from routes.auth import role_required
from validators import blank_to_none, dob_error, phone_error, required

bp = Blueprint('patients', __name__)

GENDERS = ['Male', 'Female', 'Other']
BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']


def is_my_patient(patient_id):
    """True if the logged-in doctor is linked to this patient (via the view)."""
    row = query("SELECT 1 AS ok FROM doctor_patients WHERE doctor_id = %s AND patient_id = %s",
                (session.get('doctor_id'), patient_id), one=True)
    return row is not None


# ---------------------------------------------------------------------
# Patient list with search
# ---------------------------------------------------------------------
@bp.route('/patients')
@role_required('admin', 'doctor', 'receptionist')
def patient_list():
    q = request.args.get('q', '').strip()
    like = f'%{q}%'
    rows = query(
        """SELECT p.patient_id, p.name, p.phone, p.gender, p.dob, p.blood_group, p.created_at,
                  d.name AS registered_by,
                  (SELECT COUNT(*) FROM appointments a WHERE a.patient_id = p.patient_id) AS appointment_count
           FROM patients p
           LEFT JOIN doctors d ON d.doctor_id = p.registered_by_doctor_id
           WHERE p.name LIKE %s OR p.phone LIKE %s
           ORDER BY p.patient_id DESC""", (like, like))
    return render_template('patients/list.html', patients=rows, q=q)


# ---------------------------------------------------------------------
# Add / edit patient
# ---------------------------------------------------------------------
def validate_patient(f):
    errors = required(f, {'name': 'Name', 'phone': 'Phone', 'dob': 'Date of birth', 'gender': 'Gender'})
    for err in (phone_error(f.get('phone')),
                phone_error(f.get('emergency_contact'), 'Emergency contact', optional=True),
                dob_error(f.get('dob')) if f.get('dob') else None):
        if err:
            errors.append(err)
    if f.get('gender') and f['gender'] not in GENDERS:
        errors.append('Choose a valid gender.')
    if f.get('blood_group') and f['blood_group'] not in BLOOD_GROUPS:
        errors.append('Choose a valid blood group.')
    return errors


def patient_values(f):
    return (f['name'].strip(), f['phone'].strip(), f['dob'], f['gender'],
            blank_to_none(f.get('address')), blank_to_none(f.get('blood_group')),
            blank_to_none(f.get('emergency_contact')), blank_to_none(f.get('allergies')),
            blank_to_none(f.get('existing_conditions')))


@bp.route('/patients/add', methods=['GET', 'POST'])
@role_required('doctor', 'receptionist')
def patient_add():
    # "?from=my" means the doctor came from My Patients -> go back there afterwards
    came_from_my = request.args.get('from') == 'my'
    patient = {}
    if request.method == 'POST':
        f = request.form
        errors = validate_patient(f)
        if not errors:
            # a doctor who adds a patient is automatically linked to them
            doctor_id = session['doctor_id'] if session['role'] == 'doctor' else None
            new_id = execute(
                """INSERT INTO patients (name, phone, dob, gender, address, blood_group,
                                         emergency_contact, allergies, existing_conditions,
                                         registered_by_doctor_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                patient_values(f) + (doctor_id,))
            flash(f'Patient registered (ID {new_id}).', 'success')
            if came_from_my:
                return redirect(url_for('patients.my_patients'))
            return redirect(url_for('patients.profile', patient_id=new_id))
        for err in errors:
            flash(err, 'danger')
        patient = f

    return render_template('patients/form.html', patient=patient, editing=False,
                           genders=GENDERS, blood_groups=BLOOD_GROUPS, came_from_my=came_from_my)


@bp.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@role_required('doctor', 'receptionist')
def patient_edit(patient_id):
    patient = query("SELECT * FROM patients WHERE patient_id = %s", (patient_id,), one=True)
    if not patient:
        abort(404)
    if session['role'] == 'doctor' and not is_my_patient(patient_id):
        flash('Doctors can only edit their own patients.', 'danger')
        return redirect(url_for('patients.profile', patient_id=patient_id))

    if request.method == 'POST':
        f = request.form
        errors = validate_patient(f)
        if not errors:
            execute(
                """UPDATE patients SET name=%s, phone=%s, dob=%s, gender=%s, address=%s,
                          blood_group=%s, emergency_contact=%s, allergies=%s, existing_conditions=%s
                   WHERE patient_id=%s""",
                patient_values(f) + (patient_id,))
            flash('Patient details updated.', 'success')
            return redirect(url_for('patients.profile', patient_id=patient_id))
        for err in errors:
            flash(err, 'danger')
        patient = dict(f, patient_id=patient_id)

    return render_template('patients/form.html', patient=patient, editing=True,
                           genders=GENDERS, blood_groups=BLOOD_GROUPS, came_from_my=False)


# ---------------------------------------------------------------------
# Patient profile: details + appointments + full visit history
# ---------------------------------------------------------------------
@bp.route('/patients/<int:patient_id>')
@role_required('admin', 'doctor', 'receptionist')
def profile(patient_id):
    patient = query(
        """SELECT p.*, d.name AS registered_by
           FROM patients p LEFT JOIN doctors d ON d.doctor_id = p.registered_by_doctor_id
           WHERE p.patient_id = %s""", (patient_id,), one=True)
    if not patient:
        abort(404)

    appointments = query(
        """SELECT a.*, d.name AS doctor_name, dep.name AS department_name
           FROM appointments a
           JOIN doctors d       ON d.doctor_id = a.doctor_id
           JOIN departments dep ON dep.department_id = d.department_id
           WHERE a.patient_id = %s
           ORDER BY a.appointment_date DESC, a.appointment_time DESC""", (patient_id,))

    visits = query(
        """SELECT v.*, d.name AS doctor_name, dep.name AS department_name,
                  b.bill_id, b.total, b.status AS bill_status
           FROM visits v
           JOIN appointments a  ON a.appointment_id = v.appointment_id
           JOIN doctors d       ON d.doctor_id = a.doctor_id
           JOIN departments dep ON dep.department_id = d.department_id
           LEFT JOIN bills b    ON b.visit_id = v.visit_id
           WHERE a.patient_id = %s
           ORDER BY v.visit_date DESC, v.visit_id DESC""", (patient_id,))

    # all prescribed medicines for this patient, grouped by visit in Python
    items = query(
        """SELECT pr.visit_id, m.name AS medicine, pi.dosage, pi.duration, pi.quantity
           FROM prescription_items pi
           JOIN prescriptions pr ON pr.prescription_id = pi.prescription_id
           JOIN medicines m      ON m.medicine_id = pi.medicine_id
           JOIN visits v         ON v.visit_id = pr.visit_id
           JOIN appointments a   ON a.appointment_id = v.appointment_id
           WHERE a.patient_id = %s
           ORDER BY pi.item_id""", (patient_id,))
    meds_by_visit = defaultdict(list)
    for it in items:
        meds_by_visit[it['visit_id']].append(it)

    can_edit = session['role'] == 'receptionist' or (
        session['role'] == 'doctor' and is_my_patient(patient_id))

    return render_template('patients/profile.html', patient=patient, appointments=appointments,
                           visits=visits, meds_by_visit=meds_by_visit, can_edit=can_edit)


# ---------------------------------------------------------------------
# My Patients (doctor only) - uses the doctor_patients VIEW
# ---------------------------------------------------------------------
@bp.route('/my-patients')
@role_required('doctor')
def my_patients():
    q = request.args.get('q', '').strip()
    like = f'%{q}%'
    rows = query(
        """SELECT dp.patient_id, dp.name, dp.phone, dp.gender, dp.dob, dp.blood_group,
                  MAX(v.visit_date) AS last_visit,
                  MIN(CASE WHEN a.status = 'Scheduled' AND a.appointment_date >= CURDATE()
                           THEN a.appointment_date END) AS next_appointment
           FROM doctor_patients dp
           LEFT JOIN appointments a ON a.patient_id = dp.patient_id AND a.doctor_id = dp.doctor_id
           LEFT JOIN visits v       ON v.appointment_id = a.appointment_id
           WHERE dp.doctor_id = %s AND (dp.name LIKE %s OR dp.phone LIKE %s)
           GROUP BY dp.patient_id, dp.name, dp.phone, dp.gender, dp.dob, dp.blood_group
           ORDER BY dp.name""", (session['doctor_id'], like, like))
    return render_template('patients/my_patients.html', patients=rows, q=q)
