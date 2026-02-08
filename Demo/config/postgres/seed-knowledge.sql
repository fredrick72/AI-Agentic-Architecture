-- ============================================
-- AI-Agentic Architecture - Knowledge Base Seed Data
-- ============================================
-- Healthcare domain documents for RAG demonstration
-- Embeddings are generated on Tool Registry startup via LLM Gateway

\echo '==================================='
\echo 'Loading Knowledge Base Seed Data...'
\echo '==================================='

-- ============================================
-- Insurance Policies
-- ============================================

INSERT INTO knowledge_base (title, content, metadata) VALUES
(
    'Medical Coverage Policy - Overview',
    'Our standard medical insurance plan covers preventive care visits, diagnostic testing, surgical procedures, prescription medications, and emergency services. Annual deductible is $500 for individuals and $1,000 for families. After meeting the deductible, the plan covers 80% of in-network costs and 60% of out-of-network costs. Preventive care including annual physicals, immunizations, and routine screenings are covered at 100% with no deductible when using in-network providers. Maximum out-of-pocket limit is $5,000 per individual and $10,000 per family per year.',
    '{"category": "policy", "tags": ["medical", "coverage", "deductible", "out-of-pocket"], "source": "policy_handbook"}'
),
(
    'Dental Coverage Policy',
    'Dental coverage includes preventive, basic, and major services. Preventive care (cleanings, exams, x-rays) is covered at 100% with two visits per year. Basic services (fillings, simple extractions) are covered at 80% after deductible. Major services (crowns, bridges, root canals) are covered at 50% after deductible. Cosmetic procedures such as teeth whitening, veneers for cosmetic purposes, and elective orthodontics for adults are NOT covered. Annual dental maximum benefit is $2,000 per person. Dental deductible is $50 per person.',
    '{"category": "policy", "tags": ["dental", "coverage", "cosmetic", "preventive"], "source": "policy_handbook"}'
),
(
    'Vision Coverage Policy',
    'Vision coverage includes one comprehensive eye exam per year covered at 100% in-network. Contact lens fittings and evaluations are covered as part of the eye exam benefit. Prescription glasses or contact lenses are covered up to $200 per year for frames and standard lenses. Progressive and bifocal lenses have an additional $50 copay. LASIK and other elective vision correction surgeries are not covered. Vision deductible is $10 per visit for in-network providers.',
    '{"category": "policy", "tags": ["vision", "eye exam", "glasses", "contacts"], "source": "policy_handbook"}'
),
(
    'Prescription Drug Coverage',
    'Prescription medications are covered through a tiered formulary system. Tier 1 (generic drugs): $10 copay. Tier 2 (preferred brand name): $30 copay. Tier 3 (non-preferred brand): $60 copay. Tier 4 (specialty medications): 20% coinsurance up to $250 per prescription. Mail-order pharmacy provides a 90-day supply at 2.5x the copay amount. Prior authorization is required for specialty medications and certain brand-name drugs when generic alternatives exist. Common medications like lisinopril, atorvastatin, and metoprolol are Tier 1 generics.',
    '{"category": "policy", "tags": ["prescription", "formulary", "copay", "medication"], "source": "policy_handbook"}'
),
(
    'Prior Authorization Requirements',
    'Prior authorization is required for the following services: MRI and CT scans (except emergency), surgical procedures over $5,000, specialty medications (Tier 4), out-of-network referrals, inpatient hospital admissions (except emergency), physical therapy beyond 20 sessions per year, cardiac catheterization and interventional procedures, and durable medical equipment over $500. Authorization requests are reviewed within 72 hours for standard requests and 24 hours for urgent requests. Failure to obtain prior authorization may result in claim denial or reduced benefits (50% coverage instead of standard rate).',
    '{"category": "policy", "tags": ["prior authorization", "approval", "requirements"], "source": "policy_handbook"}'
);

\echo '  Inserted 5 policy documents'

-- ============================================
-- Medical Procedures
-- ============================================

INSERT INTO knowledge_base (title, content, metadata) VALUES
(
    'MRI Scan Procedure',
    'Magnetic Resonance Imaging (MRI) is a non-invasive diagnostic procedure that uses magnetic fields and radio waves to create detailed images of organs and tissues. Common uses include evaluating knee injuries (meniscus tears, ligament damage), brain and spinal cord conditions, joint problems, and abdominal organ assessment. An MRI scan typically takes 30-60 minutes. Patients must remove all metal objects. MRI is covered under the medical plan at 80% after deductible when prior authorization is obtained. Average cost ranges from $1,500 to $5,000 depending on body part and contrast usage. Diagnosis codes commonly associated: S83.5 (knee), M54.5 (back pain), S06 (brain).',
    '{"category": "procedure", "tags": ["MRI", "imaging", "diagnostic", "knee", "brain"], "source": "procedure_guide"}'
),
(
    'Arthroscopic Knee Surgery',
    'Arthroscopic knee surgery is a minimally invasive surgical procedure used to diagnose and treat knee joint problems. Common conditions treated include torn meniscus, ACL/MCL/PCL ligament tears (diagnosis code S83.5), loose cartilage, and knee joint inflammation. The procedure involves small incisions and use of a tiny camera (arthroscope). Recovery time is typically 4-6 weeks for minor procedures and 6-9 months for ligament reconstruction. Average cost ranges from $5,000 to $15,000. Prior authorization is required. Covered at 80% after deductible for in-network surgeons. Physical therapy following surgery is typically approved for 20-30 sessions.',
    '{"category": "procedure", "tags": ["surgery", "knee", "arthroscopy", "ligament", "S83.5"], "source": "procedure_guide"}'
),
(
    'Cardiac Catheterization Procedure',
    'Cardiac catheterization is a procedure used to diagnose and treat cardiovascular conditions. A thin tube (catheter) is inserted through a blood vessel and guided to the heart. It can measure blood pressure in the heart chambers, evaluate coronary artery blockages, and perform interventions like angioplasty and stenting. Associated diagnosis codes include I25.10 (atherosclerotic heart disease) and I25.11 (coronary artery disease). Average cost ranges from $3,000 to $10,000. Prior authorization is required. Hospital stay is typically 1-2 days. Covered at 80% after deductible when medically necessary. Often preceded by stress testing and EKG evaluation.',
    '{"category": "procedure", "tags": ["cardiology", "catheterization", "heart", "I25.10", "coronary"], "source": "procedure_guide"}'
),
(
    'Blood Work and Laboratory Tests',
    'Routine blood work and laboratory testing includes Complete Blood Count (CBC), Basic Metabolic Panel (BMP), Comprehensive Metabolic Panel (CMP), Lipid Panel, Hemoglobin A1C, Thyroid Function Tests, and Urinalysis. When ordered as part of a preventive care visit (diagnosis code Z00.00), lab work is covered at 100% with no deductible. When ordered for diagnostic purposes, lab work is covered at 80% after deductible. Average cost ranges from $100 to $1,500 depending on tests ordered. No prior authorization required for standard panels. Results typically available within 1-3 business days.',
    '{"category": "procedure", "tags": ["lab", "blood work", "diagnostic", "preventive", "Z00.00"], "source": "procedure_guide"}'
);

\echo '  Inserted 4 procedure documents'

-- ============================================
-- Diagnosis Codes (ICD-10)
-- ============================================

INSERT INTO knowledge_base (title, content, metadata) VALUES
(
    'ICD-10 Code S83.5 - Sprain of Cruciate Ligament of Knee',
    'Diagnosis code S83.5 refers to a sprain of the cruciate ligament of the knee. This includes injuries to the Anterior Cruciate Ligament (ACL) and Posterior Cruciate Ligament (PCL). Common causes include sports injuries, sudden stops or changes in direction, and trauma. Subcodes: S83.50 (unspecified cruciate ligament, unspecified knee), S83.51 (anterior cruciate ligament), S83.52 (posterior cruciate ligament). Treatment options range from physical therapy and bracing for partial tears to arthroscopic surgical reconstruction for complete tears. Claims with this code commonly include MRI imaging, orthopedic consultations, arthroscopic surgery, and post-surgical physical therapy.',
    '{"category": "diagnosis_code", "tags": ["S83.5", "knee", "ACL", "PCL", "cruciate", "ligament"], "source": "icd10_reference"}'
),
(
    'ICD-10 Code I25.10 - Atherosclerotic Heart Disease',
    'Diagnosis code I25.10 refers to atherosclerotic heart disease of native coronary artery without angina pectoris. This condition involves buildup of plaque in the coronary arteries, reducing blood flow to the heart muscle. Risk factors include high cholesterol, hypertension, smoking, diabetes, and family history. Related codes: I25.11 (with angina), E78.5 (hyperlipidemia), I10 (hypertension). Common treatments include medications (statins like atorvastatin, beta-blockers like metoprolol), lifestyle modifications, stress testing and EKG monitoring, and cardiac catheterization for severe cases. Regular cardiology follow-up visits are typically every 3-6 months.',
    '{"category": "diagnosis_code", "tags": ["I25.10", "heart disease", "coronary", "atherosclerotic", "cardiology"], "source": "icd10_reference"}'
),
(
    'ICD-10 Code Z00.00 - General Adult Medical Examination',
    'Diagnosis code Z00.00 is used for encounter for general adult medical examination without abnormal findings. This code is used for annual physicals, wellness visits, and routine health assessments. Services typically billed with this code include physical examination, vital signs, health risk assessment, preventive counseling, routine blood work (CBC, metabolic panel, lipid panel), and age-appropriate cancer screenings. When Z00.00 is the primary diagnosis, preventive services are covered at 100% with no deductible under most insurance plans. If abnormal findings are discovered, additional diagnostic codes may be added.',
    '{"category": "diagnosis_code", "tags": ["Z00.00", "physical exam", "preventive", "wellness", "annual"], "source": "icd10_reference"}'
),
(
    'ICD-10 Code M54.5 - Low Back Pain',
    'Diagnosis code M54.5 refers to low back pain (lumbago). This is one of the most common diagnoses in outpatient settings. Common causes include muscle strain, disc herniation, degenerative disc disease, and poor posture. Treatment approaches include physical therapy (typically 12-20 sessions covered per year), chiropractic care (covered up to 20 visits per year), muscle relaxant medications, pain management, and in severe cases, surgical intervention. Imaging (X-ray, MRI) may be ordered if symptoms persist beyond 6 weeks or if neurological symptoms are present. Chiropractic and physical therapy visits require referral from primary care provider.',
    '{"category": "diagnosis_code", "tags": ["M54.5", "back pain", "lumbago", "physical therapy", "chiropractic"], "source": "icd10_reference"}'
);

\echo '  Inserted 4 diagnosis code documents'

-- ============================================
-- Claims Processing Guidelines
-- ============================================

INSERT INTO knowledge_base (title, content, metadata) VALUES
(
    'Claims Processing Timeline',
    'Standard claims are processed within 30 calendar days of receipt. Electronic claims submitted by in-network providers are typically processed within 10-15 business days. Paper claims may take up to 45 days. Claim status can be checked through the member portal or by contacting member services. Claims are processed in the following stages: (1) Receipt and validation, (2) Eligibility verification, (3) Benefit determination, (4) Provider contract review, (5) Payment or denial notification. Expedited processing within 72 hours is available for urgent claims related to ongoing treatment.',
    '{"category": "claims_process", "tags": ["timeline", "processing", "status", "electronic"], "source": "claims_handbook"}'
),
(
    'Claims Appeal Process',
    'If a claim is denied, members have 180 days from the denial date to file an appeal. The appeal process has three levels: Level 1 - Internal review by a different claims examiner (decision within 30 days). Level 2 - Review by medical director and clinical staff (decision within 45 days). Level 3 - External independent review by a third-party organization (decision within 60 days). Common reasons for denial include: lack of prior authorization, cosmetic procedure exclusion, out-of-network without referral, exceeding benefit maximums, and non-covered services. Members should include supporting documentation, physician letters, and medical records with their appeal.',
    '{"category": "claims_process", "tags": ["appeal", "denial", "review", "process"], "source": "claims_handbook"}'
);

\echo '  Inserted 2 claims process documents'

-- ============================================
-- Summary
-- ============================================

\echo ''
\echo '==================================='
\echo 'Knowledge Base Seed Data Summary'
\echo '==================================='

SELECT metadata->>'category' as category, COUNT(*) as doc_count
FROM knowledge_base
GROUP BY metadata->>'category'
ORDER BY doc_count DESC;

\echo ''
\echo 'Total knowledge base documents:'
SELECT COUNT(*) as total FROM knowledge_base;

\echo ''
\echo 'NOTE: Embeddings will be generated on Tool Registry startup'
\echo '==================================='
\echo 'Knowledge Base Seed Data Complete!'
\echo '==================================='
