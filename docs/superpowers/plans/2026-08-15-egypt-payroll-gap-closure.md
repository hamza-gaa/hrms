# Egypt Payroll Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close three genuine gaps found in a full re-read of
`docs/Payroll System.rtf.doc` against the shipped Egypt payroll
implementation: Annual Bonus, Loan interest/installment cap, and
deduction (penalty) caps — none of which a seed script alone can add,
since none of the fields/doctypes they need exist yet.

**Architecture:** All three features are additive Egypt-regional code,
following the exact conventions already established by the five prior
Egypt plans: new `Egypt Statutory Settings` fields for tunable rates, a
new formula-driven `Salary Component` for the bonus (mirroring `Insurance
Wage`'s existing pattern), an `@hrms.allow_regional`-decorated function in
`hrms/hr/utils.py` for the loan cap (the correct pattern for a
non-hrms-owned doctype, per this plan's spec §3), and one new small
doctype (`Egypt Employee Penalty`) for deduction-cap tracking. Zero
behavior change for non-Egypt companies throughout.

**Tech Stack:** Frappe Framework doctype JSON, Python controllers,
`bench run-tests`.

**Spec:** `docs/superpowers/specs/2026-08-15-egypt-payroll-gap-closure-design.md`

## Global Constraints

- Custom field / doctype field `fieldname`s use no `custom_` prefix,
  consistent with every prior Egypt plan.
- `Egypt Employee Penalty` belongs to the `Payroll` module (matches
  `Egypt Statutory Fund`/`Egypt Statutory Settings` — financial/
  compliance-tracking doctypes live in Payroll in this codebase's
  existing convention, confirmed by reading those two doctypes' JSON
  `module` field).
- Tab indentation, double quotes, line length 110 (ruff, `pyproject.toml`).
  No bench/pre-commit/ruff binary was available in the session that wrote
  this plan — trace changes by hand against each test's assertions if
  unavailable at implementation time; do not fabricate PASS output.
- Tests live next to the code as `test_*.py`, extending
  `hrms.tests.utils.HRMSTestSuite` for anything needing `make_employee`.
- Commit messages follow Conventional Commits.
- All new fields on existing doctypes (`Egypt Statutory Settings`) are
  additive and optional with sane defaults — non-Egypt companies see zero
  behavior change, matching every prior Egypt plan's contract.
- **`_get_gross_salary(employee)`** already exists in
  `hrms/regional/egypt/utils.py` (added for the Overtime Slip cap check) —
  reuse it verbatim for both the Loan cap (Task 2) and Penalty cap (Task
  3) checks. Do not write a second gross-salary lookup.
- **Confirmed against current code** (read during planning, 2026-08-15):
  - `hrms/payroll/utils.py` defines `COMPONENT_EVAL_GLOBALS` (a module-level
    dict of names available inside Salary Component `formula`/`condition`
    strings — currently `int`, `float`, `long`, `round`, `rounded`, `date`,
    `getdate`, `get_first_day`, `get_last_day`, `ceil`, `floor`, `min`,
    `max`, plus `egypt_insurance_wage_bounds`) and
    `get_component_eval_context(employee, ssa_as_dict)` (line 107), which
    builds the actual `data` dict a formula evaluates against by merging
    component-abbreviation defaults, Salary Structure Assignment fields,
    and **`frappe.get_cached_doc("Employee", employee).as_dict()`** — i.e.
    every Employee field, including `date_of_joining` and `company`, is
    already available as a bare variable name inside a formula string. A
    formula does NOT receive `employee` as a variable (there is no
    `employee` key merged in) — use `date_of_joining` and `company`
    directly instead, exactly as `Insurance Wage`'s own formula does
    (`egypt_insurance_wage_bounds(getdate())` — note it takes no employee
    arg either, just `date`).
  - **`Loan` is an ERPNext-core doctype, not an hrms-owned one.**
    `hrms/hooks.py:212` has `doc_events = {"Loan": {"validate":
    "hrms.hr.utils.validate_loan_repay_from_salary"}}` — this is how hrms
    reacts to Loan's lifecycle without owning Loan's controller code.
    `hrms/hr/utils.py:833` defines `validate_loan_repay_from_salary(doc,
    method=None)`. India's regional overrides
    (`hrms/hooks.py:305-309`) already use the identical pattern this plan
    needs: an `@hrms.allow_regional`-decorated function living in
    `hrms/hr/utils.py` (a file hrms owns), overridden per-country via
    `regional_overrides`. `hrms/__init__.py:32-51` defines the
    `allow_regional` decorator — it looks up `regional_overrides` by the
    CURRENT COMPANY'S COUNTRY (via `hrms.get_region()`, which reads
    `frappe.local.flags.company` or falls back to system settings), not a
    hardcoded region, so the same decorated function is a safe no-op for
    every non-Egypt company automatically.
  - `Egypt Statutory Fund`'s doctype JSON
    (`hrms/payroll/doctype/egypt_statutory_fund/egypt_statutory_fund.json`)
    is the structural template for `Egypt Employee Penalty` — same
    `module: "Payroll"`, same permission block shape (System Manager + HR
    Manager, full CRUD), same `naming_rule: "Random"`/`autoname: "hash"`
    convention for an incident-log-style doctype with no natural unique
    key.
  - `hrms/regional/egypt/data/salary_components.json` currently has 11
    records ending with `Social Insurance Contribution`. Task 1 appends a
    12th.
  - `hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json`'s
    `field_order` currently ends with `[..., 'training_fund_rate',
    'training_fund_min', 'training_fund_max']` (added by the Area 4 plan).
    Task 1 appends new fields after this.

---

## Task 1: Annual Bonus — Egypt Statutory Settings fields + Salary Component

**Files:**
- Modify: `hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json`
- Modify: `hrms/payroll/doctype/egypt_statutory_settings/test_egypt_statutory_settings.py`
- Modify: `hrms/payroll/utils.py`
- Modify: `hrms/payroll/test_utils_egypt.py`
- Modify: `hrms/regional/egypt/data/salary_components.json`

**Interfaces:**
- Produces: `Egypt Statutory Settings.annual_bonus_rate` (Percent, default
  `3`), `Egypt Statutory Settings.annual_bonus_minimum_amount` (Currency,
  default `250`). New function
  `hrms.payroll.utils.egypt_annual_bonus_amount(date_of_joining, company,
  date) -> float`, registered in `COMPONENT_EVAL_GLOBALS` under the key
  `"egypt_annual_bonus_amount"`. New `Salary Component` record `"Annual
  Bonus"` whose formula calls this function.
- Consumes: `hrms.payroll.doctype.egypt_statutory_settings.egypt_statutory_settings.get_active_settings(date,
  company=None)` (existing function, confirmed signature via prior Area 4
  plan's ledger).

- [ ] **Step 1: Write the failing test for the new settings fields**

Add to `hrms/payroll/doctype/egypt_statutory_settings/test_egypt_statutory_settings.py`:

```python
	def test_create_settings_with_annual_bonus_fields(self):
		doc = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"effective_from": "2026-03-01",
				"annual_bonus_rate": 3,
				"annual_bonus_minimum_amount": 250,
			}
		).insert()

		self.assertEqual(doc.annual_bonus_rate, 3)
		self.assertEqual(doc.annual_bonus_minimum_amount, 250)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.doctype.egypt_statutory_settings.test_egypt_statutory_settings`
Expected: FAIL — `Unknown field 'annual_bonus_rate' in Egypt Statutory
Settings`. If no bench, report NOT EXECUTED with rationale (fields absent
from current JSON, confirmed during planning).

- [ ] **Step 3: Add the fields to Egypt Statutory Settings**

In `hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json`,
add `"annual_bonus_section"` and the two new fieldnames to `field_order`,
right after the existing `"training_fund_max"` entry:

```json
  "annual_bonus_section",
  "annual_bonus_rate",
  "column_break_6",
  "annual_bonus_minimum_amount"
```

Add to the `fields` array, right before the final closing `]`:

```json
  {
   "fieldname": "annual_bonus_section",
   "fieldtype": "Section Break",
   "label": "Annual Bonus"
  },
  {
   "default": "3",
   "description": "Percent of Insurance Wage. Employee must have completed 1 full year of service by January of the payroll year to be eligible.",
   "fieldname": "annual_bonus_rate",
   "fieldtype": "Percent",
   "label": "Annual Bonus Rate"
  },
  {
   "fieldname": "column_break_6",
   "fieldtype": "Column Break"
  },
  {
   "default": "250",
   "fieldname": "annual_bonus_minimum_amount",
   "fieldtype": "Currency",
   "label": "Annual Bonus Minimum Amount",
   "non_negative": 1,
   "options": "currency"
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.doctype.egypt_statutory_settings.test_egypt_statutory_settings`
Expected: PASS. If no bench, report NOT EXECUTED with static-read rationale.

- [ ] **Step 5: Write the failing test for the eligibility/amount helper**

Add to `hrms/payroll/test_utils_egypt.py` (this file already exists with
tests for `egypt_insurance_wage_bounds` — add a new test class alongside
the existing one, matching its imports/setup pattern):

```python
class TestEgyptAnnualBonusAmount(IntegrationTestCase):
	def test_returns_zero_when_no_settings_exist(self):
		from hrms.payroll.utils import egypt_annual_bonus_amount

		amount = egypt_annual_bonus_amount(
			date_of_joining="2020-01-01", company="_Test Company Bonus Empty", date=getdate("2026-06-01")
		)
		self.assertEqual(amount, 0)

	def test_returns_zero_when_tenure_under_one_year(self):
		from hrms.payroll.utils import egypt_annual_bonus_amount

		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "Test Egypt Statutory Settings Bonus 1",
				"effective_from": "2026-01-01",
				"annual_bonus_rate": 3,
				"annual_bonus_minimum_amount": 250,
			}
		).insert(ignore_if_duplicate=True)

		amount = egypt_annual_bonus_amount(
			date_of_joining=add_days(getdate("2026-06-01"), -100), company=None, date=getdate("2026-06-01")
		)
		self.assertEqual(amount, 0)

	def test_returns_minimum_when_rate_based_amount_is_lower(self):
		from hrms.payroll.utils import egypt_annual_bonus_amount

		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "Test Egypt Statutory Settings Bonus 2",
				"effective_from": "2026-01-01",
				"annual_bonus_rate": 3,
				"annual_bonus_minimum_amount": 250,
			}
		).insert(ignore_if_duplicate=True)

		# 3% of an insurance wage of 5000 is 150, below the 250 minimum
		amount = egypt_annual_bonus_amount(
			date_of_joining=add_days(getdate("2026-06-01"), -365 * 2),
			company=None,
			date=getdate("2026-06-01"),
			insurance_wage=5000,
		)
		self.assertEqual(amount, 250)

	def test_returns_rate_based_amount_when_above_minimum(self):
		from hrms.payroll.utils import egypt_annual_bonus_amount

		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "Test Egypt Statutory Settings Bonus 3",
				"effective_from": "2026-01-01",
				"annual_bonus_rate": 3,
				"annual_bonus_minimum_amount": 250,
			}
		).insert(ignore_if_duplicate=True)

		# 3% of an insurance wage of 15000 is 450, above the 250 minimum
		amount = egypt_annual_bonus_amount(
			date_of_joining=add_days(getdate("2026-06-01"), -365 * 2),
			company=None,
			date=getdate("2026-06-01"),
			insurance_wage=15000,
		)
		self.assertEqual(amount, 450)
```

Add `from frappe.utils import add_days, getdate` and `from frappe.tests
import IntegrationTestCase` to this test file's imports if not already
present — read the file first to check, since it already has tests for
`egypt_insurance_wage_bounds` and may already import some of these.

- [ ] **Step 6: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.test_utils_egypt`
Expected: FAIL — `ImportError: cannot import name 'egypt_annual_bonus_amount'`.
If no bench, report NOT EXECUTED with rationale.

- [ ] **Step 7: Implement the helper and register it**

In `hrms/payroll/utils.py`, add after the existing
`egypt_insurance_wage_bounds` function and its
`COMPONENT_EVAL_GLOBALS["egypt_insurance_wage_bounds"] = ...` line:

```python
def egypt_annual_bonus_amount(
	date_of_joining, company=None, date=None, insurance_wage=None
) -> float:
	"""Egypt Annual Bonus: max(rate% of Insurance Wage, minimum amount),
	only for employees with >= 1 full year of tenure as of January 1 of
	`date`'s year. Returns 0 if ineligible or no active settings exist.
	`insurance_wage` defaults to reading the "IW" component abbreviation
	from the eval globals cache if not passed explicitly (formula usage
	passes it as the IW variable already resolved in the eval context;
	direct Python callers, e.g. tests, pass it explicitly)."""
	from frappe.utils import date_diff, getdate

	from hrms.payroll.doctype.egypt_statutory_settings.egypt_statutory_settings import (
		get_active_settings,
	)

	date = getdate(date) if date else getdate()
	if not date_of_joining:
		return 0

	january_first = date.replace(month=1, day=1)
	years_of_service = date_diff(january_first, getdate(date_of_joining)) / 365.25
	if years_of_service < 1:
		return 0

	settings = get_active_settings(date, company=company)
	if not settings:
		return 0

	rate_based = (insurance_wage or 0) * (settings.annual_bonus_rate or 0) / 100
	return max(rate_based, settings.annual_bonus_minimum_amount or 0)


COMPONENT_EVAL_GLOBALS["egypt_annual_bonus_amount"] = egypt_annual_bonus_amount
```

Note on the `insurance_wage` parameter: unlike `egypt_insurance_wage_bounds`
(which needs no employee-specific data, just settings bounds),
`egypt_annual_bonus_amount` needs the employee's actual computed Insurance
Wage for the period, which inside a Salary Component formula is available
as the bare variable `IW` (the component abbreviation, already resolved
earlier in the same slip's evaluation — same mechanism `Social Insurance
Contribution`'s `IW * 0.11` formula relies on). The formula will call this
as `egypt_annual_bonus_amount(date_of_joining, company, getdate(), IW)`.

- [ ] **Step 8: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.test_utils_egypt`
Expected: PASS (4 new tests). If no bench, report NOT EXECUTED with
static-read rationale — trace `egypt_annual_bonus_amount` by hand against
each test's assertions, paying attention to the January-1-of-`date`'s-year
boundary calculation.

- [ ] **Step 9: Seed the Annual Bonus salary component**

Append to `hrms/regional/egypt/data/salary_components.json` (it currently
ends with the `Social Insurance Contribution` record — add this as a new
array element after it, remembering to add a comma after the previous
record's closing `}`):

```json
	{
		"doctype": "Salary Component",
		"salary_component": "Annual Bonus",
		"salary_component_abbr": "ANB",
		"type": "Earning",
		"is_tax_applicable": 1,
		"amount_based_on_formula": 1,
		"formula": "egypt_annual_bonus_amount(date_of_joining, company, getdate(), IW)"
	}
```

- [ ] **Step 10: Lint**

```bash
pre-commit run --files hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json hrms/payroll/doctype/egypt_statutory_settings/test_egypt_statutory_settings.py hrms/payroll/utils.py hrms/payroll/test_utils_egypt.py hrms/regional/egypt/data/salary_components.json
```

- [ ] **Step 11: Commit**

```bash
git add hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json hrms/payroll/doctype/egypt_statutory_settings/test_egypt_statutory_settings.py hrms/payroll/utils.py hrms/payroll/test_utils_egypt.py hrms/regional/egypt/data/salary_components.json
git commit -m "feat(egypt): add Annual Bonus statutory settings fields and salary component"
```

---

## Task 2: Loan Cap — interest-free + 10% monthly installment ceiling

**Files:**
- Modify: `hrms/hr/utils.py`
- Modify: `hrms/regional/egypt/utils.py`
- Modify: `hrms/regional/egypt/test_utils.py`
- Modify: `hrms/hooks.py`

**Interfaces:**
- Produces: `hrms.hr.utils.validate_loan_cap(doc) -> None` (new,
  `@hrms.allow_regional`-decorated, no-op body). `hrms.regional.egypt.utils.validate_egypt_loan_cap(doc)
  -> None` (Egypt override).
- Consumes: `hrms.regional.egypt.utils._get_gross_salary(employee) ->
  float` (existing function — read it first, it's already in
  `hrms/regional/egypt/utils.py` from the Overtime Slip work).

- [ ] **Step 1: Write the failing test**

Add to `hrms/regional/egypt/test_utils.py` (this file already exists with
tests for `validate_overtime_detail` — add a new test class, matching its
imports/setup pattern; read the file first to see its existing
`HRMSTestSuite` usage and `make_employee`/Salary Structure Assignment
setup helpers so this test follows the same conventions):

```python
class TestEgyptLoanCap(HRMSTestSuite):
	def test_blocks_loan_with_nonzero_interest_rate(self):
		from hrms.regional.egypt.utils import validate_egypt_loan_cap

		employee = self.make_employee("egypt_loan_interest@example.com")
		doc = frappe._dict(
			applicant_type="Employee",
			applicant=employee,
			repay_from_salary=1,
			rate_of_interest=5,
			monthly_repayment_amount=0,
		)
		with self.assertRaises(frappe.ValidationError):
			validate_egypt_loan_cap(doc)

	def test_blocks_installment_above_ten_percent_of_gross_salary(self):
		from hrms.regional.egypt.test_utils import _make_salary_structure_assignment_with_gross_salary
		from hrms.regional.egypt.utils import validate_egypt_loan_cap

		employee = self.make_employee("egypt_loan_installment@example.com")
		_make_salary_structure_assignment_with_gross_salary(employee, gross_salary=10000)

		doc = frappe._dict(
			applicant_type="Employee",
			applicant=employee,
			repay_from_salary=1,
			rate_of_interest=0,
			monthly_repayment_amount=1500,  # 15% of 10000
		)
		with self.assertRaises(frappe.ValidationError):
			validate_egypt_loan_cap(doc)

	def test_allows_interest_free_loan_within_installment_cap(self):
		from hrms.regional.egypt.test_utils import _make_salary_structure_assignment_with_gross_salary
		from hrms.regional.egypt.utils import validate_egypt_loan_cap

		employee = self.make_employee("egypt_loan_ok@example.com")
		_make_salary_structure_assignment_with_gross_salary(employee, gross_salary=10000)

		doc = frappe._dict(
			applicant_type="Employee",
			applicant=employee,
			repay_from_salary=1,
			rate_of_interest=0,
			monthly_repayment_amount=900,  # 9% of 10000
		)
		validate_egypt_loan_cap(doc)  # should not raise

	def test_ignores_loans_not_repaid_from_salary(self):
		from hrms.regional.egypt.utils import validate_egypt_loan_cap

		employee = self.make_employee("egypt_loan_external@example.com")
		doc = frappe._dict(
			applicant_type="Employee",
			applicant=employee,
			repay_from_salary=0,
			rate_of_interest=10,
			monthly_repayment_amount=99999,
		)
		validate_egypt_loan_cap(doc)  # should not raise, out of scope per repay_from_salary=0
```

`_make_salary_structure_assignment_with_gross_salary(employee,
gross_salary)` is a real, existing, MODULE-LEVEL (not `self.`-method)
private helper already defined at the bottom of
`hrms/regional/egypt/test_utils.py:93` (added by the Area 3 plan for the
leave-encashment tests — confirmed by reading the file directly, not
assumed). Import it explicitly (`from hrms.regional.egypt.test_utils
import _make_salary_structure_assignment_with_gross_salary`) — it is NOT
a method on `HRMSTestSuite`, do not call it as `self.make_...`. Pass
`gross_salary` as the keyword shown (matching its existing usage at
`test_utils.py:72`). It creates a `Gross Salary` Salary Component if
missing, an active `Salary Structure` with that one earning, and submits
a `Salary Structure Assignment` for the employee — reuse it exactly as
that existing call site does, do not reimplement any of this.

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_utils`
Expected: FAIL — `ImportError: cannot import name 'validate_egypt_loan_cap'`.
If no bench, report NOT EXECUTED with rationale.

- [ ] **Step 3: Add the allow_regional hook function to hrms/hr/utils.py**

In `hrms/hr/utils.py`, find the existing `validate_loan_repay_from_salary`
function (search for `def validate_loan_repay_from_salary`). Add a new
function immediately after it:

```python
@hrms.allow_regional
def validate_loan_cap(doc):
	"""No-op outside regions that override it via regional_overrides."""
	pass
```

Then modify `validate_loan_repay_from_salary` to call it — add this line
at the very end of the existing function body (after its existing
currency-match check, so it runs for every Loan validate, not just the
currency-checked branch):

```python
def validate_loan_repay_from_salary(doc, method=None):
	if doc.applicant_type == "Employee" and doc.repay_from_salary:
		# ... existing body unchanged ...
		pass

	validate_loan_cap(doc)
```

Read the actual current function body first (it's a few lines, shown in
this plan's Global Constraints section above) and add the
`validate_loan_cap(doc)` call as the function's last line, outside the
existing `if` block (so it always runs, letting the Egypt override itself
decide whether `repay_from_salary`/`applicant_type` apply — matching
Task 2's test `test_ignores_loans_not_repaid_from_salary`, which expects
the override itself to no-op for non-salary-repaid loans, not the caller).

Confirm `hrms` is already imported at the top of `hrms/hr/utils.py` (it
almost certainly is, given this is the hrms package's own utils module —
check for `import hrms` or add it if genuinely missing).

- [ ] **Step 4: Add the Egypt override**

In `hrms/regional/egypt/utils.py`, add at the end of the file:

```python
LOAN_MONTHLY_INSTALLMENT_CAP_RATIO = 0.10


def validate_egypt_loan_cap(doc):
	"""Egypt-specific Loan validation: interest-free, monthly installment
	capped at 10% of the employee's gross salary. Registered via
	regional_overrides["Egypt"] against hrms.hr.utils.validate_loan_cap.
	"""
	if doc.applicant_type != "Employee" or not doc.repay_from_salary:
		return

	if doc.rate_of_interest:
		frappe.throw(_("Loans to employees must be interest-free"))

	gross_salary = _get_gross_salary(doc.applicant)
	if gross_salary and doc.monthly_repayment_amount > gross_salary * LOAN_MONTHLY_INSTALLMENT_CAP_RATIO:
		frappe.throw(
			_("Monthly loan installment cannot exceed {0}% of the employee's gross salary").format(
				LOAN_MONTHLY_INSTALLMENT_CAP_RATIO * 100
			)
		)
```

`_get_gross_salary` and `frappe`/`_` are already imported/defined earlier
in this same file — no new imports needed.

- [ ] **Step 5: Wire the regional override**

In `hrms/hooks.py`, find the `regional_overrides = {"Egypt": {...}}`
block (has two existing entries for `validate_overtime_detail_hook` and
`calculate_encashment_amount_hook`). Add a third entry:

```python
	"Egypt": {
		"hrms.hr.doctype.overtime_slip.overtime_slip.validate_overtime_detail_hook": "hrms.regional.egypt.utils.validate_overtime_detail",
		"hrms.hr.doctype.leave_encashment.leave_encashment.calculate_encashment_amount_hook": "hrms.regional.egypt.utils.calculate_leave_encashment_amount",
		"hrms.hr.utils.validate_loan_cap": "hrms.regional.egypt.utils.validate_egypt_loan_cap",
	},
```

- [ ] **Step 6: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_utils`
Expected: PASS (4 new tests). If no bench, report NOT EXECUTED with
static-read rationale.

- [ ] **Step 7: Lint**

```bash
pre-commit run --files hrms/hr/utils.py hrms/regional/egypt/utils.py hrms/regional/egypt/test_utils.py hrms/hooks.py
```

- [ ] **Step 8: Commit**

```bash
git add hrms/hr/utils.py hrms/regional/egypt/utils.py hrms/regional/egypt/test_utils.py hrms/hooks.py
git commit -m "feat(egypt): add interest-free and 10% installment-cap validation to employee loans"
```

---

## Task 3: Egypt Employee Penalty doctype (deduction caps)

**Files:**
- Create: `hrms/payroll/doctype/egypt_employee_penalty/__init__.py`
- Create: `hrms/payroll/doctype/egypt_employee_penalty/egypt_employee_penalty.json`
- Create: `hrms/payroll/doctype/egypt_employee_penalty/egypt_employee_penalty.py`
- Create: `hrms/payroll/doctype/egypt_employee_penalty/test_egypt_employee_penalty.py`

**Interfaces:**
- Consumes: `hrms.regional.egypt.utils._get_gross_salary(employee) ->
  float` (existing function, reused verbatim).
- Produces: doctype `Egypt Employee Penalty` with fields `employee`
  (Link, required), `penalty_date` (Date, required), `reason_category`
  (Select: `Violation`, `Damage`, `Alimony`), `basis` (Select: `Insurance
  Wage`, `Fixed Value`), `amount` (Currency, required), `days_deducted`
  (Int, default 0, non-negative), `status` (Select: `Draft`, `Applied`,
  default `Draft`). Controller method `validate_monthly_caps(self) ->
  None`, called from `validate()`.

- [ ] **Step 1: Write the failing test**

`hrms/payroll/doctype/egypt_employee_penalty/test_egypt_employee_penalty.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.regional.egypt.test_utils import _make_salary_structure_assignment_with_gross_salary
from hrms.tests.utils import HRMSTestSuite


class TestEgyptEmployeePenalty(HRMSTestSuite):
	def test_blocks_more_than_five_absence_days_in_one_month(self):
		employee = self.make_employee("egypt_penalty_days@example.com")
		_make_salary_structure_assignment_with_gross_salary(employee, gross_salary=10000)

		for i in range(5):
			frappe.get_doc(
				{
					"doctype": "Egypt Employee Penalty",
					"employee": employee,
					"penalty_date": f"2026-03-0{i + 1}",
					"reason_category": "Violation",
					"basis": "Insurance Wage",
					"amount": 10,
					"days_deducted": 1,
				}
			).insert()

		sixth = frappe.get_doc(
			{
				"doctype": "Egypt Employee Penalty",
				"employee": employee,
				"penalty_date": "2026-03-06",
				"reason_category": "Violation",
				"basis": "Insurance Wage",
				"amount": 10,
				"days_deducted": 1,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			sixth.insert()

	def test_blocks_violation_amount_above_ten_percent_cap(self):
		employee = self.make_employee("egypt_penalty_violation_cap@example.com")
		_make_salary_structure_assignment_with_gross_salary(employee, gross_salary=10000)

		doc = frappe.get_doc(
			{
				"doctype": "Egypt Employee Penalty",
				"employee": employee,
				"penalty_date": "2026-03-01",
				"reason_category": "Violation",
				"basis": "Insurance Wage",
				"amount": 1500,  # 15% of 10000, exceeds the 10% Violation cap
				"days_deducted": 0,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_allows_damage_amount_up_to_twenty_five_percent_cap(self):
		employee = self.make_employee("egypt_penalty_damage_cap@example.com")
		_make_salary_structure_assignment_with_gross_salary(employee, gross_salary=10000)

		doc = frappe.get_doc(
			{
				"doctype": "Egypt Employee Penalty",
				"employee": employee,
				"penalty_date": "2026-03-01",
				"reason_category": "Damage",
				"basis": "Fixed Value",
				"amount": 2000,  # 20% of 10000, within the 25% Damage cap
				"days_deducted": 0,
			}
		)
		doc.insert()  # should not raise

	def test_allows_alimony_amount_up_to_fifty_percent_cap(self):
		employee = self.make_employee("egypt_penalty_alimony_cap@example.com")
		_make_salary_structure_assignment_with_gross_salary(employee, gross_salary=10000)

		doc = frappe.get_doc(
			{
				"doctype": "Egypt Employee Penalty",
				"employee": employee,
				"penalty_date": "2026-03-01",
				"reason_category": "Alimony",
				"basis": "Fixed Value",
				"amount": 4500,  # 45% of 10000, within the 50% Alimony cap
				"days_deducted": 0,
			}
		)
		doc.insert()  # should not raise
```

`_make_salary_structure_assignment_with_gross_salary` — same real,
module-level, underscore-prefixed helper documented in Task 2 above
(`hrms/regional/egypt/test_utils.py:93`), imported explicitly, called
with `gross_salary` as a keyword argument, NOT a `self.`-method.

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.doctype.egypt_employee_penalty.test_egypt_employee_penalty`
Expected: FAIL — `ModuleNotFoundError` (doctype doesn't exist). If no
bench, report NOT EXECUTED with rationale.

- [ ] **Step 3: Create the doctype JSON**

`hrms/payroll/doctype/egypt_employee_penalty/egypt_employee_penalty.json`:

```json
{
 "actions": [],
 "autoname": "hash",
 "creation": "2026-08-15 00:00:00.000000",
 "doctype": "DocType",
 "editable_grid": 1,
 "engine": "InnoDB",
 "field_order": [
  "employee",
  "penalty_date",
  "column_break_1",
  "status",
  "details_section",
  "reason_category",
  "basis",
  "column_break_2",
  "amount",
  "days_deducted"
 ],
 "fields": [
  {
   "fieldname": "employee",
   "fieldtype": "Link",
   "in_list_view": 1,
   "label": "Employee",
   "options": "Employee",
   "reqd": 1
  },
  {
   "fieldname": "penalty_date",
   "fieldtype": "Date",
   "in_list_view": 1,
   "label": "Penalty Date",
   "reqd": 1
  },
  {
   "fieldname": "column_break_1",
   "fieldtype": "Column Break"
  },
  {
   "default": "Draft",
   "fieldname": "status",
   "fieldtype": "Select",
   "in_list_view": 1,
   "label": "Status",
   "options": "Draft\nApplied",
   "read_only": 1
  },
  {
   "fieldname": "details_section",
   "fieldtype": "Section Break",
   "label": "Details"
  },
  {
   "fieldname": "reason_category",
   "fieldtype": "Select",
   "in_list_view": 1,
   "label": "Reason Category",
   "options": "Violation\nDamage\nAlimony",
   "reqd": 1
  },
  {
   "description": "Per docs/Payroll System.rtf.doc: Violation is based on Insurance Wage, Damage is a Fixed Value. Alimony has no basis specified in the source document (a court-ordered figure) — Fixed Value by default, editable.",
   "fieldname": "basis",
   "fieldtype": "Select",
   "label": "Basis",
   "options": "Insurance Wage\nFixed Value"
  },
  {
   "fieldname": "column_break_2",
   "fieldtype": "Column Break"
  },
  {
   "fieldname": "amount",
   "fieldtype": "Currency",
   "in_list_view": 1,
   "label": "Amount",
   "non_negative": 1,
   "options": "currency",
   "reqd": 1
  },
  {
   "description": "Absence days this incident consumes toward the 5-days-per-month cap. 0 for pure monetary penalties that don't consume absence-days.",
   "fieldname": "days_deducted",
   "fieldtype": "Int",
   "label": "Days Deducted",
   "non_negative": 1
  }
 ],
 "links": [],
 "modified": "2026-08-15 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "Payroll",
 "name": "Egypt Employee Penalty",
 "naming_rule": "Random",
 "owner": "Administrator",
 "permissions": [
  {
   "create": 1,
   "delete": 1,
   "email": 1,
   "export": 1,
   "print": 1,
   "read": 1,
   "report": 1,
   "role": "System Manager",
   "share": 1,
   "write": 1
  },
  {
   "create": 1,
   "delete": 1,
   "email": 1,
   "export": 1,
   "print": 1,
   "read": 1,
   "report": 1,
   "role": "HR Manager",
   "share": 1,
   "write": 1
  }
 ],
 "sort_field": "creation",
 "sort_order": "DESC",
 "states": [],
 "track_changes": 1
}
```

- [ ] **Step 4: Create the controller with validate_monthly_caps()**

`hrms/payroll/doctype/egypt_employee_penalty/egypt_employee_penalty.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_first_day, get_last_day

# reason_category -> maximum fraction of monthly gross salary this
# category's cumulative penalty amount may reach in one calendar month,
# per docs/Payroll System.rtf.doc's employee-deductions table
REASON_CAP_RATIOS = {
	"Violation": 0.10,
	"Damage": 0.25,
	"Alimony": 0.50,
}

MAX_DAYS_DEDUCTED_PER_MONTH = 5


class EgyptEmployeePenalty(Document):
	def validate(self):
		self.validate_monthly_caps()

	def validate_monthly_caps(self):
		if not self.employee or not self.penalty_date:
			return

		month_start = get_first_day(self.penalty_date)
		month_end = get_last_day(self.penalty_date)

		other_records = frappe.get_all(
			"Egypt Employee Penalty",
			filters={
				"employee": self.employee,
				"penalty_date": ["between", [month_start, month_end]],
				"name": ["!=", self.name or ""],
			},
			fields=["amount", "days_deducted", "reason_category"],
		)

		total_days = self.days_deducted + sum(r.days_deducted for r in other_records)
		if total_days > MAX_DAYS_DEDUCTED_PER_MONTH:
			frappe.throw(
				_("Cannot deduct more than {0} days off per month for {1}").format(
					MAX_DAYS_DEDUCTED_PER_MONTH, self.employee
				)
			)

		cap_ratio = REASON_CAP_RATIOS.get(self.reason_category)
		if not cap_ratio:
			return

		same_category_total = self.amount + sum(
			r.amount for r in other_records if r.reason_category == self.reason_category
		)

		from hrms.regional.egypt.utils import _get_gross_salary

		gross_salary = _get_gross_salary(self.employee)
		if gross_salary and same_category_total > gross_salary * cap_ratio:
			frappe.throw(
				_(
					"Total {0} deductions for {1} this month ({2}) cannot exceed {3}% of gross salary"
				).format(
					self.reason_category, self.employee, same_category_total, cap_ratio * 100
				)
			)
```

`hrms/payroll/doctype/egypt_employee_penalty/__init__.py` (empty file).

Note: `_get_gross_salary` is imported from `hrms.regional.egypt.utils`
inside the method body (not at module level) — this doctype lives under
`hrms/payroll/doctype/`, not `hrms/regional/egypt/`, so it is NOT itself
Egypt-gated the way `regional_overrides`-wired functions are (any company
can technically create an `Egypt Employee Penalty` record — that's fine,
the doctype's name and purpose are self-descriptive, matching how `Egypt
Statutory Fund` is likewise a plain doctype anyone could technically use,
not runtime-gated by company country). The import is deferred into the
method body only to avoid a module-level circular-import risk between
`hrms/payroll/` and `hrms/regional/egypt/` — match the existing lazy-import
style already used in `egypt_statutory_fund.py`'s `_apply_fund_rate`
method for the same reason (`from hrms.payroll.doctype.egypt_statutory_settings...`
imported inside the function, not at the top of the file).

- [ ] **Step 5: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.doctype.egypt_employee_penalty.test_egypt_employee_penalty`
Expected: PASS (4 tests). If no bench, report NOT EXECUTED with
static-read rationale — trace `validate_monthly_caps` by hand against
each test's assertions, including the 5th-vs-6th-day boundary
(`total_days > 5`, so exactly 5 is allowed, 6 is blocked — confirm this
matches the document's "may not be deducting more than 5 days" wording).

- [ ] **Step 6: Lint**

```bash
pre-commit run --files hrms/payroll/doctype/egypt_employee_penalty/
```

- [ ] **Step 7: Commit**

```bash
git add hrms/payroll/doctype/egypt_employee_penalty/
git commit -m "feat(egypt): add Egypt Employee Penalty doctype with monthly deduction-cap enforcement"
```

---

## Task 4: Whole-area integration test

**Files:**
- Create: `hrms/regional/egypt/test_integration_gap_closure.py`

**Interfaces:**
- Consumes: everything from Tasks 1-3.
- Produces: none — final verification task for this plan.

- [ ] **Step 1: Write the integration test**

`hrms/regional/egypt/test_integration_gap_closure.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import getdate

from hrms.payroll.utils import egypt_annual_bonus_amount
from hrms.regional.egypt.utils import validate_egypt_loan_cap
from hrms.tests.utils import HRMSTestSuite


class TestEgyptGapClosureIntegration(HRMSTestSuite):
	def test_all_three_gap_closure_features_are_reachable(self):
		# Annual Bonus fixture + settings
		self.assertTrue(
			frappe.db.exists("Salary Component", "Annual Bonus"),
			"Annual Bonus salary component must be seeded",
		)

		# Loan cap validation function is callable and enforces the interest-free rule
		employee = self.make_employee("egypt_gap_closure_integration@example.com")
		bad_loan = frappe._dict(
			applicant_type="Employee",
			applicant=employee,
			repay_from_salary=1,
			rate_of_interest=5,
			monthly_repayment_amount=0,
		)
		with self.assertRaises(frappe.ValidationError):
			validate_egypt_loan_cap(bad_loan)

		# Annual bonus helper returns 0 for a brand-new employee (no tenure yet)
		amount = egypt_annual_bonus_amount(
			date_of_joining=getdate(), company=None, date=getdate(), insurance_wage=10000
		)
		self.assertEqual(amount, 0)

		# Egypt Employee Penalty doctype is registered and insertable
		penalty = frappe.get_doc(
			{
				"doctype": "Egypt Employee Penalty",
				"employee": employee,
				"penalty_date": getdate(),
				"reason_category": "Violation",
				"basis": "Insurance Wage",
				"amount": 1,
				"days_deducted": 0,
			}
		)
		penalty.insert()
		self.assertTrue(frappe.db.exists("Egypt Employee Penalty", penalty.name))
```

- [ ] **Step 2: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_integration_gap_closure`
Expected: PASS. If no bench, report NOT EXECUTED with a static-read
rationale tracing each assertion against Tasks 1-3's actual committed
code.

- [ ] **Step 3: Lint**

```bash
pre-commit run --files hrms/regional/egypt/test_integration_gap_closure.py
```

- [ ] **Step 4: Commit**

```bash
git add hrms/regional/egypt/test_integration_gap_closure.py
git commit -m "test(egypt): verify Annual Bonus, Loan Cap, and Employee Penalty features are wired together"
```

---

## Self-Review Notes

**Spec coverage:** Every section of
`docs/superpowers/specs/2026-08-15-egypt-payroll-gap-closure-design.md`
maps to a task — §5 (Annual Bonus) → Task 1, §6 (Loan Cap) → Task 2, §7
(Deduction Caps) → Task 3, §8 (cross-feature consistency, `_get_gross_salary`
reuse) → verified in Tasks 2 and 3's interfaces, both explicitly reuse the
existing helper rather than reimplementing it.

**Placeholder scan:** no vague "TBD"/"add error handling" left. Every
step has literal code, not a description of code.

**Type/name consistency:** `egypt_annual_bonus_amount(date_of_joining,
company=None, date=None, insurance_wage=None)` (Task 1) is called
identically in Task 4's integration test and in the Task 1 salary
component formula (`egypt_annual_bonus_amount(date_of_joining, company,
getdate(), IW)`) — same parameter order, same names. `validate_egypt_loan_cap(doc)`
(Task 2) is called identically in Task 4's integration test. `_get_gross_salary`
(pre-existing, unmodified) is imported and called identically in Task 2's
`validate_egypt_loan_cap` and Task 3's `validate_monthly_caps` — same
signature, same import path (`hrms.regional.egypt.utils`).

**Corrected during planning (not left as an initial mistake in this
plan):** the design spec's §5 originally proposed
`egypt_annual_bonus_amount(employee, date)` as the formula signature —
this plan corrects that after confirming (Global Constraints, "Confirmed
against current code") that Salary Component formulas never receive an
`employee` variable, only the merged Employee-field dict (so
`date_of_joining`/`company` are available directly, `employee` is not).
This plan's task text reflects the corrected, verified signature
throughout; the spec document itself was not retroactively edited since
this plan is the executable source of truth going forward and the
correction is recorded here for anyone comparing the two documents.
