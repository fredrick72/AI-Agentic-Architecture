-- ============================================
-- AI-Agentic Architecture - Seed Data
-- ============================================
-- Sample data for healthcare claims demo
-- Demonstrates: ambiguous queries, multi-step reasoning, tool execution

\echo '==================================='
\echo 'Loading Seed Data...'
\echo '==================================='

-- ============================================
-- Sample Patients (10 total, including 3 "Johns")
-- ============================================

INSERT INTO patients (patient_id, full_name, first_name, last_name, dob, email, phone, last_visit_date, metadata) VALUES
-- The 3 Johns (for disambiguation demo)
('PAT-12345', 'John Smith', 'John', 'Smith', '1975-03-15', 'john.smith@email.com', '555-0101', '2024-01-15', '{"preferred_contact": "email", "insurance": "BlueCross"}'),
('PAT-67890', 'John Doe', 'John', 'Doe', '1982-07-22', 'john.doe@email.com', '555-0102', '2023-11-20', '{"preferred_contact": "phone", "insurance": "Aetna"}'),
('PAT-24680', 'John Williams', 'John', 'Williams', '1968-11-08', 'j.williams@email.com', '555-0103', '2024-02-05', '{"preferred_contact": "email", "insurance": "UnitedHealth"}'),

-- Other patients
('PAT-11111', 'Mary Johnson', 'Mary', 'Johnson', '1990-05-12', 'mary.j@email.com', '555-0104', '2024-01-20', '{"preferred_contact": "email", "insurance": "Cigna"}'),
('PAT-22222', 'Robert Brown', 'Robert', 'Brown', '1985-08-30', 'rbrown@email.com', '555-0105', '2023-12-10', '{"preferred_contact": "phone", "insurance": "BlueCross"}'),
('PAT-33333', 'Sarah Davis', 'Sarah', 'Davis', '1978-02-14', 'sarah.davis@email.com', '555-0106', '2024-02-28', '{"preferred_contact": "email", "insurance": "Aetna"}'),
('PAT-44444', 'Michael Wilson', 'Michael', 'Wilson', '1992-12-01', 'mwilson@email.com', '555-0107', '2023-10-15', '{"preferred_contact": "email", "insurance": "Kaiser"}'),
('PAT-55555', 'Jennifer Martinez', 'Jennifer', 'Martinez', '1988-04-25', 'jen.martinez@email.com', '555-0108', '2024-01-05', '{"preferred_contact": "phone", "insurance": "UnitedHealth"}'),
('PAT-66666', 'David Anderson', 'David', 'Anderson', '1970-09-18', 'danderson@email.com', '555-0109', '2023-09-22', '{"preferred_contact": "email", "insurance": "Humana"}'),
('PAT-77777', 'Lisa Taylor', 'Lisa', 'Taylor', '1995-06-07', 'lisa.t@email.com', '555-0110', '2024-02-12', '{"preferred_contact": "email", "insurance": "Cigna"}');

\echo '✓ Inserted 10 patients (including 3 named John)'

-- ============================================
-- Sample Claims (40 total)
-- ============================================

-- Claims for John Smith (PAT-12345) - 5 claims
INSERT INTO claims (claim_id, patient_id, claim_date, amount, status, claim_type, description, diagnosis_code, provider_name) VALUES
('CLM-12345-001', 'PAT-12345', '2024-01-10', 450.00, 'approved', 'medical', 'Annual physical examination', 'Z00.00', 'Dr. Sarah Chen, MD'),
('CLM-12345-002', 'PAT-12345', '2024-01-15', 1250.50, 'approved', 'medical', 'Blood work and lab tests', 'Z00.00', 'LabCorp Medical Labs'),
('CLM-12345-003', 'PAT-12345', '2023-12-20', 3200.00, 'approved', 'medical', 'MRI scan - knee injury', 'S83.5', 'City Imaging Center'),
('CLM-12345-004', 'PAT-12345', '2023-11-05', 150.00, 'approved', 'prescription', 'Prescription refill - lisinopril', 'I10', 'CVS Pharmacy'),
('CLM-12345-005', 'PAT-12345', '2024-02-01', 7400.00, 'pending', 'medical', 'Arthroscopic knee surgery', 'S83.5', 'Orthopedic Surgery Associates');

-- Claims for John Doe (PAT-67890) - 3 claims
INSERT INTO claims (claim_id, patient_id, claim_date, amount, status, claim_type, description, diagnosis_code, provider_name) VALUES
('CLM-67890-001', 'PAT-67890', '2023-11-15', 300.00, 'approved', 'dental', 'Dental cleaning and exam', 'D0120', 'Bright Smiles Dental'),
('CLM-67890-002', 'PAT-67890', '2023-10-20', 850.00, 'denied', 'dental', 'Cosmetic teeth whitening', 'D9972', 'Bright Smiles Dental'),
('CLM-67890-003', 'PAT-67890', '2023-09-10', 125.00, 'approved', 'vision', 'Eye examination', 'Z01.00', 'Vision Care Optometry');

-- Claims for John Williams (PAT-24680) - 6 claims
INSERT INTO claims (claim_id, patient_id, claim_date, amount, status, claim_type, description, diagnosis_code, provider_name) VALUES
('CLM-24680-001', 'PAT-24680', '2024-02-01', 500.00, 'approved', 'medical', 'Cardiology consultation', 'I25.10', 'Dr. Robert Kim, Cardiologist'),
('CLM-24680-002', 'PAT-24680', '2024-01-25', 2100.00, 'approved', 'medical', 'Stress test and EKG', 'I25.10', 'Heart Health Diagnostics'),
('CLM-24680-003', 'PAT-24680', '2024-01-10', 180.00, 'approved', 'prescription', 'Atorvastatin prescription', 'E78.5', 'Walgreens Pharmacy'),
('CLM-24680-004', 'PAT-24680', '2023-12-15', 220.00, 'approved', 'prescription', 'Metoprolol prescription', 'I25.10', 'Walgreens Pharmacy'),
('CLM-24680-005', 'PAT-24680', '2023-11-30', 450.00, 'approved', 'medical', 'Follow-up cardiology visit', 'I25.10', 'Dr. Robert Kim, Cardiologist'),
('CLM-24680-006', 'PAT-24680', '2024-02-10', 3800.00, 'in_review', 'medical', 'Cardiac catheterization', 'I25.10', 'St. Mary\'s Hospital');

-- Claims for Mary Johnson (PAT-11111) - 4 claims
INSERT INTO claims (claim_id, patient_id, claim_date, amount, status, claim_type, description, diagnosis_code, provider_name) VALUES
('CLM-11111-001', 'PAT-11111', '2024-01-18', 400.00, 'approved', 'medical', 'Annual wellness visit', 'Z00.00', 'Dr. Emily Rodriguez, MD'),
('CLM-11111-002', 'PAT-11111', '2024-01-18', 250.00, 'approved', 'medical', 'Immunizations', 'Z23', 'Dr. Emily Rodriguez, MD'),
('CLM-11111-003', 'PAT-11111', '2023-12-05', 600.00, 'approved', 'medical', 'Ultrasound imaging', 'Z36.0', 'Women\'s Health Imaging'),
('CLM-11111-004', 'PAT-11111', '2024-02-20', 180.00, 'pending', 'prescription', 'Prenatal vitamins', 'Z34.90', 'Target Pharmacy');

-- Claims for Robert Brown (PAT-22222) - 3 claims
INSERT INTO claims (claim_id, patient_id, claim_date, amount, status, claim_type, description, diagnosis_code, provider_name) VALUES
('CLM-22222-001', 'PAT-22222', '2023-12-08', 350.00, 'approved', 'medical', 'Physical therapy session', 'M54.5', 'HealthFirst PT'),
('CLM-22222-002', 'PAT-22222', '2023-11-22', 150.00, 'approved', 'prescription', 'Muscle relaxant prescription', 'M54.5', 'Rite Aid Pharmacy'),
('CLM-22222-003', 'PAT-22222', '2023-10-30', 500.00, 'approved', 'medical', 'Chiropractic treatment', 'M54.5', 'Spine & Wellness Center');

-- Claims for Sarah Davis (PAT-33333) - 5 claims
INSERT INTO claims (claim_id, patient_id, claim_date, amount, status, claim_type, description, diagnosis_code, provider_name) VALUES
('CLM-33333-001', 'PAT-33333', '2024-02-25', 420.00, 'approved', 'medical', 'Dermatology consultation', 'L70.0', 'Dr. Michael Chen, Dermatology'),
('CLM-33333-002', 'PAT-33333', '2024-02-25', 280.00, 'approved', 'medical', 'Skin biopsy procedure', 'L70.0', 'Dr. Michael Chen, Dermatology'),
('CLM-33333-003', 'PAT-33333', '2024-01-12', 95.00, 'approved', 'prescription', 'Topical antibiotic cream', 'L70.0', 'CVS Pharmacy'),
('CLM-33333-004', 'PAT-33333', '2023-11-18', 200.00, 'approved', 'vision', 'Contact lens fitting', 'Z01.00', 'Eye Experts Vision'),
('CLM-33333-005', 'PAT-33333', '2023-10-05', 550.00, 'approved', 'vision', 'New prescription glasses', 'H52.1', 'Eye Experts Vision');

-- Claims for Michael Wilson (PAT-44444) - 2 claims
INSERT INTO claims (claim_id, patient_id, claim_date, amount, status, claim_type, description, diagnosis_code, provider_name) VALUES
('CLM-44444-001', 'PAT-44444', '2023-10-10', 380.00, 'approved', 'medical', 'Urgent care visit - flu', 'J11.1', 'QuickCare Urgent Care'),
('CLM-44444-002', 'PAT-44444', '2023-10-12', 75.00, 'approved', 'prescription', 'Antiviral medication', 'J11.1', 'Walgreens Pharmacy');

-- Claims for Jennifer Martinez (PAT-55555) - 4 claims
INSERT INTO claims (claim_id, patient_id, claim_date, amount, status, claim_type, description, diagnosis_code, provider_name) VALUES
('CLM-55555-001', 'PAT-55555', '2024-01-03', 450.00, 'approved', 'medical', 'OB-GYN consultation', 'Z34.90', 'Dr. Lisa Wong, OB-GYN'),
('CLM-55555-002', 'PAT-55555', '2023-12-15', 800.00, 'approved', 'medical', 'Prenatal ultrasound', 'Z36.0', 'Women\'s Imaging Center'),
('CLM-55555-003', 'PAT-55555', '2023-11-20', 350.00, 'approved', 'medical', 'Blood work - prenatal panel', 'Z34.90', 'Quest Diagnostics'),
('CLM-55555-004', 'PAT-55555', '2024-02-14', 120.00, 'pending', 'prescription', 'Prenatal supplements', 'Z34.90', 'CVS Pharmacy');

-- Claims for David Anderson (PAT-66666) - 3 claims
INSERT INTO claims (claim_id, patient_id, claim_date, amount, status, claim_type, description, diagnosis_code, provider_name) VALUES
('CLM-66666-001', 'PAT-66666', '2023-09-18', 680.00, 'approved', 'dental', 'Crown replacement', 'D2740', 'Advanced Dental Care'),
('CLM-66666-002', 'PAT-66666', '2023-08-22', 250.00, 'approved', 'dental', 'Deep cleaning treatment', 'D4341', 'Advanced Dental Care'),
('CLM-66666-003', 'PAT-66666', '2023-07-10', 150.00, 'approved', 'dental', 'Dental x-rays', 'D0210', 'Advanced Dental Care');

-- Claims for Lisa Taylor (PAT-77777) - 5 claims
INSERT INTO claims (claim_id, patient_id, claim_date, amount, status, claim_type, description, diagnosis_code, provider_name) VALUES
('CLM-77777-001', 'PAT-77777', '2024-02-10', 320.00, 'approved', 'medical', 'Allergy testing', 'J30.9', 'Allergy & Asthma Specialists'),
('CLM-77777-002', 'PAT-77777', '2024-02-12', 180.00, 'approved', 'prescription', 'Allergy medication', 'J30.9', 'Target Pharmacy'),
('CLM-77777-003', 'PAT-77777', '2024-01-25', 400.00, 'approved', 'medical', 'Follow-up allergist visit', 'J30.9', 'Allergy & Asthma Specialists'),
('CLM-77777-004', 'PAT-77777', '2023-12-18', 95.00, 'approved', 'prescription', 'Nasal spray prescription', 'J30.9', 'Walgreens Pharmacy'),
('CLM-77777-005', 'PAT-77777', '2024-02-20', 250.00, 'pending', 'medical', 'Immunotherapy injection', 'J30.9', 'Allergy & Asthma Specialists');

\echo '✓ Inserted 40 claims across all patients'

-- ============================================
-- Summary Statistics
-- ============================================

\echo ''
\echo '==================================='
\echo 'Seed Data Summary'
\echo '==================================='
\echo ''

-- Patient count
SELECT COUNT(*) AS patient_count FROM patients;
\echo 'Total Patients: 10'

-- Claims count
SELECT COUNT(*) AS claim_count FROM claims;
\echo 'Total Claims: 40'

-- Claims by status
\echo ''
\echo 'Claims by Status:'
SELECT status, COUNT(*) AS count, SUM(amount) AS total_amount
FROM claims
GROUP BY status
ORDER BY status;

-- Total amount
\echo ''
\echo 'Total Claim Amount:'
SELECT SUM(amount) AS total FROM claims;

\echo ''
\echo '==================================='
\echo 'Demo Scenarios Ready'
\echo '==================================='
\echo ''
\echo 'Key Test Cases:'
\echo '  1. Ambiguous query: "Find claims for John"'
\echo '     → Should return 3 patients for disambiguation'
\echo ''
\echo '  2. Multi-step reasoning: "Total amount for John Smith"'
\echo '     → query_patients → get_claims → calculate_total'
\echo '     → Expected: $12,450.50'
\echo ''
\echo '  3. Simple query: "Claims for patient PAT-12345"'
\echo '     → Direct lookup, no ambiguity'
\echo '     → Expected: 5 claims'
\echo ''
\echo '==================================='
\echo 'Seed Data Loading Complete!'
\echo '==================================='
