-- =====================================================================
-- demo_queries.sql - queries to run in MySQL Workbench during the demo
-- Run one query at a time: put the cursor on it and press Ctrl+Enter
-- (Cmd+Enter on Mac).
-- =====================================================================
USE hospital_db;

-- ---------- 0. Show that the database exists ----------
SHOW TABLES;                         -- 12 tables + 2 views
SHOW TRIGGERS;                       -- 2 triggers
SHOW PROCEDURE STATUS WHERE Db = 'hospital_db';

-- ---------- 1. After adding a PATIENT ----------
SELECT * FROM patients ORDER BY patient_id DESC LIMIT 5;

-- ---------- 2. After BOOKING an appointment ----------
SELECT a.appointment_id, p.name AS patient, d.name AS doctor,
       a.appointment_date, a.appointment_time, a.status
FROM appointments a
JOIN patients p ON p.patient_id = a.patient_id
JOIN doctors  d ON d.doctor_id  = a.doctor_id
ORDER BY a.appointment_id DESC LIMIT 5;

-- Double booking is blocked by this UNIQUE constraint:
SHOW CREATE TABLE appointments;

-- ---------- 3. After the doctor completes a CONSULTATION ----------
SELECT * FROM visits ORDER BY visit_id DESC LIMIT 3;

SELECT pi.prescription_id, m.name AS medicine, pi.dosage, pi.duration,
       pi.quantity, pi.unit_price, pi.quantity * pi.unit_price AS amount
FROM prescription_items pi
JOIN medicines m ON m.medicine_id = pi.medicine_id
ORDER BY pi.item_id DESC LIMIT 5;

-- Bill created automatically; medicine_cost and total filled by the TRIGGER
SELECT * FROM bills ORDER BY bill_id DESC LIMIT 3;

-- Appointment status changed to Completed
SELECT appointment_id, status FROM appointments ORDER BY appointment_id DESC LIMIT 5;

-- Medicine stock reduced
SELECT name, stock FROM medicines ORDER BY name;

-- ---------- 4. After RECORDING a PAYMENT ----------
SELECT * FROM payments ORDER BY payment_id DESC LIMIT 3;
SELECT bill_id, total, status FROM bills ORDER BY bill_id DESC LIMIT 3;   -- status = Paid

-- ---------- 5. VIEWS ----------
SELECT * FROM doctor_patients WHERE doctor_id = 1;     -- feeds "My Patients" for Dr. Mehta
SELECT * FROM bill_summary;                            -- billing page

-- ---------- 6. Login accounts (passwords are hashed, not plain text) ----------
SELECT user_id, username, role, doctor_id, staff_id, LEFT(password_hash, 30) AS hash_start
FROM users;

-- ---------- 7. Test the STORED PROCEDURE directly ----------
CALL book_appointment(2, 3, CURDATE() + INTERVAL 5 DAY, '11:00', 'Test from Workbench', @new_id);
SELECT @new_id AS new_appointment_id;
-- run the same CALL again -> error: "This doctor already has an appointment at that date and time."

-- ---------- 8. Test the TRIGGER directly ----------
SELECT bill_id, medicine_cost, total FROM bills WHERE bill_id = 5;   -- before
INSERT INTO prescription_items (prescription_id, medicine_id, dosage, duration, quantity)
VALUES (5, 1, '1-0-1', '5 days', 10);                                -- add 10 Paracetamol
SELECT bill_id, medicine_cost, total FROM bills WHERE bill_id = 5;   -- after: +Rs. 20

-- ---------- 9. JOIN + GROUP BY report ----------
SELECT dep.name AS department, COUNT(a.appointment_id) AS appointments
FROM departments dep
LEFT JOIN doctors d      ON d.department_id = dep.department_id
LEFT JOIN appointments a ON a.doctor_id = d.doctor_id
GROUP BY dep.department_id, dep.name;
