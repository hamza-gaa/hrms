# Egypt Payroll System — Source Document Compliance Findings

**Date:** 2026-08-15
**Source:** `docs/Payroll System.rtf.doc` (converted to plain text for
this review; original is RTF, code page 1256, Arabic/Middle-East locale).
**Compared against:** branch `feat/egypt-employee-master-data` after the
five 2026-08-14 Egypt payroll-localization plans (Areas 1-5) plus this
session's fixes.

This document is a line-by-line cross-reference of every requirement in
the source document against the current codebase. It is the evidence
trail behind `docs/superpowers/specs/2026-08-15-egypt-payroll-gap-closure-design.md`.

## How to read this

- ✅ **Implemented** — verified against the actual code/data, not just a
  file's existence.
- ⚠️ **Partial / limitation** — something real exists but doesn't fully
  match the document, with the specific gap named.
- ❌ **Not implemented** — genuine gap.
- Every row cites the document's line number (in the converted plain-text
  version) and the specific file(s) checked.

---

## Section 1 — First: Employees Personal Data (doc lines 1-34)

### Personal data fields (doc lines 3-27)

✅ **Implemented.** All fields exist as `Employee` custom fields, added by
Area 1 (`hrms/regional/egypt/setup.py:get_custom_fields()`):
National ID, National ID Issue/Expiry Date (doc's "National Card
Issu/Expired date"), Social Insurance Number/Date, Insurance ID, Passport
ID/Issue/Expiry Date, Work Permit Start/Expiry Date, Military Status,
Religion, Place of Birth, Mother's Name, Educational Specialization,
Graduation Year, Is Person of Determination (doc's "Data of People of
Determination"). Standard ERPNext core `Employee` fields already cover
Employee Name, Hiring Date (`date_of_joining`), Position/Job Title
(`designation`), Nationality, Department, Cost Center, Sex (`gender`),
Birth Date, Phone Number, Address, Bank Account Number — confirmed during
Area 1's planning via `bench console` field inspection (see
`.superpowers/sdd/2026-08-13-egypt-employee-master-data/progress.md`'s
Task 1 ruling, cited from the prior session; not re-verified live this
session since no bench is available in this environment, but the field
list was directly read from ERPNext/Frappe core doctype JSON at the time).

**Family Data / Relatives / Emergency Contacts (doc lines 12-27):**
✅ Implemented as three child-table custom fields: `Egypt Employee Spouse`
(Wife name/Job/Birth Date), `Egypt Employee Child` (Son/Daughter's
Name/Job/Birth date), `Egypt Employee Relative` (Employee Name, Degree of
kinship, Department, Position — "Relatives work at the company"). Emergency
contacts ("Contacts to be reached in case of emergency") use core
ERPNext `Employee.person_to_be_contacted`/`emergency_phone_number`/
`relation` fields, confirmed already present and generic — no Egypt
custom field needed (Area 1's Task 5 was explicitly skipped for this
reason; see that plan's progress ledger).

### Required reports (doc lines 31-34)

- ✅ **Report for the hiring by date** —
  `hrms/hr/report/employee_hiring_by_date/` (Area "required-reports" plan).
- ✅ **Report for the hiring by Department** —
  `hrms/hr/report/employee_hiring_by_department/`.
- ✅ **Report for the hiring by Job** —
  `hrms/hr/report/employee_hiring_by_job/` (maps "Job" → ERPNext's
  `designation` field, confirmed no separate `job_title` field exists in
  this codebase).
- ✅ **Employment Contract** — scaffolded as `Egypt Employment Contract`
  print format targeting the existing `Appointment Letter` doctype
  (`hrms/hr/print_format/egypt_employment_contract/`). Legal clause text
  is deliberately NOT fabricated — inert `[FILL IN: ...]` HTML-comment
  placeholders a qualified legal reviewer must supply. This was an
  explicit, user-confirmed scope decision (not a gap).
- ❌ **Form 1** — not implemented at all. Deliberate: Form 1 is a specific
  numbered Egyptian government labor-registration form; neither the
  source document nor any session working on this codebase has its actual
  layout/field specification. Building a fake version risks being mistaken
  for the genuine government document. Requires the actual form content
  from the user or a local legal/HR consultant before any implementation
  is possible.

---

## Section 2 — Time and Attendance Monitoring (doc lines 36-180)

### Leave balance table (doc lines 38-46)

✅ **Implemented exactly.** `Leave Type Service Tier` child table on
`Egypt Regular Leave` (`hrms/regional/egypt/data/leave_types.json`):
0-1yr → 8 days, 1-10yr → 14 days, 10yr+ → 23 days. `Egypt Casual Leave`
flat 7 days (via Leave Policy, not the Leave Type itself — Leave Type
records only define entitlement *rules*, actual annual balances are
granted through `Leave Policy Detail`/`Leave Policy Assignment`, which
this plan doesn't seed — see note below under "What's genuinely turn-key
vs. needs configuration").

⚠️ **Partial.** The document's 4th column ("The person who has 10
insurance years or 50 years old") and 5th column ("People with
determination & dwarfs", 38 days) describe eligibility conditions the
tenure-only `service_tiers` mechanism cannot express — they depend on
`Employee.is_person_of_determination` (an Employee attribute) or "50
years old / 10 insurance years" (neither of which map to a tenure-years
counter). The 23-day tier is seeded keyed on `min_years=10` as an
approximation of the insurance-years threshold (no separate "insurance
years" counter exists anywhere in HRMS). The 38-day disability tier is
**not implemented** — flagged explicitly in the leave-rules plan's Task 5
notes as needing an Employee-attribute override layered on top of the
tenure-tiers mechanism, deliberately not attempted to avoid inventing an
untested cross-cutting rule.

### Individual leave types table (doc lines 51-180)

| Doc requirement | Status | Notes |
|---|---|---|
| Hard work leave, 7 days | ✅ | `Egypt Hard Work Leave`, flat entitlement type defined |
| Study leaves, per exam days | ✅ | `Egypt Study Leave`, `allow_negative=1` zero-allocation type for manual ad-hoc grants (event-triggered, no fixed annual figure per the doc itself) |
| Paternity leave, 3 days lifetime, 1/newborn | ✅ | `Egypt Paternity Leave`, `max_lifetime_allocations=3` |
| Public holidays | ⚠️ | Deliberately **not** a Leave Type — governed by ERPNext's existing `Holiday List` doctype instead, matching the document's own framing ("issued by decision of the competent minister," a company-wide calendar concept, not an employee-requested balance) |
| Hajj leave, 30 days, 5yr tenure, once/career | ✅ | `Egypt Hajj Leave`, `min_years_of_service=5`, `max_lifetime_allocations=1` |
| Weekly rest / Weekly rest2 | ⚠️ | Not Leave Types — `Holiday List` weekly-off configuration, per document's own framing |
| Instead of weekly rest / Instead of public holidays | ⚠️ | Not Leave Types — shift/overtime compensation concept (day off + 8hr overtime), out of Leave Type's scope; the overtime multiplier side (2.0x rest-day/holiday) IS implemented, see Section 3 |
| Work injury leave | ✅ | `Egypt Work Injury Leave`, `allow_negative=1`, `requires_insurance=1` |
| Military conscription leave | ✅ | `Egypt Military Conscription Leave`, `allow_negative=1` |
| Mission leave | ✅ | `Egypt Mission Leave`, `allow_negative=1` |
| Absence with permission (unpaid) | ✅ | `Egypt Absence With Permission`, `is_lwp=1` |
| Absence without permission (unpaid) | ✅ | `Egypt Absence Without Permission`, `is_lwp=1` |
| Sick leave: 90d@100%/180d@85%/90d@75%, 3yr cycle, insured only | ⚠️ | `Egypt Sick Leave` seeded as `requires_insurance=1`, flat **always-100%-paid** — the tiered 90/85/75% decay across a rolling 3-year window is **not implemented**. HRMS's only partial-pay mechanism (`is_ppl` + `fraction_of_daily_salary_per_leave`) applies one fixed fraction to every day used, with no tracking anywhere of cumulative days-used-so-far within a rolling window. Building that correctly needs new `Leave Allocation`/day-counter accounting in the payroll-calculation path (`salary_slip.py`) that doesn't exist today. The flat-100% seed is a safe, conservative default (never under-pays; may over-pay past day 90 within a cycle). Two candidate designs for closing this gap were noted in the leave-rules plan but neither was built (see that plan's Self-Review Notes) — this remains open, flagged, not silently dropped. |
| Maternity leave, 120 days, max 3/career | ✅ | `Egypt Maternity Leave`, `max_lifetime_allocations=3` |

**What's genuinely turn-key vs. needs configuration:** the 13 seeded
`Leave Type` records define entitlement *rules* (tenure tiers, minimum
service, lifetime caps, insurance requirement) — they do not by
themselves grant any employee a leave balance. An operator still needs to
create `Leave Policy`/`Leave Policy Detail`/`Leave Policy Assignment`
records referencing these types before any employee actually accrues
days. This is standard Frappe HR usage (not an Egypt-specific gap) but
worth stating plainly: these 13 records are type *definitions*, not
turn-key balances.

---

## Section 3 — Salaries and Their Distribution (doc lines 182-678)

### Definitions (doc lines 184-318)

| Term | Doc figure | Implementation | Status |
|---|---|---|---|
| Basic Wage | 440-2740 EGP (2026), +7%/yr | `Egypt Statutory Settings.min_basic_wage=440`/`max_basic_wage=2740` | ✅ (year-over-year +7% escalation is a manual re-seed each year via `effective_from`-dated records, not automated — matches how `Egypt Statutory Settings` is designed: dated snapshots, not a formula) |
| Insurance Wage | 4900-16700 EGP (2026), +15%/yr, = gross or 70% of it | `min_insurance_wage=4900`/`max_insurance_wage=16700`; `Insurance Wage` salary component formula: `min(max(GP*0.75, bounds[0]), bounds[1])` | ⚠️ **Correction — this was NOT previously reconciled; caught fresh in this pass.** The formula uses **75%** of gross as the base ratio, but the document's own definitions table (doc line 213: "Must be equal the gross salary or 70% of it") says **70%**. Checked the Area 3 plan text directly (`docs/superpowers/plans/2026-08-14-egypt-salary-structure-income-tax.md`) for any prior reconciliation note — **found none**; the plan simply transcribed `0.75` into the formula without ever mentioning the document's "70%" line at all, meaning this discrepancy was never actually checked before now. Independently verified this session: the document's own "Salary Distribution Proposal" worked example (doc lines 369-374) shows Insurance Wage = 5250 on Gross Salary = 7000, i.e. 5250/7000 = **75%**, contradicting the same document's own prose ("70%") two sections earlier. **This is a real internal contradiction in the source document itself** (not something introduced by the implementation) — the shipped code happens to match the document's own numeric example rather than its prose, which is a defensible reading but was never a deliberate, recorded decision until this pass. Flagged here as newly-caught, not previously-resolved, so a fresh reader doesn't assume this was already vetted. |
| Employee's share in social insurance | 11% of insurance wage | `social_insurance_employee_rate=11`, `Social Insurance Contribution` component formula `IW * 0.11` | ✅ |
| Company's share in social insurance | 18.75% of insurance wage | `social_insurance_employer_rate=18.75` | ✅ (field seeded; whether an employer-side contribution component/GL posting is wired is outside this document's payroll-slip scope per spec §9 "no GL/Salary Slip posting" for statutory funds — the settings value itself is captured and available) |
| Overtime pay | 1.35x day / 1.70x night / 2x rest-day-or-holiday | `overtime_day_multiplier=1.35`, `overtime_night_multiplier=1.70`, `overtime_rest_day_multiplier=2.0`; enforced via `hrms/regional/egypt/utils.py:validate_overtime_detail` | ✅ |
| Net Salary | Gross minus deductions | Standard ERPNext Salary Slip mechanism | ✅ (generic, no Egypt-specific code needed) |
| Income Tax | Per Egyptian tax law | `Egypt Income Tax Slab - Standard`/`- Disability`, see bracket discussion below | ⚠️ see below |
| Penalties | Per disciplinary regulations | No dedicated tracking | ❌ see Gap #3 below |
| Annual bonus | 3% of insurance wage, min 250 EGP, 1yr tenure by Jan | Not implemented | ❌ see Gap #1 below |
| Loan | Interest-free, ≤10% of salary/month | Not implemented | ❌ see Gap #2 below |
| Emergency Relief Fund | 1% of basic salaries, 30+ insured employees | `Egypt Statutory Fund` doctype, `emergency_relief_fund_rate=1`, threshold 30 | ✅ |
| Martyrs' Families Fund | 0.05% of gross salaries | Hardcoded module constant `0.0005` in `egypt_statutory_fund.py` (not a configurable `Egypt Statutory Settings` field) | ⚠️ deliberate scope limit, flagged as a follow-up if configurability is wanted — cross-referenced against the document's own worked example (7000 × 0.0005 = 3.50, matching doc line 400's "3.50 / 0.05%" row exactly) |
| Training and Rehabilitation Fund | 0.25% of min insurance wage, 10-30 EGP/employee, 30+ | `training_fund_rate=0.25`, `training_fund_min=10`/`_max=30`, threshold 30 | ✅ |
| Social, Health, Cultural Services Fund | 8-16 EGP/employee, 20+ insured | `cultural_services_fund_min=8`/`_max=16`, threshold 20 | ✅ (document has two slightly different framings — "8 L.E. flat" in the fund-definitions table vs. "8-16 EGP" in the Special Funds Calculation table at the very end of the document, doc line 820 — resolved as `min_value`=effective rate, `max_value`=future configurable ceiling, flagged not guessed) |
| Penalties fund | Distributed on liquidation | Doc's own table row is empty/unspecified (doc lines 315-318) | ❌ genuinely under-specified in the source document itself — no numeric rate, no headcount threshold given, nothing to implement against |

### Salary Distribution Proposal — component structure (doc lines 320-428, 450-628)

✅ **Implemented.** All named components exist as seeded `Salary
Component` records matching the document's element names exactly: Basic
Salary, Meal Allowance, Grants, Living Cost, Wage Supplement, Performance
Motivation, Production Motivation (blue-collar only per the doc — both
white-collar and blue-collar component sets use the same seeded component
list; a company builds its own Salary Structure choosing which components
apply per employee grade, which this seed data supports without needing
two separate hardcoded structures), Transportation Allowance, Gross
Salary, Insurance Wage. The specific percentage splits shown in the doc's
two example tables (10%/20%/10%/20%/20%/20% for white-collar vs.
10%/20%/10%/20%/15%/15%/10% for blue-collar) are Salary Structure
*configuration* an HR admin sets per grade when building their structure
— not something a fixed seed script should hardcode, since every company
using this software will have its own actual pay-grade percentages.

### Overtime Policy (doc lines 430-448)

✅ **Implemented exactly** — see the Definitions table row above. All
four rules (30-min threshold, manager exemption, 25K gross-salary cap,
multiplier formula) confirmed word-for-word against
`hrms/regional/egypt/utils.py:validate_overtime_detail`.

### Income Tax Brackets (doc lines 630-678) and Exemptions (doc lines 680-687)

✅ **Exemptions implemented exactly:** 20,000 EGP standard, 30,000 EGP
disability (50% uplift) — `Egypt Income Tax Slab - Standard`/`- Disability`
`standard_tax_exemption_amount` fields.

⚠️ **Bracket thresholds — corrected this session, one real limitation
remains.** The document's tax table (lines 631-678) is genuinely six
different bracket schedules depending on the taxpayer's total annual
income tier (columns 1-6, each a variant of the same 7-rate ladder with a
different top-bracket threshold: 600K/700K/800K/900K/1,200K/1,200K+ EGP).
The originally-seeded slab (written before this document was available to
the implementing session) had the top bracket ending at 600,000 EGP with
25%→27% transitioning there — this did not match ANY of the document's
six actual schedules correctly (it mixed the 400K-600K "25%" boundary
from one column with an incorrect early 27% cutoff). **Fixed this session**
(`hrms/regional/egypt/setup.py:make_income_tax_slabs`) to match the
document's rightmost/highest-tier schedule exactly: 25% now runs
400,000-1,200,000 EGP, 27% starts above 1,200,000 EGP. This is the
correct schedule for any employee whose income reaches the top bracket
tier, and the safest single choice among the six variants (using it for
everyone slightly under-charges tax for lower-income employees who
"should" be on an earlier-transitioning schedule, rather than
over-charging them). **The other five income-dependent schedule variants
are not implemented** — Frappe's `Income Tax Slab` doctype cannot
represent "which ladder applies" as a function of total income within a
single record. Closing this fully would need new logic selecting between
multiple `Income Tax Slab` records (or a custom tax-calculation override)
based on projected annual income — out of scope for a seed-data fix,
flagged for a decision on whether this level of nuance is actually needed.

---

## Section 4 — Employment Termination (doc lines 689-799)

### Termination types (doc lines 689-744)

✅ **Generically covered.** ERPNext core's `Employee.relieving_date` +
status transitions handle Resignation/Dismissal/Death/Retirement as
free-text/date fields already; this table is descriptive HR policy
(when each termination type applies), not a data-model requirement beyond
what core Employee already captures. No Egypt-specific gap — nothing in
this table names a field or calculation the codebase lacks.

### Employee Final Settlement Screen (doc lines 747-758)

✅ **Generically covered** by ERPNext/HRMS core's `Full and Final
Statement` doctype (`hrms/hr/doctype/full_and_final_statement/`) — already
generic, needs no Egypt-specific code.

### Annual Leave Balance Settlement / Leave Encashment (doc lines 759-772)

✅ **Implemented exactly.** `Leave Encashment Amount Before Tax = Gross
Salary × 0.75 × (days encashed / 30)`, gated by 3 consecutive years of
service — `hrms/regional/egypt/utils.py:calculate_leave_encashment_amount`,
confirmed word-for-word match against the formula and eligibility
threshold.

### Employee deductions (doc lines 774-787)

❌ **Not implemented** — see Gap #3 below. Absence-day and Late-Hours
deductions ("Based on Gross Wage") are only generically covered by
ERPNext's standard Leave-Without-Pay proration (a per-day rate deduction
for unpaid absence), which is NOT the same as tracking discrete penalty
incidents with a reason category and enforcing the document's specific
caps (5 days/month, 10%/25%/50% escalating deduction-amount caps). No
dedicated Penalty tracking, no cap enforcement anywhere in the codebase.

### Late Policy (doc lines 789-793)

⚠️ **Configuration, not a code gap.** ERPNext/HRMS core's `Shift Type`
doctype already has `late_entry_grace_period` (confirmed present in
`hrms/hr/doctype/shift_type/shift_type.json`) — an admin sets this to 5
minutes on their Shift Type record(s) and the existing auto-attendance
machinery honors it. No new code needed; this is a deployment/setup task
for whoever configures a company's shifts, correctly flagged as
out-of-plan-area in the leave-rules plan's Self-Review Notes ("this is an
Attendance/Shift Type concern, not a Leave Rules concern").

### Required reports (doc lines 795-799)

- ⚠️ **Form 6, Clearance Request** — not implemented; same "no fabricated
  government-form content" reasoning as Form 1 (Section 1 above). Not
  previously flagged in the required-reports plan since that plan's scope
  was Area 1's report list specifically; noted here as belonging to the
  same category of deliberately-unbuilt government forms.
- ⚠️ **Statistics of resignations by dates, reasons, and departments** —
  the existing `Employee Exits` report (`hrms/hr/report/employee_exits/`,
  ERPNext/HRMS core, pre-dates the Egypt work) provides a raw per-employee
  listing with a chart and summary, not an aggregated breakdown by reason
  and department specifically. Partial coverage, not a clean match to
  the document's ask. Candidate follow-up, not included in the gap-closure
  spec (reporting gap, not a payroll-calculation gap — see that spec's
  §2 "What This Spec Does NOT Cover").

---

## Section 5 — Fixed Parameters / Special Funds Calculation Screens (doc lines 801-823)

### Fixed Parameters Entry Screen (doc lines 801-810)

✅ **Fully covered** by `Egypt Statutory Settings` — a dated,
company-scoped record holding exactly the parameters this "screen"
describes: Minimum Gross Wage (via `min_basic_wage`/`max_basic_wage`
bounds — the document doesn't separately define a distinct "gross wage"
floor beyond basic/insurance wage bounds), Basic Salary min/max,
Insurance Salary min/max, and (via the seeded `Income Tax Slab` records)
Income Tax Brackets. This "screen" in the source document maps to the
`Egypt Statutory Settings` doctype's Desk form — no separate
implementation needed, it already IS this screen.

### Special Funds Calculation Screen (doc lines 812-823)

✅ **Fully covered** by the `Egypt Statutory Fund` doctype and its
`compute()` method — this table's exact three funds (Emergency Assistance
Fund, Cultural Services Fund, Training and Qualification Fund) with their
exact headcount thresholds (30/20/30), values (1%/—/0.25%), and min/max
bounds (—/8-16/10-30 EGP) are all confirmed present and correctly wired
in `hrms/payroll/doctype/egypt_statutory_fund/egypt_statutory_fund.py`.
(Martyrs' Families Fund, the 4th fund tracked by this doctype, isn't in
this specific table but IS in the earlier fund-definitions section — see
Section 3 above; this "Special Funds Calculation Screen" table is a
subset view, not the complete fund list.)

---

## Summary: Genuine Gaps Requiring New Code

These three items need new fields/doctypes/logic — a seed script alone
cannot close them. Covered by
`docs/superpowers/specs/2026-08-15-egypt-payroll-gap-closure-design.md`:

1. **Annual Bonus** (doc lines 251-264) — 3% of insurance wage, min 250
   EGP, 1-year tenure gate. No field, no Salary Component, no eligibility
   logic exists anywhere.
2. **Loan Cap** (doc lines 266-275) — interest-free requirement, 10%
   monthly-installment-of-salary cap. No validation exists on `Loan`
   beyond the existing (unrelated) currency-match check.
3. **Deduction Caps / Penalties** (doc lines 774-787) — 5-days/month cap,
   10%/25%/50% escalating amount caps by reason. No dedicated tracking
   doctype, no cap enforcement anywhere; only generic LWP proration exists.

## Summary: Fixed This Session (already committed, outside the gap-closure spec)

- **Income tax bracket thresholds** corrected to match the document's
  highest-tier schedule (25% now 400K-1,200K, 27% starts at 1,200K, was
  previously incorrectly 600K) — `hrms/regional/egypt/setup.py`.
  **Important operational note:** this fix only affects *new* installs.
  `make_income_tax_slabs()` is idempotent (skips creation if the slab
  already exists by name), so any site that already ran `setup()` before
  this fix keeps the old, wrong bracket values silently. A standalone
  correction script, `hrms/regional/egypt/fix_income_tax_slab_brackets.py`,
  is provided to update an already-seeded slab in place — run via
  `bench --site <site> execute hrms.regional.egypt.fix_income_tax_slab_brackets.execute`.
  Handles the submittable-doctype cancel/edit/resubmit cycle correctly
  (`Income Tax Slab` is `is_submittable: 1`) and is itself idempotent.

## Summary: Confirmed Out of Scope on Purpose (not gaps, not touched)

- Form 1 / Form 6 (fabrication risk, need real government-form content)
- Disability/age-based Regular Leave accrual tier (needs an
  Employee-attribute override on top of tenure-tiers, explicitly deferred
  by the leave-rules plan)
- Sick Leave tiered 90/85/75% payout decay (needs new payroll-engine
  day-tracking machinery, explicitly deferred by the leave-rules plan)
- Late Policy grace period (already achievable via existing `Shift Type`
  configuration, zero code needed)
- Gratuity Rule slab values (never sourced from this document at all —
  nothing to reconcile)
- Resignation-statistics aggregate report, Martyrs' Fund rate
  configurability, employer-side social-insurance GL posting (all
  candidate follow-ups noted but not scoped into any current plan)
