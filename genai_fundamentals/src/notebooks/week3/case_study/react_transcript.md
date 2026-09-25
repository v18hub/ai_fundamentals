# Complete Flow as a ReAct Transcript

This is a worked, end-to-end trace of the claim-automation agent handling one
patient, in the classic **Thought / Action / Action Input / Observation**
ReAct format. Steps that are plain tool calls are still shown going through
the loop here so students can see the *whole* flow in one place; Notebook 1
and Notebook 2 make the tool-vs-agent distinction explicit in code.

Sample patient: `patient_id = "P1042"`, admitted 2 days, insurance ID
`INS-778`.

```
Thought: I need to start by pulling the patient's admission record to know
who this is, how long they were admitted, and which insurance policy applies.
Action: get_patient_record
Action Input: {"patient_id": "P1042"}
Observation: {"patient_id": "P1042", "name": "R. Sharma", "insurance_id":
"INS-778", "admission_date": "2026-08-20", "discharge_date": "2026-08-22",
"days_admitted": 2}

Thought: Now I need to know what the doctor actually diagnosed and treated.
That's only available as free-text notes, so I'll fetch them first.
Action: get_doctor_notes
Action Input: {"patient_id": "P1042"}
Observation: "Patient presented with high fever and abdominal pain. Blood
work confirmed typhoid fever. Started on IV ceftriaxone for 5 days, patient
responded well and was discharged in stable condition."

Thought: The notes are unstructured. I need to extract a clean diagnosis and
treatment before I can look up codes. This requires reading comprehension,
not a lookup, so this step needs the agent/LLM rather than a plain function.
Action: extract_diagnosis_and_treatment
Action Input: {"doctor_notes_text": "Patient presented with high fever and
abdominal pain. Blood work confirmed typhoid fever. Started on IV
ceftriaxone for 5 days, patient responded well and was discharged in stable
condition."}
Observation: {"diagnosis": "Typhoid fever", "treatment": "IV ceftriaxone
therapy (5 days)"}

Thought: Now that I have plain-language diagnosis and treatment, I can look
up their standard codes. This is a deterministic table lookup.
Action: lookup_icd_code
Action Input: {"disease_name": "Typhoid fever"}
Observation: "A01.0"

Thought: Good, got the ICD code. Now the procedure code for the treatment.
Action: lookup_procedure_code
Action Input: {"treatment_name": "IV ceftriaxone therapy (5 days)"}
Observation: "J0696"

Thought: Before trusting these codes, I should check that a doctor actually
signed off on this diagnosis/treatment, since an unsigned record can't be
claimed.
Action: get_doctor_signoff_status
Action Input: {"patient_id": "P1042"}
Observation: {"signed_off": true, "signed_by": "Dr. A. Iyer",
"timestamp": "2026-08-22T09:14:00"}

Thought: Sign-off exists. Next I should sanity-check whether the treatment
given is clinically consistent with the diagnosis. Typhoid fever treated
with IV ceftriaxone is standard care, but this is a judgment call, so it
goes through the reasoning agent rather than a fixed rule table.
Action: check_diagnosis_treatment_consistency
Action Input: {"diagnosis": "Typhoid fever", "treatment": "IV ceftriaxone
therapy (5 days)"}
Observation: {"consistent": true, "reasoning": "IV ceftriaxone is a standard
first-line antibiotic for confirmed typhoid fever; treatment duration and
route are appropriate.", "needs_human_review": false}

Thought: Diagnosis and treatment are consistent, and both codes are valid.
Now I need the insurance policy to know coverage limits and exclusions.
Action: get_insurance_policy
Action Input: {"insurance_id": "INS-778"}
Observation: {"policy_id": "INS-778", "coverage_limit": 50000,
"room_rent_limit_per_day": 3000, "covered_procedures": ["J0696", "J0690",
"99223"], "excluded_procedures": ["Z100"], "deductible": 1000}

Thought: I need to decide if this specific diagnosis/procedure combination
is eligible under this policy, including any caps. This requires
interpreting the policy's covered/excluded lists together with the room-rent
cap, which is a judgment call, not a plain lookup.
Action: check_eligibility
Action Input: {"policy": {...INS-778 policy...}, "diagnosis_code": "A01.0",
"procedure_code": "J0696", "days_admitted": 2}
Observation: {"eligible": true, "eligible_amount_cap": 49000,
"reasoning": "Procedure J0696 is in the covered_procedures list and is not
excluded. Eligible amount is coverage_limit minus deductible (50000 - 1000
= 49000), room-rent cap of 3000/day for 2 days (6000) is well under this
cap and not the binding constraint."}

Thought: Eligibility is confirmed with a cap of 49000. Now I need the actual
hospital bill to know the total amount being billed.
Action: get_hospital_bill_items
Action Input: {"patient_id": "P1042"}
Observation: [{"item": "Room charges (2 days)", "category": "room",
"amount": 6000}, {"item": "IV ceftriaxone (5-day course)",
"category": "medicine", "amount": 4500}, {"item": "Lab tests",
"category": "diagnostics", "amount": 2200}, {"item": "Doctor consultation
fees", "category": "professional", "amount": 1800}]

Thought: I can now total the bill with a plain calculation.
Action: calculate_total_bill
Action Input: {"bill_items": [...4 items above...]}
Observation: 14500

Thought: With the total bill, eligibility result, and policy caps known, I
can compute the covered amount deterministically — no more judgment needed
from here on.
Action: calculate_covered_amount
Action Input: {"policy": {...}, "total_bill": 14500, "days_admitted": 2,
"eligibility_result": {"eligible": true, "eligible_amount_cap": 49000}}
Observation: 14500

Thought: Total bill (14500) is well under both the room-rent cap check and
the eligible_amount_cap (49000), so the full billed amount is covered.
Patient payable amount should be the remainder, which I'll compute directly.
Action: calculate_patient_payable
Action Input: {"total_bill": 14500, "covered_amount": 14500}
Observation: 0

Thought: Insurance covers the full bill. Now I generate the two output
documents: the claim form for the insurer and the discharge bill for the
patient.
Action: generate_claim_form
Action Input: {"patient_record": {...}, "diagnosis_code": "A01.0",
"procedure_code": "J0696", "covered_amount": 14500,
"eligibility_reasoning": "Procedure covered, within policy cap."}
Observation: {"claim_id": "CLM-P1042-20260822", "status": "ready_to_submit",
...}

Action: generate_discharge_bill
Action Input: {"patient_record": {...}, "total_bill": 14500,
"covered_amount": 14500, "patient_payable": 0}
Observation: {"bill_id": "BILL-P1042-20260822", "amount_due": 0, ...}

Final Answer: Patient R. Sharma (P1042) — diagnosis Typhoid fever (A01.0),
treatment IV ceftriaxone therapy (J0696), doctor-verified and clinically
consistent. Insurance policy INS-778 covers this claim in full: total bill
₹14,500, insurance-covered ₹14,500, patient payable ₹0. Claim CLM-P1042-
20260822 is ready to submit; discharge bill BILL-P1042-20260822 generated
with zero balance due.
```

### A second, messier example (for classroom discussion)

Ask students to trace what changes if:
- The doctor's notes are ambiguous ("gave standard IV antibiotics" — no drug
  named) → `extract_diagnosis_and_treatment` should return low confidence and
  the agent's next Thought should call `flag_for_manual_review` instead of
  guessing a procedure code.
- `get_doctor_signoff_status` returns `signed_off: false` → the agent should
  stop and flag for review *before* spending effort on eligibility checks.
- The bill total (₹64,000) exceeds the `eligible_amount_cap` (₹49,000) →
  `calculate_covered_amount` deterministically caps covered amount at 49,000
  and `calculate_patient_payable` correctly returns 15,000 — no LLM judgment
  needed here, it's just arithmetic once the cap is known.

This is a good place to emphasize: **the agent's job is to get you to the
point where the remaining steps are deterministic — not to make every
decision itself.**
