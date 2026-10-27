"""
routes/visits.py - the consultation page (doctor only).

Saving a consultation is ONE transaction:
  1. INSERT visit
  2. INSERT bill (consultation fee only)
  3. INSERT prescription
  4. INSERT prescription_items  -> trigger adds medicine cost to the bill
  5. UPDATE medicines stock
  6. UPDATE appointment status = 'Completed'
If any step fails (e.g. not enough stock) everything is rolled back.
"""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from db import query, transaction
from routes.auth import role_required

bp = Blueprint('visits', __name__)


class ConsultationError(Exception):
    """Raised inside the transaction to roll back with a friendly message."""


def load_appointment(appointment_id):
    return query(
        """SELECT a.*, p.name AS patient_name, p.dob, p.gender, p.blood_group,
                  p.allergies, p.existing_conditions, p.phone,
                  d.name AS doctor_name, d.consultation_fee
           FROM appointments a
           JOIN patients p ON p.patient_id = a.patient_id
           JOIN doctors d  ON d.doctor_id = a.doctor_id
           WHERE a.appointment_id = %s""", (appointment_id,), one=True)


def read_items(form):
    """Collect the dynamic medicine rows from the form into a list of dicts."""
    items = []
    rows = zip(form.getlist('medicine_id'), form.getlist('dosage'),
               form.getlist('duration'), form.getlist('quantity'))
    for med_id, dosage, duration, qty in rows:
        if not med_id:
            continue                      # empty row -> ignore
        if not dosage.strip() or not duration.strip():
            raise ConsultationError('Every medicine needs a dosage and a duration.')
        try:
            qty = int(qty)
        except ValueError:
            raise ConsultationError('Quantity must be a whole number.')
        if qty <= 0:
            raise ConsultationError('Quantity must be at least 1.')
        items.append({'medicine_id': int(med_id), 'dosage': dosage.strip(),
                      'duration': duration.strip(), 'quantity': qty})
    ids = [i['medicine_id'] for i in items]
    if len(ids) != len(set(ids)):
        raise ConsultationError('The same medicine was added twice. Combine them into one row.')
    return items


@bp.route('/consultation/<int:appointment_id>', methods=['GET', 'POST'])
@role_required('doctor')
def consultation(appointment_id):
    appt = load_appointment(appointment_id)
    if not appt or appt['doctor_id'] != session['doctor_id']:
        flash('Appointment not found in your schedule.', 'danger')
        return redirect(url_for('appointments.appointment_list'))
    if appt['status'] != 'Scheduled':
        flash(f"This appointment is already {appt['status']}.", 'warning')
        return redirect(url_for('patients.profile', patient_id=appt['patient_id']))

    if request.method == 'POST':
        f = request.form
        try:
            diagnosis = f.get('diagnosis', '').strip()
            if not diagnosis:
                raise ConsultationError('Diagnosis is required.')
            items = read_items(f)

            with transaction() as cur:
                # 1. visit
                cur.execute("""INSERT INTO visits (appointment_id, diagnosis, notes, visit_date)
                               VALUES (%s, %s, %s, CURDATE())""",
                            (appointment_id, diagnosis, f.get('notes', '').strip() or None))
                visit_id = cur.lastrowid

                # 2. bill with the doctor's consultation fee
                cur.execute("""INSERT INTO bills (visit_id, consultation_fee, medicine_cost, total, status)
                               VALUES (%s, %s, 0, %s, 'Pending')""",
                            (visit_id, appt['consultation_fee'], appt['consultation_fee']))

                # 3. prescription
                cur.execute("INSERT INTO prescriptions (visit_id) VALUES (%s)", (visit_id,))
                prescription_id = cur.lastrowid

                for it in items:
                    # lock the medicine row and check stock
                    cur.execute("SELECT name, stock FROM medicines WHERE medicine_id = %s FOR UPDATE",
                                (it['medicine_id'],))
                    med = cur.fetchone()
                    if med is None:
                        raise ConsultationError('A selected medicine no longer exists.')
                    if med['stock'] < it['quantity']:
                        raise ConsultationError(
                            f"Not enough stock for {med['name']} (only {med['stock']} left).")

                    # 4. item -> triggers fill unit_price and update the bill
                    cur.execute("""INSERT INTO prescription_items
                                   (prescription_id, medicine_id, dosage, duration, quantity)
                                   VALUES (%s, %s, %s, %s, %s)""",
                                (prescription_id, it['medicine_id'], it['dosage'],
                                 it['duration'], it['quantity']))
                    # 5. reduce stock
                    cur.execute("UPDATE medicines SET stock = stock - %s WHERE medicine_id = %s",
                                (it['quantity'], it['medicine_id']))

                # 6. appointment done
                cur.execute("UPDATE appointments SET status = 'Completed' WHERE appointment_id = %s",
                            (appointment_id,))

            flash('Consultation saved. The bill was generated automatically.', 'success')
            return redirect(url_for('patients.profile', patient_id=appt['patient_id']))
        except ConsultationError as e:
            flash(str(e) + ' Nothing was saved.', 'danger')

    medicines = query("SELECT medicine_id, name, unit_price, stock FROM medicines ORDER BY name")
    history = query(
        """SELECT v.visit_date, v.diagnosis, d.name AS doctor_name
           FROM visits v
           JOIN appointments a ON a.appointment_id = v.appointment_id
           JOIN doctors d      ON d.doctor_id = a.doctor_id
           WHERE a.patient_id = %s
           ORDER BY v.visit_date DESC LIMIT 5""", (appt['patient_id'],))
    return render_template('visits/consultation.html', appt=appt, medicines=medicines,
                           history=history, form=request.form)
