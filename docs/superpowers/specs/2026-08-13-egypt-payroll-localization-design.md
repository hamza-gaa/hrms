# Egypt Payroll & HR Localization — Architecture Spec

**Date:** 2026-08-13
**Source:** `docs/Payroll System.rtf.doc` (Egyptian payroll/HR requirements document)
**Status:** Approved design, pending decomposition into per-area implementation plans

## 1. Purpose

Add Egypt as a supported country in Frappe HR (HRMS), matching the payroll,
leave, tax, and compliance rules described in the source document, for an
Egyptian company with Arabic-speaking HR staff. This spec covers the target
architecture; each of the five functional areas below becomes its own
implementation plan.

## 2. Existing Extension Points (confirmed via codebase trace)

HRMS already supports country-specific behavior through:

- **`regional_overrides` hook** (`hrms/hooks.py`) — maps `Country -> {function
  path: override path}`, consumed by ERPNext's `@erpnext.allow_regional`
  decorator. Currently used by India (HRA exemption, marginal relief) and
  unused by UAE.
- **`hrms/regional/<country>/setup.py`** — per-country custom fields
  (`create_custom_fields`) and seed doctype records, invoked from
  `hrms/setup.py` when a Company's country is set/changed.
- **`hrms/regional/<country>/utils.py`** — Python override implementations
  for the above hook functions.
- **`Income Tax Slab` / `Taxable Salary Slab`** — already implements generic
  progressive/marginal bracket tax calculation
  (`income_tax_slab.py:calculate_base_tax_from_tax_slabs`), plus a
  `standard_tax_exemption_amount` field already subtracted from taxable
  income pre-slab (`salary_slip.py:compute_taxable_earnings_for_year`,
  lines ~1004-1012, ~1071-1085).
- **`exempted_from_income_tax`** flag on Salary Component deduction rows —
  already generically excludes a deduction (e.g. employee social insurance
  share) from taxable earnings
  (`salary_slip.py:get_taxable_earnings`, lines ~2085-2094). This is not
  India-specific; no new code needed to make social-insurance-before-tax
  work for Egypt.
- **`Salary Component`** `formula`/`condition` fields — evaluated per-slip
  against employee, assignment, and already-computed component data
  (`salary_slip.py:eval_condition_and_formula`), sufficient to express
  bounded formulas like `min(max(GP * 0.75, min_wage), max_wage)`.
- **`Gratuity` / `Gratuity Rule` / `Gratuity Rule Slab`** — generic
  end-of-service payout engine, already proven by the UAE regional module
  (3 seeded `Gratuity Rule` records, zero Python overrides).
- **`Overtime Slip`** and shift day/night detection — already exists in
  `hrms/hr/doctype/overtime_slip/` and `shift_type.py`.

**Net conclusion:** the large majority of the source document is
configuration (doctype records/fixtures) on top of existing generic engines,
not new business logic. Genuine gaps are narrow and enumerated per section
below.

## 3. Module Structure

New module `hrms/regional/egypt/`, following the India/UAE pattern:

```
hrms/regional/egypt/
├── __init__.py
├── setup.py            # custom fields, seed records, install/uninstall hooks
├── utils.py             # Python overrides (only where a real gap exists)
└── data/
    └── salary_components.json   # standard Egypt salary component fixtures
```

Wired into `hrms/hooks.py`:
- `regional_overrides["Egypt"]` for any function-level overrides identified
  below (expected to be empty or near-empty per the trace in §2 — most
  behavior needs no Python override).
- Company-country dispatch in `hrms/setup.py` (same call site India/UAE use)
  to run `egypt.setup.setup()` on company creation/country change.

Five functional areas, each a separate implementation plan:

1. Employee master data (custom fields)
2. Leave rules (tenure tiers, once-per-career, eligibility, tiered sick leave)
3. Salary structure & income tax
4. Statutory funds (new doctype)
5. Arabic labels (translation-only)

## 4. Area 1 — Employee Master Data

**New Employee custom fields** (via `create_custom_fields()` in
`egypt/setup.py`, grouped under a new "Egypt Compliance" section, mirroring
`hrms/regional/india/setup.py:22-25`):

| Field | Type | Notes |
|---|---|---|
| `custom_national_id` | Data | |
| `custom_national_id_issue_date` / `_expiry_date` | Date | |
| `custom_social_insurance_number` | Data | drives "insured employee" checks used by leave eligibility and statutory funds |
| `custom_social_insurance_date` | Date | |
| `custom_passport_id`, `_issue_date`, `_expiry_date` | Data/Date | |
| `custom_military_status` | Select: Exempt / Completed / Postponed / Serving | |
| `custom_religion` | Data | |
| `custom_educational_specialization`, `custom_graduation_year` | Data/Int | |
| `custom_place_of_birth`, `custom_mothers_name` | Data | |
| `custom_work_permit_start_date`, `_expiry_date` | Date | foreign employees |
| `custom_insurance_id` | Data | |
| `custom_is_person_of_determination` | Check | drives 38-day leave tier, disability Income Tax Slab selection, 30k exemption |

**Family data & emergency contacts** — reuse ERPNext's existing family/
dependent child tables on Employee if present at implementation time
(verify during Area 1 planning); otherwise add two small Egypt-scoped child
tables (spouse/children basic data, emergency contacts). Not a full
dependent-management subsystem — the source document only needs record
capture, no workflow around it.

**Relatives working at the company** — new child table
`Egypt Employee Relative` (Employee Name, Degree of Kinship, Department,
Position) on Employee, since no existing conflict-of-interest tracking
exists in HRMS.

**Required reports** (Employment Contract, Form 1, hiring-by-date/
department/job) — standard Frappe Report Builder / Query Reports against
Employee, no new architecture; built during Area 1 implementation.

## 5. Area 2 — Leave Rules

**Tenure-tiered accrual.** Extend `Leave Policy Detail`
(`hrms/hr/doctype/leave_policy_detail/leave_policy_detail.json`) with
optional fields, used only when populated so non-Egypt companies are
unaffected:

- `service_tier_table` — new child doctype `Leave Policy Service Tier`
  (`min_years` Int, `max_years` Int nullable, `days` Float). When rows
  exist, tiered lookup overrides the flat `annual_allocation`.
- `min_years_of_service` (Int, default 0) — leave type not grantable before
  this tenure (Hajj: 5).
- `is_lifetime_once` (Check) — once granted, blocks all future allocation
  for that employee + leave type combination (Hajj: granted once per
  career).

**Tiered-payout leave (sick leave).** New optional child table on
`Leave Type` — `payout_tiers` (`from_day`, `to_day`, `pay_percent`) plus
`cycle_years` (Int). Represents one entitlement pool consumed sequentially
within a rolling N-year cycle at decreasing pay percentages (Egypt: 90
days @ 100%, next 90 @ 85%, next 90 @ 75%, inside a 3-year cycle). Payroll
reads cumulative days taken against this table to compute partial pay,
extending the existing `is_ppl` (partial-pay-leave) mechanism rather than
replacing it.

**Allocation engine hook.** `leave_policy_assignment.py` already computes
accrual from `date_of_joining`. Add one new call-out point (not a full
rewrite) where tier/lifetime-once fields are read when present, falling
back unchanged to today's flat logic otherwise. Implementation plan for
this area must pin the exact function and line.

**Eligibility gating.** Two new optional `Leave Type` fields:
`requires_insurance` (Check) and `requires_attachment` (Check), validated
in `Leave Application.validate()` via a small Egypt-aware check (insurance
status read from `custom_social_insurance_number`).

**Other leave types from the document** (Hard work leave, Study leave,
Paternity leave, Public holiday compensation, Weekly-rest compensation,
Work injury leave, Military conscription leave, Mission leave, paid/unpaid
absence, Maternity leave with a 3-times-per-career cap) — expressed as
standard `Leave Type` records using the fields above (`min_years_of_service`,
`is_lifetime_once` generalizes to "max N times" via a small `max_lifetime_count`
Int field alongside `is_lifetime_once`, rather than a boolean-only cap).

## 6. Area 3 — Salary Structure & Income Tax

**Effective-dated statutory parameters.** New doctype
`Egypt Statutory Settings`, one record per `effective_from` date (mirrors
`Income Tax Slab`'s existing dated-record pattern so historical payroll
reruns stay correct):

- Min/Max Basic Wage
- Min/Max Insurance Wage
- Social insurance employee rate (11%) / employer rate (18.75%)
- Overtime multipliers (1.35 day / 1.70 night / 2.0 rest-day & holiday)
- Statutory fund default rates (feeds Area 4)

This doctype also serves as the "Fixed Parameters Entry Screen" from the
source document — no separate screen needed.

**Salary Components** (seeded fixtures in `egypt/data/salary_components.json`,
editable per company): Basic Salary, Meal Allowance, Grants, Living Cost,
Wage Supplement, Performance Motivation, Production Motivation,
Transportation Allowance, Gross Salary, and a formula-based Insurance Wage
component:

```
min(max(GP * 0.75, egypt_min_insurance_wage), egypt_max_insurance_wage)
```

where `egypt_min_insurance_wage`/`egypt_max_insurance_wage` are fetched via
a small whitelisted helper added to `COMPONENT_EVAL_GLOBALS`
(`hrms/payroll/utils.py`) that reads the active `Egypt Statutory Settings`
record for the slip's date. Employee's Social Insurance Contribution
deduction component is flagged `exempted_from_income_tax = 1` (existing
generic mechanism — no code change).

**Income Tax Slab.** Two seeded slab records:
- `Egypt Income Tax Slab - Standard` — brackets at 0% / 10% / 15% / 20% /
  22.5% / 25% / 27% per the document's table, `standard_tax_exemption_amount
  = 20000`.
- `Egypt Income Tax Slab - Disability` — same brackets,
  `standard_tax_exemption_amount = 30000`.

HR assigns the correct slab per employee via the existing
`Salary Structure Assignment.income_tax_slab` Link field (already
per-employee/per-assignment) — no new hook, no regional Python override.
This was confirmed against the actual tax-calculation trace (§2); both the
personal exemption and the pre-tax social-insurance deduction are handled
by existing generic mechanisms.

**Overtime.** Reuse `Overtime Slip` + shift day/night detection. Egypt
setup seeds multiplier configuration (from `Egypt Statutory Settings`) and
adds validation for "no overtime below 30-minute threshold," "no overtime
for manager-grade employees except rest-day/holiday work," and "no overtime
for gross salary > 25,000 EGP except rest-day/holiday work" — small
additions to the existing overtime calculation path, not a new doctype.
Implementation plan must pin the exact function.

**Gratuity / End-of-service.** Reuse `Gratuity` + `Gratuity Rule` +
`Gratuity Rule Slab` (proven pattern from UAE). Leave-encashment formula
(`Gross Salary × 0.75 × days_encashed / 30`, only after 3 consecutive years
of service, taxed after calculation) is a new Egypt-specific calculation —
implementation plan must locate HRMS's existing leave encashment flow (if
any) and either extend it or add an Egypt-scoped equivalent modeled on it.

## 7. Area 4 — Statutory Funds

New doctype **`Egypt Statutory Fund`**, one record per fund type per
company per period:

| Field | Type |
|---|---|
| `fund_type` | Select: Emergency Relief Fund / Martyrs' Families Fund / Training & Rehabilitation Fund / Social, Health & Cultural Services Fund |
| `company` | Link (Company) |
| `period_start`, `period_end` | Date |
| `insured_employee_count` | Int, snapshot |
| `rate_or_amount` | Percent or Currency, sourced from `Egypt Statutory Settings` |
| `min_value`, `max_value` | Currency, per-fund bounds (e.g. Cultural Fund 8–16 EGP, Training Fund 10–30 EGP) |
| `computed_contribution` | Currency |
| `status` | Select: Draft / Computed / Paid |

Whitelisted method `compute()`: counts active employees with
`custom_social_insurance_number` set for the company, checks the fund's
headcount threshold (≥20 or ≥30 per fund), applies rate/min/max, sets
`computed_contribution`. This is standalone compliance/reporting data — it
does not post to Salary Slip or GL; it satisfies the document's "Special
Funds Calculation Screen" as a dedicated screen, matching how the source
document itself separates it from per-employee payroll.

## 8. Area 5 — Arabic Labels & RTL

Translation-only, no schema impact:

- Arabic labels for all new Egypt doctype fields via Frappe's standard
  Translation tool (`ar` locale), same mechanism as the existing
  `hrms/locale/ar.po`.
- Frappe Desk already renders RTL automatically when a user's language is
  Arabic — no work needed.
- `frontend/` (PWA) and `roster/` RTL CSS support is explicitly **out of
  scope** for this spec; flagged as a follow-up only if the customer needs
  Arabic in those apps specifically.

## 9. Explicitly Out of Scope

- Full family/dependent management workflows (only data capture, per §4).
- Payroll GL posting changes for statutory funds (reporting/compliance only,
  not a ledger integration, per §7).
- `frontend/`/`roster/` RTL support (§8).
- Any regime other than the 2026 Egyptian values described in the source
  document — future law changes are handled via new dated
  `Egypt Statutory Settings` / `Income Tax Slab` records, not code changes.

## 10. Implementation Order (proposed)

1. **Area 1 — Employee master data.** No dependencies; unblocks the
   "insured employee" checks used by Areas 2 and 4.
2. **Area 3 — Salary structure & income tax.** Core payroll value; depends
   on Area 1 only for the disability-exemption slab selection.
3. **Area 2 — Leave rules.** Independent of Area 3; depends on Area 1 for
   insurance-eligibility checks.
4. **Area 4 — Statutory funds.** Depends on Area 1 (headcount) and Area 3
   (`Egypt Statutory Settings` rates).
5. **Area 5 — Arabic labels.** Can run in parallel with any area once its
   fields are finalized; naturally trails each area's field additions.

Each area gets its own spec-to-plan cycle via `writing-plans` before
implementation begins.
