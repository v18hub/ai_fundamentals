# Teaching Case Study: Agentic Automation of Medical Insurance Claims at Discharge

## 1. The Problem

When a patient is discharged from a hospital, the hospital cannot simply hand over
a bill. Before that bill is finalized, several checks have to happen, and each
check pulls from a different source of truth:

- **Admission record** — how many days was the patient admitted, and is the
  patient's insurance ID valid for that stay?
- **Doctor's notes** — what disease was diagnosed, and what treatment was
  actually given? These live as free-text clinical notes, not structured data.
- **Coding** — the diagnosis has to be mapped to a standard disease code
  (e.g. ICD-10) and the treatment to a standard procedure code (e.g. CPT),
  because insurers only recognize claims in this coded form.
- **Doctor's verification** — someone has to confirm the coded diagnosis and
  treatment actually match what was clinically done (sign-off), otherwise the
  claim can be rejected or flagged as fraud later.
- **Insurance policy rules** — every policy has its own coverage limits,
  exclusions, room-rent caps, and pre-conditions. Whether a given
  diagnosis/treatment combination is eligible for reimbursement, and how much
  of it is eligible, is a matter of *interpreting* the policy document, not
  just looking up a number.
- **Money math** — once eligibility is known, the split between
  insurance-covered amount and patient-payable amount has to be computed
  correctly against the actual hospital bill.
- **Document generation** — finally, a claim form (to the insurer) and a
  discharge bill (to the patient) are generated.

Today this is a slow, manual, error-prone relay race between the billing desk,
the doctor, and the insurance desk. The goal of this case study is to design
an **agentic system** that automates this relay — but to do so *thoughtfully*,
not by throwing an LLM at every step.

### Why this is a good case for AI Agents

This workflow is deliberately a mix of two very different kinds of steps, and
telling them apart is the whole point of the exercise:

1. **Deterministic steps** — fetching a record from a database, looking a code
   up in a table, adding numbers, filling a template. These need **no
   reasoning at all**. Wrapping an LLM around them would be slower, more
   expensive, and less reliable than just calling a function. These become
   **tools** (plain Python functions).

2. **Judgment steps** — reading a doctor's free-text note and pulling out the
   diagnosis and treatment; deciding whether a treatment is *clinically
   consistent* with a diagnosis; deciding whether a specific
   diagnosis/treatment combination is *eligible* under a policy full of
   exclusions and edge cases. These require reading unstructured text,
   applying general knowledge, and making a judgment call under ambiguity.
   These are where an **LLM agent** (using a ReAct-style loop: Thought →
   Action → Observation) earns its keep, because it can decide *which* tool
   to call, call it, read the result, and decide what to do next — including
   asking for a human review when it isn't confident.

Students should come away understanding that **"agentic" doesn't mean
"everything goes through an LLM."** A well-designed agentic system is mostly
boring, deterministic code, with an LLM-driven ReAct loop reserved for the
handful of steps that truly need judgment or language understanding.

### Mapping to the hand-drawn flow

The original sketch for this case study maps onto the pipeline like this:

| # in sketch | What it represents | Pipeline step(s) |
|---|---|---|
| ① | Patient's Insurance ID, days covered | `get_patient_record` |
| ② | Doctor → Disease → Code | `get_doctor_notes`, `extract_diagnosis_and_treatment`, `lookup_icd_code` |
| ③ | Doctor's verification | `verify_doctor_signoff`, `check_diagnosis_treatment_consistency` |
| ④ | Patient insurance cover, amount covered vs. claimed | `get_insurance_policy`, `calculate_covered_amount`, `calculate_patient_payable` |
| ⑤ | Insurance rules & regulations | `check_eligibility` |
| ⑥ | Insurance can be claimed | `calculate_covered_amount` (post-eligibility) |
| ⑦ | Discharge + bill generated | `generate_claim_form`, `generate_discharge_bill` |

---

## 2. Functions Needed

Below is the full function catalog. Each function is tagged as either:

- **[TOOL]** — a plain deterministic function. Called directly, by code or by
  an agent, with no LLM reasoning involved in *what* it does internally.
- **[AGENT]** — a step that genuinely benefits from LLM reasoning (reading
  unstructured text, applying judgment, interpreting ambiguous rules). In the
  notebooks, these are implemented as a small ReAct loop that itself calls
  one or more `[TOOL]` functions.

### 2.1 Data retrieval (all `[TOOL]`)

```
get_patient_record(patient_id) -> dict
    Returns {patient_id, name, insurance_id, admission_date, discharge_date,
             days_admitted}

get_doctor_notes(patient_id) -> str
    Returns the raw free-text clinical note written by the treating doctor.

get_insurance_policy(insurance_id) -> dict
    Returns {policy_id, coverage_limit, room_rent_limit_per_day,
             covered_procedures, excluded_procedures, deductible}

get_hospital_bill_items(patient_id) -> list[dict]
    Returns itemized charges: [{item, category, amount}, ...]

get_doctor_signoff_status(patient_id) -> dict
    Returns {signed_off: bool, signed_by, timestamp | None}
```

### 2.2 Coding & validation (all `[TOOL]`)

```
lookup_icd_code(disease_name) -> str | None
    Looks up a disease name against a static ICD-10 reference table.

lookup_procedure_code(treatment_name) -> str | None
    Looks up a treatment/procedure name against a static CPT-style table.

validate_code_exists(code, code_type) -> bool
    Sanity-checks a code against the reference table (code_type = "ICD" | "CPT").
```

### 2.3 Judgment steps (`[AGENT]`, each internally calls `[TOOL]`s)

```
extract_diagnosis_and_treatment(doctor_notes_text) -> dict   [AGENT]
    Reads unstructured doctor notes and extracts a structured
    {diagnosis: str, treatment: str} pair. Internally may call
    lookup_icd_code / lookup_procedure_code to confirm the extracted
    terms map to valid codes, and re-reads the note if a code isn't found.

check_diagnosis_treatment_consistency(diagnosis, treatment) -> dict  [AGENT]
    Judges whether the treatment is clinically reasonable for the stated
    diagnosis. Returns {consistent: bool, reasoning: str,
    needs_human_review: bool}. This is a judgment call, not a lookup.

check_eligibility(policy, diagnosis_code, procedure_code, days_admitted)
    -> dict   [AGENT]
    Interprets the policy's covered/excluded lists and limits to decide
    whether, and how much of, this claim is eligible. Returns
    {eligible: bool, eligible_amount_cap: float | None, reasoning: str}.
    Internally calls validate_code_exists and reads policy exclusion text.
```

### 2.4 Money math (all `[TOOL]`, purely arithmetic once inputs are known)

```
calculate_total_bill(bill_items) -> float

calculate_covered_amount(policy, total_bill, days_admitted,
                          eligibility_result) -> float
    Applies room-rent-per-day caps, the eligibility cap, and the overall
    coverage_limit to compute what insurance will actually pay.

calculate_patient_payable(total_bill, covered_amount) -> float
```

### 2.5 Output generation (all `[TOOL]`)

```
generate_claim_form(patient_record, diagnosis_code, procedure_code,
                     covered_amount, eligibility_reasoning) -> dict

generate_discharge_bill(patient_record, total_bill, covered_amount,
                         patient_payable) -> dict
```

### 2.6 Control / escalation (`[TOOL]`, called by the agent or orchestrator)

```
flag_for_manual_review(patient_id, reason) -> dict
    Records that this claim needs a human to look at it, instead of letting
    the pipeline auto-approve something it isn't sure about.
```

### 2.7 The orchestrator

```
orchestrate_claim_process(patient_id) -> dict   [CONTROLLER]
    Not itself an LLM call. This is the plain-Python "conductor" that
    decides, step by step, whether to call a [TOOL] directly or hand control
    to the ReAct agent for a [AGENT] step, and assembles the final result.
    See Notebook 2.
```

This catalog is deliberately built so that **10 of the 13 core functions are
plain tools**, and only **3** genuinely need an LLM. That ratio is the lesson:
most of an agentic system is ordinary software; the agent is a scalpel, not a
hammer.
