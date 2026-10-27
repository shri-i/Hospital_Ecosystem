-- =====================================================================
-- Hospital Management System - seed.sql (demo data)
-- Run AFTER schema.sql and triggers_views.sql.
--
-- Demo logins (password in brackets):
--   admin                     (admin123)
--   dr.mehta, dr.kulkarni, dr.patil, dr.joshi, dr.deshmukh, dr.rao  (doctor123)
--   reception, reception2     (recep123)
-- Dates use CURDATE() so "today's appointments" always has data.
-- =====================================================================
USE hospital_db;

-- ---------- 4 departments ----------
INSERT INTO departments (name, description) VALUES
('Cardiology',       'Heart and blood vessel care'),
('Orthopedics',      'Bones, joints and muscles'),
('Pediatrics',       'Care for infants and children'),
('General Medicine', 'Primary care and common illnesses');

-- ---------- 6 doctors ----------
INSERT INTO doctors (name, specialization, phone, email, department_id, consultation_fee) VALUES
('Dr. Anil Mehta',      'Interventional Cardiologist', '9822011001', 'anil.mehta@hms.local',     1, 800.00),
('Dr. Priya Kulkarni',  'Cardiologist',                '9822011002', 'priya.kulkarni@hms.local', 1, 700.00),
('Dr. Rahul Patil',     'Orthopedic Surgeon',          '9822011003', 'rahul.patil@hms.local',    2, 600.00),
('Dr. Sneha Joshi',     'Pediatrician',                '9822011004', 'sneha.joshi@hms.local',    3, 500.00),
('Dr. Vikram Deshmukh', 'General Physician',           '9822011005', 'vikram.d@hms.local',       4, 400.00),
('Dr. Kavita Rao',      'Sports Medicine',             '9822011006', 'kavita.rao@hms.local',     2, 650.00);

-- ---------- 5 staff ----------
INSERT INTO staff (name, role_title, phone, email, department_id, salary) VALUES
('Pooja Shinde',  'Receptionist',    '9763012001', 'pooja.s@hms.local',  4, 22000),
('Amit Jadhav',   'Receptionist',    '9763012002', 'amit.j@hms.local',   1, 21000),
('Sunita Pawar',  'Nurse',           '9763012003', 'sunita.p@hms.local', 1, 28000),
('Ramesh More',   'Ward Assistant',  '9763012004', 'ramesh.m@hms.local', 2, 16000),
('Neha Kale',     'Lab Technician',  '9763012005', 'neha.k@hms.local',   3, 25000);

-- ---------- users (hashes generated with werkzeug, see generate_hashes.py) ----------
-- admin123
INSERT INTO users (username, password_hash, role) VALUES
('admin', 'scrypt:32768:8:1$gkRSqSCe2gy4opmN$e344e6bb24ed6db800c795dba4b68d816acf22b551c74655870ef82074b40f5a30c0473af0a3148606d075b5dba35523044fa82f7c53bd260c0223fc3e2479a8', 'admin');

-- doctor123
INSERT INTO users (username, password_hash, role, doctor_id) VALUES
('dr.mehta',    'scrypt:32768:8:1$QhRBxUSBH3D6iUpl$b9ffa770a9af7b8279bea35d3587f620dd5d53ab51b077e690c5c4a3aba865ed2b46bf5d572c35b079d0ffd07bc979ab0b1721507608f022c0e41f78fcab65cd', 'doctor', 1),
('dr.kulkarni', 'scrypt:32768:8:1$QhRBxUSBH3D6iUpl$b9ffa770a9af7b8279bea35d3587f620dd5d53ab51b077e690c5c4a3aba865ed2b46bf5d572c35b079d0ffd07bc979ab0b1721507608f022c0e41f78fcab65cd', 'doctor', 2),
('dr.patil',    'scrypt:32768:8:1$QhRBxUSBH3D6iUpl$b9ffa770a9af7b8279bea35d3587f620dd5d53ab51b077e690c5c4a3aba865ed2b46bf5d572c35b079d0ffd07bc979ab0b1721507608f022c0e41f78fcab65cd', 'doctor', 3),
('dr.joshi',    'scrypt:32768:8:1$QhRBxUSBH3D6iUpl$b9ffa770a9af7b8279bea35d3587f620dd5d53ab51b077e690c5c4a3aba865ed2b46bf5d572c35b079d0ffd07bc979ab0b1721507608f022c0e41f78fcab65cd', 'doctor', 4),
('dr.deshmukh', 'scrypt:32768:8:1$QhRBxUSBH3D6iUpl$b9ffa770a9af7b8279bea35d3587f620dd5d53ab51b077e690c5c4a3aba865ed2b46bf5d572c35b079d0ffd07bc979ab0b1721507608f022c0e41f78fcab65cd', 'doctor', 5),
('dr.rao',      'scrypt:32768:8:1$QhRBxUSBH3D6iUpl$b9ffa770a9af7b8279bea35d3587f620dd5d53ab51b077e690c5c4a3aba865ed2b46bf5d572c35b079d0ffd07bc979ab0b1721507608f022c0e41f78fcab65cd', 'doctor', 6);

-- recep123
INSERT INTO users (username, password_hash, role, staff_id) VALUES
('reception',  'scrypt:32768:8:1$rFkkbSJnbk8kEkLR$cf38c7e2c55a9d890836b65152110c3bd01ddfcf539f22e37591bd05b2b492fb4be0ba4593e2294ed0cfba51d177820ddebe4b8068d00c74bed4083994586098', 'receptionist', 1),
('reception2', 'scrypt:32768:8:1$rFkkbSJnbk8kEkLR$cf38c7e2c55a9d890836b65152110c3bd01ddfcf539f22e37591bd05b2b492fb4be0ba4593e2294ed0cfba51d177820ddebe4b8068d00c74bed4083994586098', 'receptionist', 2);

-- ---------- 15 patients ----------
INSERT INTO patients (name, phone, dob, gender, address, blood_group, emergency_contact,
                      allergies, existing_conditions, registered_by_doctor_id) VALUES
('Rohan Deshpande',   '9890100001', '1978-04-12', 'Male',   'Vishrambag, Sangli',       'B+',  '9890200001', 'Penicillin', 'Hypertension',         1),
('Anjali Gokhale',    '9890100002', '1985-09-23', 'Female', 'Miraj Road, Sangli',       'O+',  '9890200002', NULL,         'Mild asthma',          NULL),
('Suresh Naik',       '9890100003', '1965-01-30', 'Male',   'Market Yard, Sangli',      'A+',  '9890200003', NULL,         'Knee osteoarthritis',  3),
('Aarav Kulkarni',    '9890100004', '2018-06-15', 'Male',   'Rajwada Chowk, Sangli',    'B+',  '9890200004', 'Peanuts',    NULL,                   NULL),
('Meena Bhosale',     '9890100005', '1990-11-02', 'Female', 'Kupwad, Sangli',           'AB+', '9890200005', NULL,         'Diabetes Type 2',      NULL),
('Prakash Chavan',    '9890100006', '1959-07-19', 'Male',   'Madhavnagar, Sangli',      'O-',  '9890200006', 'Sulfa drugs','Coronary artery disease', NULL),
('Kavya Patwardhan',  '9890100007', '1995-03-08', 'Female', 'Ganesh Nagar, Sangli',     'A-',  '9890200007', NULL,         NULL,                   NULL),
('Nitin Salunkhe',    '9890100008', '1972-12-25', 'Male',   'Wanlesswadi, Sangli',      'B-',  '9890200008', NULL,         'High cholesterol',     NULL),
('Sakshi More',       '9890100009', '2001-05-17', 'Female', 'Vishrambag, Sangli',       'O+',  '9890200009', NULL,         NULL,                   NULL),
('Ganesh Jagtap',     '9890100010', '1982-08-04', 'Male',   'Shivaji Nagar, Sangli',    'A+',  '9890200010', 'Dust',       NULL,                   5),
('Isha Pawar',        '9890100011', '2016-02-29', 'Female', 'Kolhapur Road, Sangli',    'B+',  '9890200011', NULL,         NULL,                   NULL),
('Vaibhav Kadam',     '9890100012', '1993-10-10', 'Male',   'Sanjay Nagar, Sangli',     'AB-', '9890200012', NULL,         'Old ACL injury',       6),
('Lata Shirke',       '9890100013', '1968-06-21', 'Female', 'Gaon Bhag, Sangli',        'O+',  '9890200013', 'Aspirin',    'Arrhythmia',           NULL),
('Omkar Mane',        '9890100014', '1999-01-14', 'Male',   'Walchand College Rd, Sangli','A+','9890200014', NULL,         NULL,                   NULL),
('Snehal Kamble',     '9890100015', '1988-09-09', 'Female', 'Miraj, Sangli',            'B+',  '9890200015', NULL,         'Thyroid',              NULL);

-- ---------- 20 medicines ----------
INSERT INTO medicines (name, manufacturer, unit_price, stock) VALUES
('Paracetamol 500mg',     'Cipla',          2.00, 1000),
('Amoxicillin 500mg',     'Sun Pharma',     8.50,  500),
('Azithromycin 500mg',    'Alkem',         22.00,  300),
('Atorvastatin 10mg',     'Ranbaxy',        6.00,  400),
('Aspirin 75mg',          'Bayer',          1.50,  800),
('Metoprolol 50mg',       'AstraZeneca',    4.00,  400),
('Amlodipine 5mg',        'Pfizer',         3.50,  500),
('Metformin 500mg',       'USV',            2.50,  600),
('Ibuprofen 400mg',       'Abbott',         3.00,  700),
('Diclofenac Gel 30g',    'Novartis',      95.00,  120),
('Calcium + Vitamin D3',  'Shelcal',        7.00,  500),
('Pantoprazole 40mg',     'Alkem',          6.50,  600),
('Cetirizine 10mg',       'Dr. Reddy''s',   1.80,  700),
('Salbutamol Inhaler',    'Cipla',        150.00,   80),
('ORS Sachet',            'FDC',           20.00,  300),
('Zinc Syrup 100ml',      'Mankind',       65.00,  150),
('Levothyroxine 50mcg',   'Abbott',         2.20,  400),
('Clopidogrel 75mg',      'Sun Pharma',     9.00,  300),
('Vitamin B Complex',     'Becosules',      3.00,  800),
('Cough Syrup 100ml',     'Benadryl',      98.00,  150);

-- ---------- 14 appointments (past, today, future, one cancelled) ----------
INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason, status) VALUES
(1,  1, CURDATE() - INTERVAL 10 DAY, '10:00', 'Chest pain on exertion',   'Completed'),  -- 1
(2,  1, CURDATE() - INTERVAL 7 DAY,  '11:00', 'Palpitations',             'Completed'),  -- 2
(3,  3, CURDATE() - INTERVAL 5 DAY,  '09:30', 'Knee pain',                'Completed'),  -- 3
(4,  4, CURDATE() - INTERVAL 3 DAY,  '10:30', 'Fever and cough',          'Completed'),  -- 4
(5,  5, CURDATE() - INTERVAL 2 DAY,  '12:00', 'Sugar check-up',           'Completed'),  -- 5
(6,  2, CURDATE() - INTERVAL 1 DAY,  '15:00', 'Follow-up after stent',    'Completed'),  -- 6
(7,  1, CURDATE(),                   '10:00', 'BP review',                'Scheduled'),  -- 7
(8,  1, CURDATE(),                   '11:30', 'Cholesterol review',       'Scheduled'),  -- 8
(9,  3, CURDATE(),                   '12:00', 'Back pain',                'Scheduled'),  -- 9
(10, 5, CURDATE(),                   '16:00', 'Seasonal allergy',         'Scheduled'),  -- 10
(11, 4, CURDATE() + INTERVAL 1 DAY,  '10:00', 'Vaccination',              'Scheduled'),  -- 11
(12, 6, CURDATE() + INTERVAL 2 DAY,  '11:00', 'Knee strain while running','Scheduled'),  -- 12
(13, 2, CURDATE() - INTERVAL 4 DAY,  '14:00', 'Irregular heartbeat',      'Cancelled'),  -- 13
(1,  1, CURDATE() + INTERVAL 3 DAY,  '10:00', 'Follow-up',                'Scheduled');  -- 14

-- ---------- 6 visits (one per completed appointment) ----------
INSERT INTO visits (appointment_id, diagnosis, notes, visit_date) VALUES
(1, 'Stable angina',          'ECG shows mild ST changes. Advised TMT.',      CURDATE() - INTERVAL 10 DAY),
(2, 'Sinus tachycardia',      'Reduce caffeine. Review after 2 weeks.',       CURDATE() - INTERVAL 7 DAY),
(3, 'Osteoarthritis - knee',  'X-ray: grade 2 OA. Physiotherapy advised.',    CURDATE() - INTERVAL 5 DAY),
(4, 'Viral upper resp. infection', 'Plenty of fluids, rest for 3 days.',      CURDATE() - INTERVAL 3 DAY),
(5, 'Type 2 diabetes - controlled', 'HbA1c 6.8. Continue diet control.',      CURDATE() - INTERVAL 2 DAY),
(6, 'Post-PCI follow-up',     'Doing well. Continue antiplatelets.',          CURDATE() - INTERVAL 1 DAY);

-- ---------- bills: created with only the consultation fee ----------
-- (the trigger will add medicine_cost when items are inserted below)
INSERT INTO bills (visit_id, consultation_fee, medicine_cost, total, status) VALUES
(1, 800.00, 0, 800.00, 'Pending'),
(2, 800.00, 0, 800.00, 'Pending'),
(3, 600.00, 0, 600.00, 'Pending'),
(4, 500.00, 0, 500.00, 'Pending'),
(5, 400.00, 0, 400.00, 'Pending'),
(6, 700.00, 0, 700.00, 'Pending');

-- ---------- prescriptions ----------
INSERT INTO prescriptions (visit_id) VALUES (1),(2),(3),(4),(5),(6);

-- ---------- prescription items (unit_price filled by trigger, bill total updated by trigger) ----------
INSERT INTO prescription_items (prescription_id, medicine_id, dosage, duration, quantity) VALUES
(1, 5,  '0-0-1', '30 days', 30),
(1, 4,  '0-0-1', '30 days', 30),
(1, 6,  '1-0-1', '30 days', 60),
(2, 6,  '1-0-0', '14 days', 14),
(3, 9,  '1-0-1', '5 days',  10),
(3, 10, 'Apply twice daily', '10 days', 1),
(3, 11, '0-1-0', '30 days', 30),
(4, 1,  '1-1-1', '3 days',   9),
(4, 16, '5 ml twice', '5 days', 1),
(5, 8,  '1-0-1', '30 days', 60),
(6, 18, '0-0-1', '30 days', 30),
(6, 5,  '0-1-0', '30 days', 30),
(6, 12, '1-0-0', '30 days', 30);

-- ---------- payments: bills 1-3 fully paid, bill 4 partly paid, 5-6 pending ----------
INSERT INTO payments (bill_id, amount, method, payment_date)
SELECT bill_id, total, 'UPI', NOW() - INTERVAL (7 - bill_id) DAY FROM bills WHERE bill_id IN (1, 2, 3);
UPDATE bills SET status = 'Paid' WHERE bill_id IN (1, 2, 3);

INSERT INTO payments (bill_id, amount, method, payment_date) VALUES (4, 200.00, 'Cash', NOW() - INTERVAL 3 DAY);
