-- =====================================================================
-- Hospital Management System - triggers_views.sql
-- Triggers, views and the stored procedure.  Run AFTER schema.sql.
-- =====================================================================
USE hospital_db;

DROP TRIGGER   IF EXISTS trg_item_price_before_insert;
DROP TRIGGER   IF EXISTS trg_update_bill_after_item;
DROP VIEW      IF EXISTS doctor_patients;
DROP VIEW      IF EXISTS bill_summary;
DROP PROCEDURE IF EXISTS book_appointment;

DELIMITER $$

-- ---------------------------------------------------------------------
-- TRIGGER 1 (BEFORE INSERT): copy the medicine's current price into the
-- prescription item, so later price changes don't change old bills.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_item_price_before_insert
BEFORE INSERT ON prescription_items
FOR EACH ROW
BEGIN
    IF NEW.unit_price IS NULL OR NEW.unit_price = 0 THEN
        SET NEW.unit_price = (SELECT unit_price FROM medicines
                              WHERE medicine_id = NEW.medicine_id);
    END IF;
END$$

-- ---------------------------------------------------------------------
-- TRIGGER 2 (AFTER INSERT): when a medicine is added to a prescription,
-- recalculate medicine_cost and total on that visit's bill.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_update_bill_after_item
AFTER INSERT ON prescription_items
FOR EACH ROW
BEGIN
    DECLARE v_visit_id INT;
    DECLARE v_med_cost DECIMAL(10,2);

    -- which visit does this prescription belong to?
    SELECT visit_id INTO v_visit_id
    FROM prescriptions WHERE prescription_id = NEW.prescription_id;

    -- sum of (quantity x price) for all items of this prescription
    SELECT COALESCE(SUM(quantity * unit_price), 0) INTO v_med_cost
    FROM prescription_items WHERE prescription_id = NEW.prescription_id;

    UPDATE bills
    SET medicine_cost = v_med_cost,
        total         = consultation_fee + v_med_cost
    WHERE visit_id = v_visit_id;
END$$

-- ---------------------------------------------------------------------
-- STORED PROCEDURE with TRANSACTION: book_appointment
-- Validates input, checks the slot is free, inserts the appointment.
-- Any error -> ROLLBACK and the error is passed back to Flask.
-- ---------------------------------------------------------------------
CREATE PROCEDURE book_appointment(
    IN  p_patient_id     INT,
    IN  p_doctor_id      INT,
    IN  p_date           DATE,
    IN  p_time           TIME,
    IN  p_reason         VARCHAR(255),
    OUT p_appointment_id INT
)
BEGIN
    DECLARE v_count INT DEFAULT 0;

    -- if anything fails, undo the transaction and re-raise the error
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    IF TIMESTAMP(p_date, p_time) < NOW() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot book an appointment in the past.';
    END IF;

    SELECT COUNT(*) INTO v_count FROM patients WHERE patient_id = p_patient_id;
    IF v_count = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Patient does not exist.';
    END IF;

    SELECT COUNT(*) INTO v_count FROM doctors WHERE doctor_id = p_doctor_id;
    IF v_count = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Doctor does not exist.';
    END IF;

    -- lock the slot rows so two receptionists cannot book it at the same moment
    SELECT COUNT(*) INTO v_count FROM appointments
    WHERE doctor_id = p_doctor_id
      AND appointment_date = p_date
      AND appointment_time = p_time
    FOR UPDATE;

    IF v_count > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'This doctor already has an appointment at that date and time.';
    END IF;

    INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason, status)
    VALUES (p_patient_id, p_doctor_id, p_date, p_time, p_reason, 'Scheduled');

    SET p_appointment_id = LAST_INSERT_ID();

    COMMIT;
END$$

DELIMITER ;

-- ---------------------------------------------------------------------
-- VIEW: doctor_patients  (feeds the "My Patients" page)
-- A patient belongs to a doctor if they had a (non-cancelled)
-- appointment with that doctor OR were registered by that doctor.
-- UNION removes duplicates.
-- ---------------------------------------------------------------------
CREATE VIEW doctor_patients AS
SELECT a.doctor_id, p.patient_id, p.name, p.phone, p.gender, p.dob, p.blood_group
FROM appointments a
JOIN patients p ON p.patient_id = a.patient_id
WHERE a.status <> 'Cancelled'
UNION
SELECT p.registered_by_doctor_id, p.patient_id, p.name, p.phone, p.gender, p.dob, p.blood_group
FROM patients p
WHERE p.registered_by_doctor_id IS NOT NULL;

-- ---------------------------------------------------------------------
-- VIEW: bill_summary  (feeds the Billing pages and dashboards)
-- One row per bill with patient, doctor, amount paid and balance.
-- ---------------------------------------------------------------------
CREATE VIEW bill_summary AS
SELECT b.bill_id, b.visit_id, b.consultation_fee, b.medicine_cost, b.total,
       b.status, b.created_at,
       v.visit_date, v.diagnosis, a.appointment_id,
       p.patient_id, p.name  AS patient_name, p.phone AS patient_phone,
       d.doctor_id,  d.name  AS doctor_name,
       dep.name AS department_name,
       COALESCE(pay.paid, 0)           AS amount_paid,
       b.total - COALESCE(pay.paid, 0) AS balance
FROM bills b
JOIN visits       v   ON v.visit_id        = b.visit_id
JOIN appointments a   ON a.appointment_id  = v.appointment_id
JOIN patients     p   ON p.patient_id      = a.patient_id
JOIN doctors      d   ON d.doctor_id       = a.doctor_id
JOIN departments  dep ON dep.department_id = d.department_id
LEFT JOIN (SELECT bill_id, SUM(amount) AS paid FROM payments GROUP BY bill_id) pay
       ON pay.bill_id = b.bill_id;
