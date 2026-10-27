# MediCare – Hospital Management System (DBMS Project)

Flask + MySQL + Bootstrap 5. Raw SQL only (no ORM), so every query can be shown in the viva.

## Features
- 3 roles with different menus: **admin**, **doctor**, **receptionist**
- Departments, doctors, staff, medicines (admin)
- Patient registration, search, profile with full visit history
- Doctor's **My Patients** page (uses the `doctor_patients` view)
- Appointment booking through the `book_appointment` **stored procedure** (transaction + no double booking)
- Consultation: diagnosis, notes, multiple medicines, saved in **one transaction**
- Bill created automatically; medicine cost added by a **trigger**
- Printable invoice, partial / full payments
- Role-based dashboards using `COUNT`, `SUM`, `JOIN`, `GROUP BY` (click **SQL** on a card to see the query)

## Demo logins
| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Doctor | `dr.mehta` (also dr.kulkarni, dr.patil, dr.joshi, dr.deshmukh, dr.rao) | `doctor123` |
| Receptionist | `reception` / `reception2` | `recep123` |

---

## Setup on Windows

**1. Install** Python 3.10+ (tick "Add Python to PATH") and MySQL Server 8 + MySQL Workbench.

**2. Create the database** in MySQL Workbench. Open each file with *File → Open SQL Script* and run it with the ⚡ button, **in this order**:
1. `database/schema.sql` – database `hospital_db` + 12 tables
2. `database/triggers_views.sql` – 2 triggers, 2 views, 1 stored procedure
3. `database/seed.sql` – demo data

Refresh *SCHEMAS* – `hospital_db` appears.
(Running `schema.sql` again wipes and recreates the database – handy to reset before the demo.)

**3. Set your MySQL password** in `config.py`:
```python
'password': os.environ.get('DB_PASSWORD', 'YOUR_PASSWORD_HERE'),
```

**4. Install and run** (Command Prompt, inside the `hospital-management` folder):
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open **http://localhost:5000**

> macOS: use `source .venv/bin/activate`. Port 5000 is taken by AirPlay on Mac, so run `PORT=5001 python app.py` and open http://localhost:5001.

Need a new password hash? `python database/generate_hashes.py mypassword`

---

## Project structure
```
app.py                  Flask entry point + dashboards
config.py               DB credentials
db.py                   connection helper: query(), execute(), transaction()
validators.py           form validation helpers
database/
  schema.sql            12 tables with PK, FK, UNIQUE, CHECK, ENUM
  triggers_views.sql    triggers, views, stored procedure
  seed.sql              demo data
  generate_hashes.py    password hash generator
routes/
  auth.py               login/logout, login_required, role_required
  admin.py              departments, doctors, staff, medicines
  patients.py           list, add/edit, profile, My Patients
  appointments.py       list, book (CALL procedure), cancel
  visits.py             consultation + prescription (one transaction)
  billing.py            bill list, invoice, payments
templates/              one Jinja template per page
static/css, static/js   styling and small helpers
```

## Database objects to show in the viva
| Concept | Where |
|---|---|
| Primary / foreign keys, NOT NULL, UNIQUE, CHECK, ENUM | `schema.sql` |
| Double booking blocked | `UNIQUE (doctor_id, appointment_date, appointment_time)` on `appointments` |
| Trigger | `trg_update_bill_after_item` – recalculates bill when a medicine is prescribed; `trg_item_price_before_insert` copies price |
| Views | `doctor_patients` (My Patients), `bill_summary` (billing, dashboards) |
| Stored procedure + transaction | `book_appointment` – `START TRANSACTION`, checks, `SIGNAL`, `ROLLBACK` on error |
| Application transactions | add doctor + login; consultation save; record payment (`SELECT … FOR UPDATE`) |
| Many-to-many | doctor ↔ patient via `appointments`; prescription ↔ medicine via `prescription_items` |
| Role-based access | `role_required(...)` decorator in `routes/auth.py` |
| SQL injection safety | every query uses `%s` placeholders |

---

## 5-minute demo script

Keep **MySQL Workbench** open next to the browser. After each step run the query shown.

1. **Login as admin** (`admin` / `admin123`). Show the dashboard cards → click **SQL** to show the aggregate query. Open Departments, Doctors, Medicines.
   Try deleting *Cardiology* → friendly "cannot delete" message (foreign key protects data).
2. **Login as receptionist** (`reception` / `recep123`). *Patients → Add patient*, fill the form, save.
   `SELECT * FROM patients ORDER BY patient_id DESC LIMIT 1;`
3. **Book an appointment** for that patient with Dr. Anil Mehta (Cardiology), tomorrow 15:00.
   `SELECT * FROM appointments ORDER BY appointment_id DESC LIMIT 1;`
   Book the **same doctor, same date, same time** again → "already has an appointment" (procedure + UNIQUE).
4. **Login as doctor** (`dr.mehta` / `doctor123`). Dashboard shows today's appointments → **Start consultation**.
   Enter diagnosis, add 2 medicines, **Complete consultation**.
   ```sql
   SELECT * FROM visits ORDER BY visit_id DESC LIMIT 1;
   SELECT * FROM prescription_items ORDER BY item_id DESC LIMIT 2;
   SELECT * FROM bills ORDER BY bill_id DESC LIMIT 1;   -- medicine_cost filled by the trigger
   ```
   Show **My Patients** – it comes from the `doctor_patients` view.
5. **Login as receptionist** → *Billing* → open the new bill (printable invoice) → record a payment.
   `SELECT * FROM payments ORDER BY payment_id DESC LIMIT 1;` and the bill status becomes **Paid**.

---

## Likely viva questions

1. **Why MySQL and not MongoDB?** Hospital data is highly relational (patients, doctors, appointments, bills). MySQL gives foreign keys, joins, transactions, triggers and views, which a DBMS course expects.
2. **What normal form is the schema in?** 3NF. Every non-key column depends only on the primary key; e.g. department name lives only in `departments`, doctors store `department_id`.
3. **How do you prevent double booking?** Two layers: the procedure checks the slot inside a transaction with `SELECT … FOR UPDATE`, and `UNIQUE(doctor_id, appointment_date, appointment_time)` rejects duplicates at table level.
4. **What does your trigger do?** After a prescription item is inserted, it sums `quantity × unit_price` for that prescription and updates `medicine_cost` and `total` on the bill.
5. **What is a transaction? Where do you use one?** A group of statements that succeed or fail together (ACID). Used when saving a consultation (visit, bill, prescription, items, stock, status) – if stock is insufficient everything rolls back.
6. **What is a view and why use one?** A stored SELECT that acts like a table. `doctor_patients` hides the UNION of appointment-linked and doctor-registered patients; `bill_summary` joins 6 tables and computes paid/balance.
7. **Stored procedure vs. query from Python?** The procedure keeps the booking rules inside the database, runs as one unit, and returns clear errors via `SIGNAL`.
8. **Which relationships are many-to-many?** Doctor–patient (resolved by `appointments`) and prescription–medicine (resolved by `prescription_items`).
9. **How are passwords stored?** As salted hashes (werkzeug `generate_password_hash`), never plain text.
10. **How do you stop SQL injection?** All queries use parameter placeholders (`%s`); user input is never concatenated into SQL.
