# Egypt Payroll Gap Closure — Architecture Spec

**Date:** 2026-08-15
**Source:** `docs/Payroll System.rtf.doc`, cross-checked line-by-line against
the current implementation on branch `feat/egypt-employee-master-data`
(post the Egypt payroll-localization work in
`docs/superpowers/specs/2026-08-13-egypt-payroll-localization-design.md`
and its five implementation plans).
**Status:** Approved design, pending decomposition into per-feature
implementation plans.

## 1. Purpose

The 2026-08-13 spec and its five plans (Areas 1-5) implemented the large
majority of `docs/Payroll System.rtf.doc`. A full re-read of the source
document against the shipped code (this session, 2026-08-15) found three
genuine functional gaps that need new fields/doctypes/logic, not just seed
data — a seed script cannot add data for a field that does not exist yet.
This spec covers those three gaps. It also corrects one real numeric error
found in the same pass (already fixed, not part of this spec's scope) and
documents two items confirmed out of scope on purpose.

See `docs/superpowers/EGYPT-COMPLIANCE-FINDINGS.md` for the full line-by-line
cross-reference this spec is derived from.

## 2. What This Spec Does NOT Cover

- **Income tax bracket-schedule variants.** The source document's tax table
  (lines 631-678) describes six income-dependent bracket schedules (the top
  bracket's threshold shifts between 600K/700K/800K/900K/1,200K EGP
  depending on the taxpayer's total annual income tier). Frappe's
  `Income Tax Slab` doctype holds one linear bracket ladder per record —
  it cannot represent "which schedule applies" as a function of total
  income. The already-seeded `Egypt Income Tax Slab - Standard`/
  `- Disability` records were corrected this session (2026-08-15) to match
  the document's highest-income schedule variant (25% bracket now runs
  400K-1,200K, 27% starts at 1,200K, not 600K as previously seeded) — this
  fix already landed in `hrms/regional/egypt/setup.py` outside this spec.
  Representing all six variants would require new logic beyond Income Tax
  Slab's data model and is explicitly out of scope here pending a decision
  on how much of that nuance the business actually needs modeled.
- **Late Policy (5-minute grace period).** Already achievable via the
  existing, unmodified `Shift Type.late_entry_grace_period` field — this is
  a configuration task for whoever sets up a company's shifts, not a code
  gap. No implementation needed.
- **Resignation statistics report** (by date/reason/department breakdown,
  doc line 799). The existing `Employee Exits` report (ERPNext/HRMS core)
  provides a raw per-employee listing with a chart, not an aggregated
  breakdown by reason. Flagged in the compliance findings doc as a
  candidate follow-up; not included in this spec since it's a reporting
  gap, not a payroll-calculation gap, and the three features below are
  already a full architectural spec's worth of scope.
- **Form 1 / Form 6.** Government-form content, deliberately not
  fabricated — unchanged from the 2026-08-14 required-reports plan's
  decision (see that plan's Task 4 notes).
- **Gratuity Rule slab values.** The seeded `Egypt Standard Gratuity Rule`
  (0.5x years 0-5, 1.0x years 5+) was never sourced from this document —
  the document never mentions gratuity/severance. Its values remain
  unconfirmed placeholders from general Egyptian labor-law knowledge, not
  a gap this spec addresses (nothing to close against a source that says
  nothing).

## 3. Confirmed Against Current Code (2026-08-15)

- `Egypt Statutory Settings` (`hrms/payroll/doctype/egypt_statutory_settings/`)
  currently has: `effective_from`, `company`, `disabled`,
  `min_basic_wage`, `max_basic_wage`, `min_insurance_wage`,
  `max_insurance_wage`, `social_insurance_employee_rate`,
  `social_insurance_employer_rate`, `overtime_day_multiplier`,
  `overtime_night_multiplier`, `overtime_rest_day_multiplier`,
  `emergency_relief_fund_rate`, `cultural_services_fund_min`/`_max`,
  `training_fund_rate`, `training_fund_min`/`_max` — no bonus or loan
  fields. Confirmed by reading `egypt_statutory_settings.json` directly.
- `hrms/regional/egypt/data/salary_components.json` currently seeds 11
  components (Basic Salary, Meal Allowance, Grants, Living Cost, Wage
  Supplement, Performance Motivation, Production Motivation,
  Transportation Allowance, Gross Salary, Insurance Wage, Social Insurance
  Contribution) — no Annual Bonus component. Confirmed by reading the file.
- `hrms/regional/egypt/utils.py` currently exports
  `validate_overtime_detail` and `calculate_leave_encashment_amount`,
  both wired via `regional_overrides["Egypt"]` against hook functions
  **owned by hrms** (`Overtime Slip`, `Leave Encashment` — both live under
  `hrms/hr/doctype/`). Confirmed by reading `hrms/hooks.py:305-316`.
- **`Loan` is an ERPNext-core doctype, not hrms-owned.** `hrms/hooks.py`
  wires `doc_events["Loan"]["validate"] =
  "hrms.hr.utils.validate_loan_repay_from_salary"` — a function hrms
  itself defines in a file hrms owns (`hrms/hr/utils.py`), reacting to a
  Frappe `doc_events` lifecycle hook, not a call site inside Loan's own
  controller (which hrms cannot edit). This is the same mechanism India's
  regional overrides use for `calculate_annual_eligible_hra_exemption`
  etc. (`hrms.hr.utils.*` functions decorated `@hrms.allow_regional`) —
  confirmed by reading `hrms/hooks.py:212,305-309` and
  `hrms/__init__.py:32-51` (the `allow_regional` decorator implementation).
  **This means the Egypt loan-cap override must follow the
  `hrms/hr/utils.py` + `@hrms.allow_regional` pattern, not the
  `<doctype>.py`-owned-hook pattern Overtime Slip/Leave Encashment use** —
  those two are hrms-owned doctypes, Loan is not.
- No `Egypt Employee Penalty` or equivalent doctype exists anywhere in the
  repo (confirmed via filesystem search). No dedicated Penalty tracking
  exists in hrms core either — deductions currently flow only through
  generic Leave-Without-Pay proration
  (`salary_slip.py:calculate_lwp_ppl_and_absent_days_based_on_attendance`)
  or manually-entered Salary Slip deduction rows, neither of which
  tracks a reason category or enforces a cap.

## 4. Module Structure

All three features live inside the existing `hrms/regional/egypt/` module
(no new top-level module) plus one new doctype folder, following the
established pattern:

```
hrms/regional/egypt/
├── setup.py                          # +2 fields, +1 salary component, wiring
├── utils.py                          # +1 function: validate_egypt_loan_cap
└── data/
    └── salary_components.json        # +1 record: Annual Bonus

hrms/hr/utils.py                      # +1 function: validate_loan_cap
                                       #   (@hrms.allow_regional, hrms-owned
                                       #   call site for the Egypt override)

hrms/payroll/doctype/egypt_employee_penalty/   # NEW doctype
├── egypt_employee_penalty.json
├── egypt_employee_penalty.py
└── test_egypt_employee_penalty.py
```

Wired into `hrms/hooks.py`:
- `regional_overrides["Egypt"]["hrms.hr.utils.validate_loan_cap"] =
  "hrms.regional.egypt.utils.validate_egypt_loan_cap"` (new entry,
  alongside the existing two Egypt entries).
- No new `doc_events` entries needed — `Loan`'s existing
  `doc_events["Loan"]["validate"]` already calls
  `validate_loan_repay_from_salary`, which this spec extends to also call
  the new `validate_loan_cap` (itself a no-op outside Egypt via
  `allow_regional`).
- `Egypt Employee Penalty` belongs to the `Payroll` module (matching
  `Egypt Statutory Fund`, `Egypt Statutory Settings` — compliance/
  financial-tracking doctypes live in Payroll, not HR, in this codebase's
  existing convention).

## 5. Feature 1: Annual Bonus

**Source:** doc lines 251-264.

> An amount added to the basic salary at a rate of 3% of the insured wage,
> with a minimum of 250 EGP... The employee must have completed a full
> year or more by January of each year.

**Design:** a new, optional `Annual Bonus` Salary Component (Earning,
`amount_based_on_formula=1`), matching the existing `Insurance Wage`
component's formula-based pattern exactly — not auto-added to any Salary
Structure (HR opts a structure into it, same as every other Egypt salary
component).

- Two new fields on `Egypt Statutory Settings`: `annual_bonus_rate`
  (Percent, default `3`), `annual_bonus_minimum_amount` (Currency, default
  `250`).
- New helper `egypt_annual_bonus_amount(date_of_joining, company=None,
  date=None, insurance_wage=None) -> float`, registered in
  `COMPONENT_EVAL_GLOBALS` (same registration point
  `egypt_insurance_wage_bounds` already uses — confirmed in
  `hrms/payroll/utils.py`, NOT `salary_component.py` as an earlier draft
  of this spec assumed; `COMPONENT_EVAL_GLOBALS` and
  `egypt_insurance_wage_bounds` both live in `hrms/payroll/utils.py`).
  Computes tenure-eligibility (≥1 full year of service as of January 1 of
  `date`'s year) and returns `max(insurance_wage * annual_bonus_rate/100,
  annual_bonus_minimum_amount)` if eligible, else `0`. **Takes
  `date_of_joining`/`company`, not `employee`** — confirmed by reading
  `get_component_eval_context()` (`hrms/payroll/utils.py:107`): a Salary
  Component formula's evaluation context is built by merging the
  employee's own doc fields directly into the eval namespace (so
  `date_of_joining`, `company` are bare variables), it never includes a
  variable literally named `employee`. `Insurance Wage`'s own existing
  formula follows the same constraint — it takes `date`/`company`, not
  `employee`, for the same reason.
- Salary Component formula: `egypt_annual_bonus_amount(date_of_joining,
  company, getdate(), IW)` — `IW` is Insurance Wage's own component
  abbreviation, resolved to its already-computed amount earlier in the
  same slip evaluation, the same mechanism `Social Insurance
  Contribution`'s `IW * 0.11` formula relies on.
- Seeded into `hrms/regional/egypt/data/salary_components.json` as a 12th
  record (`"salary_component": "Annual Bonus"`, `"salary_component_abbr":
  "ANB"` — `"AB"` avoided as too likely to collide with an
  already-existing site-wide component abbreviation outside this Egypt
  fixture set, `"type": "Earning"`, `"is_tax_applicable": 1`,
  `"amount_based_on_formula": 1`, `"formula":
  "egypt_annual_bonus_amount(date_of_joining, company, getdate(), IW)"`).

**Not in scope:** automatic once-a-year triggering. Same pattern as every
other Egypt component — it computes correctly whenever a Salary Slip
includes it, but nothing forces HR to run payroll with it included only in
January. This matches the source document's framing (a payroll-parameter
rate, not a scheduled batch job) and the existing Egypt Statutory Fund's
"HR runs this per period" convention.

## 6. Feature 2: Loan Cap

**Source:** doc lines 266-275.

> Any loans given by the company to the employee... must be interest-free.
> The monthly installment should not exceed 10% of the employee's salary.

**Design:** extend the existing `validate_loan_repay_from_salary` in
`hrms/hr/utils.py` to call a new `@hrms.allow_regional`-decorated
`validate_loan_cap(doc)` function (no-op outside Egypt), and add the Egypt
override in `hrms/regional/egypt/utils.py`:

```python
# hrms/hr/utils.py — new function, called from validate_loan_repay_from_salary
@hrms.allow_regional
def validate_loan_cap(doc):
    pass  # no-op outside regions that override it


# hrms/regional/egypt/utils.py — Egypt override
def validate_egypt_loan_cap(doc):
    if doc.applicant_type != "Employee" or not doc.repay_from_salary:
        return
    if flt(doc.rate_of_interest) != 0:
        frappe.throw(_("Loans to employees must be interest-free"))
    gross_salary = _get_gross_salary(doc.applicant)
    if gross_salary and flt(doc.monthly_repayment_amount) > gross_salary * 0.10:
        frappe.throw(_("Monthly loan installment cannot exceed 10% of the employee's salary"))
```

Reuses the existing `_get_gross_salary` helper already in
`hrms/regional/egypt/utils.py` (added for the overtime cap check) — no new
salary-lookup code needed.

**Not in scope:** loans that aren't repaid from salary (`repay_from_salary
= 0`) — the document's framing is specifically about payroll-deducted
company loans, and a loan with an external repayment channel isn't a
payroll-deduction-cap concern.

## 7. Feature 3: Deduction Caps (Egypt Employee Penalty)

**Source:** doc lines 774-787 (Employee deductions table).

> An employee may not be deducting more than 5 days off per month, and no
> more than 10% may be deducted from their total monthly salary. If the
> employee has taken out a loan or damages something of value, the
> discount rate can be increased to 25%, and if they have court-ordered
> alimony payments, the discount rate can be increased to 50%.

Also: "Penalties: If the violation is in the penalty regulations → Based on
Insurance Wage" / "If an employee damages something of value → Fixed
Value" (doc lines 781-783).

**Design:** new doctype `Egypt Employee Penalty`, one record per
disciplinary/deduction incident:

| Field | Type | Notes |
|---|---|---|
| `employee` | Link (Employee), required | |
| `penalty_date` | Date, required | Determines which calendar month's cap it counts against |
| `reason_category` | Select: `Violation`, `Damage`, `Alimony`, required | Determines the applicable cap tier |
| `basis` | Select: `Insurance Wage`, `Fixed Value` | Per doc: Violation → Insurance Wage-based, Damage → Fixed Value. Alimony has no basis specified in the document (court-ordered figure) — Fixed Value by default, editable. |
| `amount` | Currency, required | The computed or fixed deduction amount |
| `days_deducted` | Int, default 0, non-negative | For absence-type deductions counting toward the 5-day/month cap; 0 for pure monetary penalties that don't consume absence-days |
| `status` | Select: `Draft`, `Applied` — default `Draft` | Mirrors `Egypt Statutory Fund`'s Draft/Computed/Paid convention; `Applied` means it's been included in a Salary Slip |

**Validation (on submit, or a `validate_monthly_caps()` whitelisted
method — implementer's call during planning which is cleaner given
Frappe's document lifecycle):**
1. Sum `days_deducted` across all of this employee's `Egypt Employee
   Penalty` records in the same calendar month (including the one being
   validated) — throw if total exceeds 5.
2. Determine the cap percentage from `reason_category`: `Violation` → 10%,
   `Damage` → 25%, `Alimony` → 50%. (Document text: "loan or damages...
   25%" — a Loan-linked deduction is not itself a penalty incident in this
   doctype's model, since Loan already has its own repayment-amount cap
   from Feature 2; `Damage` alone maps to the 25% tier here, matching the
   document's "damages something of value" clause.)
3. Sum `amount` across the employee's records in the same calendar month
   (including this one) — throw if it exceeds `cap_percentage * gross
   salary` (reusing `_get_gross_salary`).

**Not in scope:** automatic creation of these records from Attendance
absences, or automatic inclusion in Salary Slip deduction rows. HR creates
records manually per incident (matching the doc's "should submit absence
request" framing for the related Absence-With/Without-Permission leave
types, which this plan already implements) and, once `Applied`, is
expected to reflect the amount in the Salary Slip's Deductions table by
hand — wiring this to auto-populate Salary Slip is a natural next step but
adds payroll-engine integration risk beyond what a first cut needs to
prove out the cap logic.

## 8. Cross-Feature Consistency

- All three features are purely additive to Egypt-scoped code paths
  (`hrms/regional/egypt/`, one new Egypt-owned doctype, one new
  `@allow_regional`-decorated function in an hrms-owned file that is a
  no-op for every other country). Zero behavior change for non-Egypt
  companies — same additive-only contract every prior Egypt plan this
  session upheld.
- `_get_gross_salary(employee)` (already in
  `hrms/regional/egypt/utils.py`) is reused by both Feature 2 and Feature
  3 rather than reimplemented — one salary-lookup helper, three
  consumers (it already serves the overtime cap check from the earlier
  leave-rules/statutory-funds work).
- Naming/module placement: `Egypt Employee Penalty` under `Payroll`
  module matches `Egypt Statutory Fund`/`Egypt Statutory Settings`
  (financial compliance tracking → Payroll), not `Egypt Employee
  Relative`/`Egypt Employee Spouse`/`Egypt Employee Child` (personal data
  child tables → HR module, under Employee).

## 9. Self-Review Notes

**Placeholder scan:** no vague "TBD" left. Every design decision above
traces to a specific document line and a specific confirmed code fact.

**Ambiguity resolved, not guessed:** the document's "loan or damages...
25%" phrase could be read as "Loan-linked penalties get 25%" — resolved
above (§7) as: Loan already has its own cap mechanism (Feature 2), so
`Egypt Employee Penalty`'s `Damage` category alone carries the 25% tier;
a loan doesn't need a matching penalty record since its own cap logic
already constrains it independently. Flagged explicitly here rather than
silently picked.

**Type/name consistency:** `_get_gross_salary` signature
(`employee -> float`) confirmed unchanged from its existing definition in
`hrms/regional/egypt/utils.py`, reused verbatim by both new features'
designs above — no new salary-lookup helper invented.
