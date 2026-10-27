-- =====================================================================
-- Hospital Management System - schema.sql
-- Creates the database and all 12 tables.
-- Run order: schema.sql  ->  triggers_views.sql  ->  seed.sql
-- =====================================================================

DROP DATABASE IF EXISTS hospital_db;
CREATE DATABASE hospital_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hospital_db;

-- ---------------------------------------------------------------------
-- 1. departments : hospital departments (Cardiology, Orthopedics, ...)
-- ---------------------------------------------------------------------
CREATE TABLE departments (
    department_id  INT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(100) NOT NULL UNIQUE,
    description    VARCHAR(255),
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- 2. doctors : each doctor belongs to exactly one department
-- ---------------------------------------------------------------------
CREATE TABLE doctors (
    doctor_id         INT AUTO_INCREMENT PRIMARY KEY,
    name              VARCHAR(100) NOT NULL,
    specialization    VARCHAR(100) NOT NULL,
    phone             VARCHAR(10)  NOT NULL,
    email             VARCHAR(100) UNIQUE,
    department_id     INT NOT NULL,
    consultation_fee  DECIMAL(10,2) NOT NULL DEFAULT 500.00,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_doctor_phone CHECK (phone REGEXP '^[0-9]{10}$'),
    CONSTRAINT chk_doctor_fee   CHECK (consultation_fee >= 0),
    CONSTRAINT fk_doctor_dept FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
);

-- ---------------------------------------------------------------------
-- 3. staff : non-doctor employees (receptionists, nurses, ...)
-- ---------------------------------------------------------------------
CREATE TABLE staff (
    staff_id       INT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    role_title     VARCHAR(50)  NOT NULL,          -- e.g. Receptionist, Nurse
    phone          VARCHAR(10)  NOT NULL,
    email          VARCHAR(100) UNIQUE,
    department_id  INT NOT NULL,
    salary         DECIMAL(10,2) NOT NULL DEFAULT 0,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_staff_phone  CHECK (phone REGEXP '^[0-9]{10}$'),
    CONSTRAINT chk_staff_salary CHECK (salary >= 0),
    CONSTRAINT fk_staff_dept FOREIGN KEY (department_id)
        REFERENCES departments(department_id)
);

-- ---------------------------------------------------------------------
-- 4. users : login accounts. A user is linked to a doctor OR a staff row
--    (admin is linked to neither).
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id        INT AUTO_INCREMENT PRIMARY KEY,
    username       VARCHAR(50)  NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    role           ENUM('admin','doctor','receptionist') NOT NULL,
    doctor_id      INT UNIQUE,      -- set only when role = doctor
    staff_id       INT UNIQUE,      -- set only when role = receptionist
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id),
    CONSTRAINT fk_user_staff  FOREIGN KEY (staff_id)  REFERENCES staff(staff_id),
    -- a doctor login must point to a doctor row, a receptionist to a staff row
    CONSTRAINT chk_user_link CHECK (
        (role = 'admin'        AND doctor_id IS NULL     AND staff_id IS NULL) OR
        (role = 'doctor'       AND doctor_id IS NOT NULL AND staff_id IS NULL) OR
        (role = 'receptionist' AND staff_id  IS NOT NULL AND doctor_id IS NULL)
    )
);

-- ---------------------------------------------------------------------
-- 5. patients : details from the registration form
-- ---------------------------------------------------------------------
CREATE TABLE patients (
    patient_id               INT AUTO_INCREMENT PRIMARY KEY,
    name                     VARCHAR(100) NOT NULL,
    phone                    VARCHAR(10)  NOT NULL,
    dob                      DATE NOT NULL,
    gender                   ENUM('Male','Female','Other') NOT NULL,
    address                  VARCHAR(255),
    blood_group              ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-'),
    emergency_contact        VARCHAR(10),
    allergies                VARCHAR(255),
    existing_conditions      VARCHAR(255),
    registered_by_doctor_id  INT NULL,        -- doctor who added this patient (optional)
    created_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_patient_phone CHECK (phone REGEXP '^[0-9]{10}$'),
    CONSTRAINT chk_patient_emergency CHECK (emergency_contact IS NULL OR emergency_contact REGEXP '^[0-9]{10}$'),
    CONSTRAINT fk_patient_doctor FOREIGN KEY (registered_by_doctor_id)
        REFERENCES doctors(doctor_id)
);

-- ---------------------------------------------------------------------
-- 6. appointments : the doctor <-> patient link (many-to-many)
--    UNIQUE(doctor, date, time) prevents double booking.
-- ---------------------------------------------------------------------
CREATE TABLE appointments (
    appointment_id    INT AUTO_INCREMENT PRIMARY KEY,
    patient_id        INT NOT NULL,
    doctor_id         INT NOT NULL,
    appointment_date  DATE NOT NULL,
    appointment_time  TIME NOT NULL,
    reason            VARCHAR(255),
    status            ENUM('Scheduled','Completed','Cancelled') NOT NULL DEFAULT 'Scheduled',
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_doctor_slot UNIQUE (doctor_id, appointment_date, appointment_time),
    CONSTRAINT fk_appt_patient FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    CONSTRAINT fk_appt_doctor  FOREIGN KEY (doctor_id)  REFERENCES doctors(doctor_id)
);

-- ---------------------------------------------------------------------
-- 7. visits : one consultation per appointment
-- ---------------------------------------------------------------------
CREATE TABLE visits (
    visit_id        INT AUTO_INCREMENT PRIMARY KEY,
    appointment_id  INT NOT NULL UNIQUE,        -- 1:1 with appointment
    diagnosis       VARCHAR(255) NOT NULL,
    notes           TEXT,
    visit_date      DATE NOT NULL,
    CONSTRAINT fk_visit_appt FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
);

-- ---------------------------------------------------------------------
-- 8. medicines : master list
-- ---------------------------------------------------------------------
CREATE TABLE medicines (
    medicine_id   INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL UNIQUE,
    manufacturer  VARCHAR(100),
    unit_price    DECIMAL(10,2) NOT NULL,
    stock         INT NOT NULL DEFAULT 0,
    CONSTRAINT chk_medicine_price CHECK (unit_price >= 0),
    CONSTRAINT chk_medicine_stock CHECK (stock >= 0)
);

-- ---------------------------------------------------------------------
-- 9. prescriptions : one prescription per visit
-- ---------------------------------------------------------------------
CREATE TABLE prescriptions (
    prescription_id  INT AUTO_INCREMENT PRIMARY KEY,
    visit_id         INT NOT NULL UNIQUE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_presc_visit FOREIGN KEY (visit_id) REFERENCES visits(visit_id)
);

-- ---------------------------------------------------------------------
-- 10. prescription_items : prescription <-> medicine (many-to-many)
--     unit_price is copied at prescribing time (filled by a trigger).
-- ---------------------------------------------------------------------
CREATE TABLE prescription_items (
    item_id          INT AUTO_INCREMENT PRIMARY KEY,
    prescription_id  INT NOT NULL,
    medicine_id      INT NOT NULL,
    dosage           VARCHAR(50)  NOT NULL,     -- e.g. 1-0-1
    duration         VARCHAR(50)  NOT NULL,     -- e.g. 5 days
    quantity         INT NOT NULL,
    unit_price       DECIMAL(10,2) NOT NULL DEFAULT 0,
    CONSTRAINT chk_item_qty CHECK (quantity > 0),
    CONSTRAINT uq_presc_medicine UNIQUE (prescription_id, medicine_id),
    CONSTRAINT fk_item_presc    FOREIGN KEY (prescription_id) REFERENCES prescriptions(prescription_id),
    CONSTRAINT fk_item_medicine FOREIGN KEY (medicine_id)     REFERENCES medicines(medicine_id)
);

-- ---------------------------------------------------------------------
-- 11. bills : one bill per visit
-- ---------------------------------------------------------------------
CREATE TABLE bills (
    bill_id           INT AUTO_INCREMENT PRIMARY KEY,
    visit_id          INT NOT NULL UNIQUE,
    consultation_fee  DECIMAL(10,2) NOT NULL DEFAULT 0,
    medicine_cost     DECIMAL(10,2) NOT NULL DEFAULT 0,
    total             DECIMAL(10,2) NOT NULL DEFAULT 0,
    status            ENUM('Pending','Paid') NOT NULL DEFAULT 'Pending',
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_bill_amounts CHECK (consultation_fee >= 0 AND medicine_cost >= 0 AND total >= 0),
    CONSTRAINT fk_bill_visit FOREIGN KEY (visit_id) REFERENCES visits(visit_id)
);

-- ---------------------------------------------------------------------
-- 12. payments : many payments can be recorded against one bill
-- ---------------------------------------------------------------------
CREATE TABLE payments (
    payment_id    INT AUTO_INCREMENT PRIMARY KEY,
    bill_id       INT NOT NULL,
    amount        DECIMAL(10,2) NOT NULL,
    method        ENUM('Cash','Card','UPI','Insurance') NOT NULL,
    payment_date  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_payment_amount CHECK (amount > 0),
    CONSTRAINT fk_payment_bill FOREIGN KEY (bill_id) REFERENCES bills(bill_id)
);
