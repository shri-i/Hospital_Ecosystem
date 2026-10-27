"""
routes/billing.py - bill list, printable invoice, record payment.
Receptionist and admin only. Uses the bill_summary VIEW.
"""
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from db import query, transaction
from routes.auth import role_required

bp = Blueprint('billing', __name__, url_prefix='/bills')

METHODS = ['Cash', 'Card', 'UPI', 'Insurance']


@bp.route('/')
@role_required('receptionist', 'admin')
def bill_list():
    status = request.args.get('status', '')
    q = request.args.get('q', '').strip()
    sql = "SELECT * FROM bill_summary WHERE (patient_name LIKE %s OR patient_phone LIKE %s)"
    params = [f'%{q}%', f'%{q}%']
    if status in ('Pending', 'Paid'):
        sql += " AND status = %s"
        params.append(status)
    sql += " ORDER BY created_at DESC, bill_id DESC"
    bills = query(sql, tuple(params))

    totals = query("""SELECT COALESCE(SUM(total), 0) AS billed,
                             COALESCE(SUM(amount_paid), 0) AS collected,
                             COALESCE(SUM(balance), 0) AS outstanding
                      FROM bill_summary""", one=True)
    return render_template('billing/list.html', bills=bills, status=status, q=q, totals=totals)


@bp.route('/<int:bill_id>')
@role_required('receptionist', 'admin')
def detail(bill_id):
    bill = query("SELECT * FROM bill_summary WHERE bill_id = %s", (bill_id,), one=True)
    if not bill:
        abort(404)
    items = query(
        """SELECT m.name, pi.dosage, pi.duration, pi.quantity, pi.unit_price,
                  pi.quantity * pi.unit_price AS line_total
           FROM prescription_items pi
           JOIN prescriptions pr ON pr.prescription_id = pi.prescription_id
           JOIN medicines m      ON m.medicine_id = pi.medicine_id
           WHERE pr.visit_id = %s
           ORDER BY pi.item_id""", (bill['visit_id'],))
    payments = query("SELECT * FROM payments WHERE bill_id = %s ORDER BY payment_date", (bill_id,))
    return render_template('billing/detail.html', bill=bill, items=items, payments=payments,
                           methods=METHODS)


@bp.route('/<int:bill_id>/pay', methods=['POST'])
@role_required('receptionist', 'admin')
def pay(bill_id):
    method = request.form.get('method', '')
    try:
        amount = Decimal(request.form.get('amount', '')).quantize(Decimal('0.01'))
    except InvalidOperation:
        flash('Enter a valid amount.', 'danger')
        return redirect(url_for('billing.detail', bill_id=bill_id))
    if method not in METHODS:
        flash('Choose a payment method.', 'danger')
        return redirect(url_for('billing.detail', bill_id=bill_id))

    # TRANSACTION: lock the bill, insert the payment, mark Paid if fully paid
    with transaction() as cur:
        cur.execute("SELECT total, status FROM bills WHERE bill_id = %s FOR UPDATE", (bill_id,))
        bill = cur.fetchone()
        if not bill:
            abort(404)
        cur.execute("SELECT COALESCE(SUM(amount), 0) AS paid FROM payments WHERE bill_id = %s", (bill_id,))
        paid = cur.fetchone()['paid']
        balance = bill['total'] - paid

        if amount <= 0 or amount > balance:
            flash(f'Amount must be between ₹0.01 and the balance ₹{balance:,.2f}.', 'danger')
            return redirect(url_for('billing.detail', bill_id=bill_id))

        cur.execute("INSERT INTO payments (bill_id, amount, method) VALUES (%s, %s, %s)",
                    (bill_id, amount, method))
        if paid + amount >= bill['total']:
            cur.execute("UPDATE bills SET status = 'Paid' WHERE bill_id = %s", (bill_id,))
            flash('Payment recorded. Bill is now fully PAID.', 'success')
        else:
            flash(f'Payment recorded. Remaining balance ₹{balance - amount:,.2f}.', 'info')

    return redirect(url_for('billing.detail', bill_id=bill_id))
