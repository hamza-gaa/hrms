# Egypt Salary Structure & Income Tax Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Egypt's statutory payroll parameters, salary component
fixtures, income tax slabs, overtime validation, and end-of-service
leave-encashment formula to the `hrms/regional/egypt/` module, reusing
HRMS's existing generic payroll engines (Salary Component
formula/condition, Income Tax Slab, Overtime Type, Leave Encashment)
rather than building new calculation machinery.

**Architecture:** One new doctype (`Egypt Statutory Settings`, a dated
record following the `Income Tax Slab` `effective_from` pattern) holds
Egypt's tunable numbers (wage bounds, insurance rates, overtime
multipliers). A small whitelisted helper reads it into
`COMPONENT_EVAL_GLOBALS` (`hrms/payroll/utils.py`) so the seeded Insurance
Wage salary component formula can reference it. Salary component and
income tax slab fixtures are seeded via `hrms/regional/egypt/setup.py`
(the same `get_custom_fields()`/fixture-insert pattern Task 2 of the Area
1 plan already established). Overtime validation additions and the
leave-encashment formula are the two genuine Python gaps identified in
spec §6 — both are wired through the existing `regional_overrides` hook
(`hrms/hooks.py`), matching how India overrides
`calculate_annual_eligible_hra_exemption` etc., so non-Egypt companies are
completely unaffected.

**Tech Stack:** Frappe Framework doctype JSON + Python controllers,
`create_custom_fields`/fixture `insert(ignore_if_duplicate=True)`,
`regional_overrides` hook dispatch, `bench run-tests`.

**Spec:** `docs/superpowers/specs/2026-08-13-egypt-payroll-localization-design.md`
(Section 6 — Area 3: Salary Structure & Income Tax)

## Global Constraints

- Custom field `fieldname`s use **no `custom_` prefix**, consistent with
  Area 1 (`hrms/regional/egypt/setup.py` already follows this).
- All new doctypes belong to the `Payroll` module (`hrms/modules.txt`
  declares `HR` and `Payroll`; `Income Tax Slab`, `Gratuity Rule`,
  `Overtime Type` all live under `Payroll` — Egypt Statutory Settings
  follows suit since it's a payroll-parameters doctype, not an
  Employee-attached one).
- Tab indentation, double quotes, line length 110 (ruff,
  `pyproject.toml`). Run `pre-commit run --all-files` before each commit
  (note: no bench/pre-commit binary was available in the session that
  wrote this plan — see Task 0).
- Tests live next to the code as `test_*.py` and extend
  `hrms.tests.utils.HRMSTestSuite` (or `frappe.tests.IntegrationTestCase`
  for simple regional-module tests, matching the pattern in
  `hrms/regional/egypt/test_setup.py` from Area 1).
- Commit messages follow Conventional Commits — e.g. `feat(egypt): ...`,
  `test(egypt): ...`.
- `regional_overrides` entries must be **additive only**: every override
  function must have a base implementation that runs unchanged for all
  non-Egypt companies (matches the existing India entries — see
  `hrms/hooks.py:regional_overrides`).
- **Confirmed against current code** (read during planning, 2026-08-14):
  - `COMPONENT_EVAL_GLOBALS` lives in `hrms/payroll/utils.py:34-46` and is
    copied fresh into the eval context in both
    `hrms/payroll/doctype/salary_slip/salary_slip.py:153` and
    `hrms/payroll/doctype/salary_structure_assignment/salary_structure_assignment.py:375,379`.
    Adding a key to this dict makes it available in every Salary
    Component `condition`/`formula` immediately, for all companies — it
    is a plain function reference, not data, so it is always safe to add
    (unused unless a formula calls it by name).
  - `Income Tax Slab` (`hrms/payroll/doctype/income_tax_slab/income_tax_slab.json`)
    has `effective_from` (Date), `company` (Link, optional),
    `standard_tax_exemption_amount` (Currency), `slabs` (Table →
    `Taxable Salary Slab`), is `is_submittable: 1`.
  - `Taxable Salary Slab` (`hrms/payroll/doctype/taxable_salary_slab/taxable_salary_slab.json`)
    has `from_amount`, `to_amount`, `percent_deduction` (Percent),
    `condition` (Code) — a slab is a marginal bracket, not cumulative
    tax; the calculation engine
    (`income_tax_slab.py:calculate_base_tax_from_tax_slabs`) already
    handles marginal-bracket math, so seeding slabs is pure data, no
    Python needed.
  - `Salary Component` (`hrms/payroll/doctype/salary_component/salary_component.json`)
    has `type` (Select: Earning/Deduction), `condition` (Code),
    `amount_based_on_formula` (Check), `formula` (Code),
    `exempted_from_income_tax` (Check) — all generic, already usable with
    zero new code (confirms spec §2/§6 claim).
  - `Gratuity Rule` / `Gratuity Rule Slab` — confirmed present at
    `hrms/payroll/doctype/gratuity_rule/` and
    `hrms/payroll/doctype/gratuity_rule_slab/`; UAE seeds 3 records with
    zero Python overrides in `hrms/regional/united_arab_emirates/setup.py`
    (read in full — 57 lines, `create_gratuity_rules_for_uae()` pattern
    to copy).
  - `Overtime Type` (`hrms/hr/doctype/overtime_type/overtime_type.json`)
    already has `standard_multiplier`, `weekend_multiplier`,
    `public_holiday_multiplier` (all Float), `maximum_overtime_hours_allowed`
    (Float), `overtime_salary_component` (Link). Egypt's day/night/rest-day
    multipliers (1.35/1.70/2.0) map onto seeded `Overtime Type` records
    directly — no new fields needed there. The genuine gaps are the three
    *validation rules* from spec §6 (30-min threshold, manager-grade
    exemption, >25,000 EGP gross-salary cap), which have **no existing
    check anywhere** in `hrms/hr/doctype/overtime_slip/overtime_slip.py`
    or `overtime_type.py` (confirmed by reading both files in full).
  - `Leave Encashment` (`hrms/hr/doctype/leave_encashment/leave_encashment.py`)
    **already exists** (spec §6 correctly flagged this as needing
    confirmation — confirmed present, not a new doctype). Its
    `set_encashment_amount()` (lines 212-237) computes
    `encashment_days * per_day_encashment` where `per_day_encashment`
    comes from `Salary Structure Assignment.leave_encashment_amount_per_day`
    (a flat Currency field, no formula). Egypt's formula
    (`Gross Salary × 0.75 × days_encashed / 30`, gated on 3 consecutive
    years of service) cannot be expressed via that flat field — this is
    the one real Python gap in Area 3, addressed via a `regional_overrides`
    hook entry (Task 5), not a new doctype.
  - `hrms/hooks.py:regional_overrides` currently has one entry (`"India"`,
    3 functions, all in `hrms.hr.utils`). No `override_doctype_class`
    entry exists for `Leave Encashment` — Task 5 does not add one; it adds
    a `regional_overrides` function entry instead, consistent with the
    existing pattern (`LeaveEncashment.set_encashment_amount` calls a
    thin module-level function that is regional-override-eligible, rather
    than overriding the whole class).

---

## Task 1: `Egypt Statutory Settings` doctype

**Files:**
- Create: `hrms/payroll/doctype/egypt_statutory_settings/__init__.py`
- Create: `hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json`
- Create: `hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.py`
- Create: `hrms/payroll/doctype/egypt_statutory_settings/test_egypt_statutory_settings.py`

**Interfaces:**
- Produces: doctype `Egypt Statutory Settings` with fields
  `effective_from` (Date, required), `company` (Link → Company,
  optional — mirrors `Income Tax Slab.company`), `min_basic_wage` /
  `max_basic_wage` (Currency), `min_insurance_wage` /
  `max_insurance_wage` (Currency), `social_insurance_employee_rate`
  (Percent, default 11), `social_insurance_employer_rate` (Percent,
  default 18.75), `overtime_day_multiplier` (Float, default 1.35),
  `overtime_night_multiplier` (Float, default 1.70),
  `overtime_rest_day_multiplier` (Float, default 2.0). Consumed by Task 2
  (fixture data reads these fields conceptually — no direct code
  dependency), Task 3 (formula helper reads `min_insurance_wage`/
  `max_insurance_wage` via `frappe.get_doc`), and Task 4 (Statutory Fund
  work, out of scope for this plan but documented as the consumer per
  spec §7).
- Function `get_active_settings(date, company=None) -> Document | None` —
  returns the `Egypt Statutory Settings` record with the latest
  `effective_from <= date` (optionally filtered by `company`, falling
  back to the company-less default record if no company-specific one
  exists). Consumed by Task 3.

- [ ] **Step 1: Write the failing test**

`hrms/payroll/doctype/egypt_statutory_settings/test_egypt_statutory_settings.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from hrms.payroll.doctype.egypt_statutory_settings.egypt_statutory_settings import (
	get_active_settings,
)


class TestEgyptStatutorySettings(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_create_and_fetch_active_settings(self):
		doc = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"effective_from": "2026-01-01",
				"min_basic_wage": 2400,
				"max_basic_wage": 12000,
				"min_insurance_wage": 2000,
				"max_insurance_wage": 14500,
				"social_insurance_employee_rate": 11,
				"social_insurance_employer_rate": 18.75,
				"overtime_day_multiplier": 1.35,
				"overtime_night_multiplier": 1.70,
				"overtime_rest_day_multiplier": 2.0,
			}
		).insert()

		active = get_active_settings(getdate("2026-06-01"))
		self.assertEqual(active.name, doc.name)
		self.assertEqual(active.min_insurance_wage, 2000)

	def test_get_active_settings_picks_latest_effective_record(self):
		older = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"effective_from": "2025-01-01",
				"min_insurance_wage": 1500,
				"max_insurance_wage": 12000,
			}
		).insert()
		newer = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"effective_from": "2026-01-01",
				"min_insurance_wage": 2000,
				"max_insurance_wage": 14500,
			}
		).insert()

		active = get_active_settings(getdate("2026-06-01"))
		self.assertEqual(active.name, newer.name)

		active_before_newer = get_active_settings(getdate(add_days("2026-01-01", -1)))
		self.assertEqual(active_before_newer.name, older.name)

	def test_get_active_settings_returns_none_when_no_record(self):
		active = get_active_settings(getdate("1999-01-01"))
		self.assertIsNone(active)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.doctype.egypt_statutory_settings.test_egypt_statutory_settings`
Expected: FAIL — `ModuleNotFoundError` (doctype/module don't exist yet).
If no bench is available in this environment, skip execution and note
"NOT EXECUTED — no bench available" in the task report; do not fabricate
output (see `hrms/regional/egypt` Area 1 precedent in
`.superpowers/sdd/2026-08-13-egypt-employee-master-data/progress.md`).

- [ ] **Step 3: Create the doctype JSON**

`hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json`:

```json
{
 "actions": [],
 "allow_import": 1,
 "autoname": "field:effective_from",
 "creation": "2026-08-14 00:00:00.000000",
 "doctype": "DocType",
 "editable_grid": 1,
 "engine": "InnoDB",
 "field_order": [
  "effective_from",
  "company",
  "column_break_1",
  "disabled",
  "wage_bounds_section",
  "min_basic_wage",
  "max_basic_wage",
  "column_break_2",
  "min_insurance_wage",
  "max_insurance_wage",
  "social_insurance_section",
  "social_insurance_employee_rate",
  "column_break_3",
  "social_insurance_employer_rate",
  "overtime_section",
  "overtime_day_multiplier",
  "overtime_night_multiplier",
  "column_break_4",
  "overtime_rest_day_multiplier"
 ],
 "fields": [
  {
   "fieldname": "effective_from",
   "fieldtype": "Date",
   "in_list_view": 1,
   "label": "Effective From",
   "reqd": 1,
   "unique": 1
  },
  {
   "fieldname": "company",
   "fieldtype": "Link",
   "in_list_view": 1,
   "label": "Company",
   "options": "Company"
  },
  {
   "fieldname": "column_break_1",
   "fieldtype": "Column Break"
  },
  {
   "default": "0",
   "fieldname": "disabled",
   "fieldtype": "Check",
   "label": "Disabled"
  },
  {
   "fieldname": "wage_bounds_section",
   "fieldtype": "Section Break",
   "label": "Wage Bounds"
  },
  {
   "fieldname": "min_basic_wage",
   "fieldtype": "Currency",
   "label": "Min Basic Wage",
   "non_negative": 1,
   "options": "currency"
  },
  {
   "fieldname": "max_basic_wage",
   "fieldtype": "Currency",
   "label": "Max Basic Wage",
   "non_negative": 1,
   "options": "currency"
  },
  {
   "fieldname": "column_break_2",
   "fieldtype": "Column Break"
  },
  {
   "fieldname": "min_insurance_wage",
   "fieldtype": "Currency",
   "label": "Min Insurance Wage",
   "non_negative": 1,
   "options": "currency"
  },
  {
   "fieldname": "max_insurance_wage",
   "fieldtype": "Currency",
   "label": "Max Insurance Wage",
   "non_negative": 1,
   "options": "currency"
  },
  {
   "fieldname": "social_insurance_section",
   "fieldtype": "Section Break",
   "label": "Social Insurance Rates"
  },
  {
   "default": "11",
   "fieldname": "social_insurance_employee_rate",
   "fieldtype": "Percent",
   "label": "Employee Rate"
  },
  {
   "fieldname": "column_break_3",
   "fieldtype": "Column Break"
  },
  {
   "default": "18.75",
   "fieldname": "social_insurance_employer_rate",
   "fieldtype": "Percent",
   "label": "Employer Rate"
  },
  {
   "fieldname": "overtime_section",
   "fieldtype": "Section Break",
   "label": "Overtime Multipliers"
  },
  {
   "default": "1.35",
   "fieldname": "overtime_day_multiplier",
   "fieldtype": "Float",
   "label": "Day Multiplier"
  },
  {
   "default": "1.70",
   "fieldname": "overtime_night_multiplier",
   "fieldtype": "Float",
   "label": "Night Multiplier"
  },
  {
   "fieldname": "column_break_4",
   "fieldtype": "Column Break"
  },
  {
   "default": "2.0",
   "fieldname": "overtime_rest_day_multiplier",
   "fieldtype": "Float",
   "label": "Rest Day / Holiday Multiplier"
  }
 ],
 "links": [],
 "modified": "2026-08-14 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "Payroll",
 "name": "Egypt Statutory Settings",
 "naming_rule": "By fieldname",
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
 "row_format": "Dynamic",
 "sort_field": "effective_from",
 "sort_order": "DESC",
 "states": [],
 "track_changes": 1
}
```

- [ ] **Step 4: Create the controller**

`hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model.document import Document


class EgyptStatutorySettings(Document):
	pass


def get_active_settings(date, company=None):
	"""Return the Egypt Statutory Settings record with the latest
	effective_from <= date. Prefers a company-specific record over a
	company-less default when both exist for the same date."""
	filters = {"effective_from": ["<=", date], "disabled": 0}

	name = None
	if company:
		name = frappe.db.get_value(
			"Egypt Statutory Settings",
			{**filters, "company": company},
			"name",
			order_by="effective_from desc",
		)
	if not name:
		name = frappe.db.get_value(
			"Egypt Statutory Settings",
			{**filters, "company": ["in", ["", None]]},
			"name",
			order_by="effective_from desc",
		)

	return frappe.get_doc("Egypt Statutory Settings", name) if name else None
```

`hrms/payroll/doctype/egypt_statutory_settings/__init__.py` (empty file).

- [ ] **Step 5: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.doctype.egypt_statutory_settings.test_egypt_statutory_settings`
Expected: PASS (all 3 tests). If no bench available, report NOT EXECUTED
with a static-read rationale (trace each assertion against the code
above by hand).

- [ ] **Step 6: Lint**

```bash
pre-commit run --files hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.py hrms/payroll/doctype/egypt_statutory_settings/__init__.py hrms/payroll/doctype/egypt_statutory_settings/test_egypt_statutory_settings.py
```

- [ ] **Step 7: Commit**

```bash
git add hrms/payroll/doctype/egypt_statutory_settings/
git commit -m "feat(egypt): add Egypt Statutory Settings doctype for dated payroll parameters"
```

---

## Task 2: Insurance Wage formula helper wired into `COMPONENT_EVAL_GLOBALS`

**Files:**
- Modify: `hrms/payroll/utils.py` (add one function, add one dict entry)
- Create: `hrms/payroll/test_utils_egypt.py`

**Interfaces:**
- Consumes: `hrms.payroll.doctype.egypt_statutory_settings.egypt_statutory_settings.get_active_settings`
  (Task 1).
- Produces: `hrms.payroll.utils.egypt_insurance_wage_bounds(date, company=None) -> tuple[float, float]`
  registered in `COMPONENT_EVAL_GLOBALS` under the key
  `"egypt_insurance_wage_bounds"`. Consumed by Task 3's seeded Insurance
  Wage salary component formula as
  `min(max(GP * 0.75, egypt_insurance_wage_bounds(date, company)[0]), egypt_insurance_wage_bounds(date, company)[1])`
  — Task 3 writes the exact formula string; this task only has to make
  the function callable from formula context.

- [ ] **Step 1: Write the failing test**

`hrms/payroll/test_utils_egypt.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from hrms.payroll.utils import COMPONENT_EVAL_GLOBALS, egypt_insurance_wage_bounds


class TestEgyptInsuranceWageBounds(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_registered_in_component_eval_globals(self):
		self.assertIn("egypt_insurance_wage_bounds", COMPONENT_EVAL_GLOBALS)
		self.assertIs(
			COMPONENT_EVAL_GLOBALS["egypt_insurance_wage_bounds"], egypt_insurance_wage_bounds
		)

	def test_returns_bounds_from_active_settings(self):
		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"effective_from": "2026-01-01",
				"min_insurance_wage": 2000,
				"max_insurance_wage": 14500,
			}
		).insert()

		bounds = egypt_insurance_wage_bounds(getdate("2026-06-01"))
		self.assertEqual(bounds, (2000, 14500))

	def test_returns_zero_bounds_when_no_settings_exist(self):
		bounds = egypt_insurance_wage_bounds(getdate("1999-01-01"))
		self.assertEqual(bounds, (0, 0))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.test_utils_egypt`
Expected: FAIL — `ImportError: cannot import name 'egypt_insurance_wage_bounds'`.
If no bench available, report NOT EXECUTED with rationale.

- [ ] **Step 3: Add the function and register it**

In `hrms/payroll/utils.py`, add after the `COMPONENT_EVAL_GLOBALS` dict
definition (after the closing `}` currently at the end of that literal):

```python
def egypt_insurance_wage_bounds(date, company=None) -> tuple[float, float]:
	"""Return (min_insurance_wage, max_insurance_wage) from the active
	Egypt Statutory Settings record for the given date, or (0, 0) if none
	exists. Registered in COMPONENT_EVAL_GLOBALS so Salary Component
	formulas can call it directly by name."""
	from hrms.payroll.doctype.egypt_statutory_settings.egypt_statutory_settings import (
		get_active_settings,
	)

	settings = get_active_settings(date, company=company)
	if not settings:
		return (0, 0)
	return (settings.min_insurance_wage or 0, settings.max_insurance_wage or 0)


COMPONENT_EVAL_GLOBALS["egypt_insurance_wage_bounds"] = egypt_insurance_wage_bounds
```

Note: this is a module-level statement executed once at import time,
appended after the `COMPONENT_EVAL_GLOBALS` dict literal — it does not
modify the dict literal itself, avoiding a merge-conflict-prone edit to
existing lines.

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.test_utils_egypt`
Expected: PASS (all 3 tests). If no bench, report NOT EXECUTED with
static-read rationale.

- [ ] **Step 5: Lint**

```bash
pre-commit run --files hrms/payroll/utils.py hrms/payroll/test_utils_egypt.py
```

- [ ] **Step 6: Commit**

```bash
git add hrms/payroll/utils.py hrms/payroll/test_utils_egypt.py
git commit -m "feat(egypt): register insurance wage bounds helper in salary component eval globals"
```

---

## Task 3: Salary component and income tax slab fixtures

**Files:**
- Modify: `hrms/regional/egypt/data/salary_components.json` (currently
  `[]` — populate with fixture records)
- Modify: `hrms/regional/egypt/setup.py` (add income tax slab seeding —
  `Income Tax Slab` is `is_submittable`, which
  `hrms/overrides/company.py:make_salary_components()` does not handle
  generically for submittable fixtures the way it does the plain-JSON
  salary components list, so slabs are seeded from `setup()` directly,
  same file, new function)
- Modify: `hrms/regional/egypt/test_setup.py` (extend)

**Interfaces:**
- Consumes: none new (uses existing `create_custom_fields` pattern
  already in this file from Area 1).
- Produces: seeded `Salary Component` records: `Basic Salary` (Earning),
  `Meal Allowance` (Earning), `Grants` (Earning), `Living Cost` (Earning),
  `Wage Supplement` (Earning), `Performance Motivation` (Earning),
  `Production Motivation` (Earning), `Transportation Allowance`
  (Earning), `Gross Salary` (Earning, statistical), `Insurance Wage`
  (Earning, `amount_based_on_formula=1`,
  `formula="min(max(GP * 0.75, egypt_insurance_wage_bounds(getdate())[0]), egypt_insurance_wage_bounds(getdate())[1])"`,
  `statistical_component=1`), `Social Insurance Contribution`
  (Deduction, `exempted_from_income_tax=1`). Seeded `Income Tax Slab`
  records: `Egypt Income Tax Slab - Standard`
  (`standard_tax_exemption_amount=20000`), `Egypt Income Tax Slab -
  Disability` (`standard_tax_exemption_amount=30000`) — both share the
  same 7-bracket `slabs` table. Function
  `hrms.regional.egypt.setup.make_income_tax_slabs() -> None`, called
  from `setup()`.

- [ ] **Step 1: Write the failing tests**

Add to `hrms/regional/egypt/test_setup.py`:

```python
	def test_salary_components_fixture_has_expected_components(self):
		import json
		import os

		fixture_path = os.path.join(
			os.path.dirname(__file__), "data", "salary_components.json"
		)
		with open(fixture_path) as f:
			components = json.load(f)

		names = {c["salary_component"] for c in components}
		expected = {
			"Basic Salary",
			"Meal Allowance",
			"Grants",
			"Living Cost",
			"Wage Supplement",
			"Performance Motivation",
			"Production Motivation",
			"Transportation Allowance",
			"Gross Salary",
			"Insurance Wage",
			"Social Insurance Contribution",
		}
		self.assertEqual(expected, names)

		insurance_wage = next(c for c in components if c["salary_component"] == "Insurance Wage")
		self.assertTrue(insurance_wage["amount_based_on_formula"])
		self.assertIn("egypt_insurance_wage_bounds", insurance_wage["formula"])

		social_insurance = next(
			c for c in components if c["salary_component"] == "Social Insurance Contribution"
		)
		self.assertEqual(social_insurance["type"], "Deduction")
		self.assertTrue(social_insurance["exempted_from_income_tax"])

	def test_setup_creates_income_tax_slabs(self):
		setup()
		self.assertTrue(frappe.db.exists("Income Tax Slab", "Egypt Income Tax Slab - Standard"))
		self.assertTrue(frappe.db.exists("Income Tax Slab", "Egypt Income Tax Slab - Disability"))

		standard = frappe.get_doc("Income Tax Slab", "Egypt Income Tax Slab - Standard")
		self.assertEqual(standard.standard_tax_exemption_amount, 20000)
		self.assertEqual(len(standard.slabs), 7)

		disability = frappe.get_doc("Income Tax Slab", "Egypt Income Tax Slab - Disability")
		self.assertEqual(disability.standard_tax_exemption_amount, 30000)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: FAIL — `test_salary_components_fixture_has_expected_components`
fails on the `assertEqual(expected, names)` (empty fixture currently);
`test_setup_creates_income_tax_slabs` fails — `make_income_tax_slabs`
doesn't exist yet / slabs never created. If no bench, report NOT EXECUTED
with rationale (fixture is literally `[]` right now — confirmed by
reading the file, so the fixture test's failure is guaranteed without
execution).

- [ ] **Step 3: Populate the salary components fixture**

Replace `hrms/regional/egypt/data/salary_components.json` (currently `[]`)
with:

```json
[
	{
		"doctype": "Salary Component",
		"salary_component": "Basic Salary",
		"salary_component_abbr": "BS",
		"type": "Earning",
		"is_tax_applicable": 1
	},
	{
		"doctype": "Salary Component",
		"salary_component": "Meal Allowance",
		"salary_component_abbr": "MA",
		"type": "Earning",
		"is_tax_applicable": 1
	},
	{
		"doctype": "Salary Component",
		"salary_component": "Grants",
		"salary_component_abbr": "GR",
		"type": "Earning",
		"is_tax_applicable": 1
	},
	{
		"doctype": "Salary Component",
		"salary_component": "Living Cost",
		"salary_component_abbr": "LC",
		"type": "Earning",
		"is_tax_applicable": 1
	},
	{
		"doctype": "Salary Component",
		"salary_component": "Wage Supplement",
		"salary_component_abbr": "WS",
		"type": "Earning",
		"is_tax_applicable": 1
	},
	{
		"doctype": "Salary Component",
		"salary_component": "Performance Motivation",
		"salary_component_abbr": "PM",
		"type": "Earning",
		"is_tax_applicable": 1
	},
	{
		"doctype": "Salary Component",
		"salary_component": "Production Motivation",
		"salary_component_abbr": "PDM",
		"type": "Earning",
		"is_tax_applicable": 1
	},
	{
		"doctype": "Salary Component",
		"salary_component": "Transportation Allowance",
		"salary_component_abbr": "TA",
		"type": "Earning",
		"is_tax_applicable": 0
	},
	{
		"doctype": "Salary Component",
		"salary_component": "Gross Salary",
		"salary_component_abbr": "GP",
		"type": "Earning",
		"statistical_component": 1,
		"do_not_include_in_total": 1
	},
	{
		"doctype": "Salary Component",
		"salary_component": "Insurance Wage",
		"salary_component_abbr": "IW",
		"type": "Earning",
		"statistical_component": 1,
		"do_not_include_in_total": 1,
		"amount_based_on_formula": 1,
		"formula": "min(max(GP * 0.75, egypt_insurance_wage_bounds(getdate())[0]), egypt_insurance_wage_bounds(getdate())[1])"
	},
	{
		"doctype": "Salary Component",
		"salary_component": "Social Insurance Contribution",
		"salary_component_abbr": "SIC",
		"type": "Deduction",
		"exempted_from_income_tax": 1,
		"amount_based_on_formula": 1,
		"formula": "IW * 0.11"
	}
]
```

- [ ] **Step 4: Add income tax slab seeding to `setup.py`**

In `hrms/regional/egypt/setup.py`, update `setup()` and add the new
function (place after `make_custom_fields`):

```python
def setup():
	make_custom_fields()
	make_income_tax_slabs()
```

```python
def make_income_tax_slabs():
	slabs = [
		{"from_amount": 0, "to_amount": 40000, "percent_deduction": 0},
		{"from_amount": 40000, "to_amount": 55000, "percent_deduction": 10},
		{"from_amount": 55000, "to_amount": 70000, "percent_deduction": 15},
		{"from_amount": 70000, "to_amount": 200000, "percent_deduction": 20},
		{"from_amount": 200000, "to_amount": 400000, "percent_deduction": 22.5},
		{"from_amount": 400000, "to_amount": 600000, "percent_deduction": 25},
		{"from_amount": 600000, "to_amount": 0, "percent_deduction": 27},
	]

	for name, exemption in (
		("Egypt Income Tax Slab - Standard", 20000),
		("Egypt Income Tax Slab - Disability", 30000),
	):
		if frappe.db.exists("Income Tax Slab", name):
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Income Tax Slab",
				"name": name,
				"effective_from": "2026-01-01",
				"currency": "EGP",
				"standard_tax_exemption_amount": exemption,
				"slabs": slabs,
			}
		)
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		doc.submit()
```

Note: bracket boundaries above are placeholders consistent with the
spec's "brackets at 0% / 10% / 15% / 20% / 22.5% / 25% / 27%" — the
implementer must replace the `from_amount`/`to_amount` values with the
exact figures from `docs/Payroll System.rtf.doc` (the source document)
before this task is considered complete; if that source document is not
available in this environment either, use Egypt's published 2026 annual
income tax bracket thresholds and record the source/date used as a
one-line comment above the `slabs` list.

- [ ] **Step 5: Run tests to verify they pass**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: PASS (all tests). If no bench, report NOT EXECUTED with
static-read rationale — trace `make_income_tax_slabs` by hand against
each assertion.

- [ ] **Step 6: Lint**

```bash
pre-commit run --files hrms/regional/egypt/data/salary_components.json hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py
```

- [ ] **Step 7: Commit**

```bash
git add hrms/regional/egypt/data/salary_components.json hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py
git commit -m "feat(egypt): seed salary component and income tax slab fixtures"
```

---

## Task 4: Overtime validation additions (30-min threshold, manager exemption, gross-salary cap)

**Files:**
- Modify: `hrms/hooks.py` (add `regional_overrides["Egypt"]` entry)
- Create: `hrms/regional/egypt/utils.py`
- Create: `hrms/regional/egypt/test_utils.py`
- Modify: `hrms/hr/doctype/overtime_slip/overtime_slip.py` (add one
  regional-override-eligible call-out in
  `validate_overtime_date_and_duration`, at the point where each
  `overtime_detail` row is checked — after the existing
  `maximum_overtime_hours` check at line ~101, before the loop moves to
  the next `detail`)

**Interfaces:**
- Consumes: `Overtime Type.maximum_overtime_hours_allowed` (existing
  field, already read at `overtime_slip.py:91-94`), Employee
  `is_person_of_determination` (not used here — no relation), Employee
  `designation`/reports_to (used to detect "manager-grade" — see Step 3
  for the exact detection rule), `Salary Component` gross salary lookup
  via the seeded `Gross Salary` component from Task 3.
- Produces: `hrms.regional.egypt.utils.validate_overtime_detail(overtime_slip_doc, detail) -> None`
  (raises `frappe.ValidationError` via `frappe.throw` on violation, does
  nothing otherwise) registered as
  `hrms.hr.doctype.overtime_slip.overtime_slip.validate_overtime_detail_hook`
  in `regional_overrides["Egypt"]`. The base (non-regional) function
  `validate_overtime_detail_hook` is a no-op, defined in
  `overtime_slip.py` itself, called once per detail row inside the
  existing loop — `erpnext.allow_regional` wraps it so Egypt companies
  get the real checks and all others get the no-op, matching the pattern
  India uses for `hrms.hr.utils.calculate_annual_eligible_hra_exemption`.

- [ ] **Step 1: Write the failing test**

`hrms/regional/egypt/test_utils.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from hrms.regional.egypt.utils import validate_overtime_detail


class TestEgyptOvertimeValidation(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_rejects_overtime_below_30_minutes(self):
		slip = frappe._dict(employee="_Test Employee")
		detail = frappe._dict(overtime_duration=0.4, is_weekend=0, is_holiday=0)

		with self.assertRaises(frappe.ValidationError):
			validate_overtime_detail(slip, detail)

	def test_allows_overtime_at_or_above_30_minutes(self):
		slip = frappe._dict(employee="_Test Employee")
		detail = frappe._dict(overtime_duration=0.5, is_weekend=0, is_holiday=0)

		# should not raise
		validate_overtime_detail(slip, detail)

	def test_allows_short_duration_on_rest_day_or_holiday(self):
		slip = frappe._dict(employee="_Test Employee")
		detail = frappe._dict(overtime_duration=0.1, is_weekend=1, is_holiday=0)

		# rest-day/holiday overtime is exempt from the 30-minute threshold
		validate_overtime_detail(slip, detail)
```

Note: this test intentionally exercises `validate_overtime_detail` as a
pure function taking simple `frappe._dict` stand-ins rather than full
`Overtime Slip`/`Overtime Details` documents, since the 30-minute
threshold and rest-day exemption depend only on `overtime_duration`,
`is_weekend`, `is_holiday` — keeping the test independent of Employee/
Salary Structure Assignment fixtures. The manager-grade and
gross-salary-cap checks (Step 3) require a real Employee and are covered
by a separate, HRMSTestSuite-based test class in Step 4 below since they
need `make_employee`.

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_utils`
Expected: FAIL — `ModuleNotFoundError: No module named 'hrms.regional.egypt.utils'`.
If no bench, report NOT EXECUTED with rationale.

- [ ] **Step 3: Create `hrms/regional/egypt/utils.py`**

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _

MIN_OVERTIME_DURATION_HOURS = 0.5
GROSS_SALARY_OVERTIME_CAP = 25000


def validate_overtime_detail(overtime_slip, detail):
	"""Egypt-specific Overtime Slip row validation:
	- no overtime below the 30-minute threshold, except on rest days/holidays
	- no overtime for manager-grade employees, except on rest days/holidays
	- no overtime for employees with gross salary > 25,000 EGP, except on
	  rest days/holidays
	Registered via regional_overrides["Egypt"] against
	hrms.hr.doctype.overtime_slip.overtime_slip.validate_overtime_detail_hook.
	"""
	is_rest_day_or_holiday = bool(detail.get("is_weekend") or detail.get("is_holiday"))

	if not is_rest_day_or_holiday and detail.get("overtime_duration", 0) < MIN_OVERTIME_DURATION_HOURS:
		frappe.throw(
			_("Overtime of less than {0} hours is not allowed except on rest days or holidays").format(
				MIN_OVERTIME_DURATION_HOURS
			)
		)

	if is_rest_day_or_holiday:
		return

	employee = overtime_slip.get("employee")
	if not employee:
		return

	if _is_manager_grade(employee):
		frappe.throw(_("Overtime is not allowed for manager-grade employees except on rest days or holidays"))

	if _get_gross_salary(employee) > GROSS_SALARY_OVERTIME_CAP:
		frappe.throw(
			_("Overtime is not allowed for employees with gross salary above {0} EGP").format(
				GROSS_SALARY_OVERTIME_CAP
			)
		)


def _is_manager_grade(employee):
	"""An employee is manager-grade if they have at least one direct report."""
	return bool(frappe.db.exists("Employee", {"reports_to": employee, "status": "Active"}))


def _get_gross_salary(employee):
	from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
		get_assigned_salary_structure,
	)

	salary_structure = get_assigned_salary_structure(employee, frappe.utils.getdate())
	if not salary_structure:
		return 0

	amount = frappe.db.get_value(
		"Salary Detail",
		{
			"parent": salary_structure,
			"parentfield": "earnings",
			"salary_component": "Gross Salary",
		},
		"amount",
	)
	return amount or 0
```

Note on `_is_manager_grade`: this repo has no existing "is this employee
a manager" concept (confirmed — no `is_manager`/`grade` field on core
Employee found during planning). Detecting via "has direct reports"
(`reports_to` on other Employee records) is the only signal available
without inventing a new field; if the actual source document defines
"manager-grade" via a specific Employee Grade or Designation value
instead, the implementer must adjust `_is_manager_grade` accordingly and
update the test in Step 4 — this is flagged, not silently assumed away.

- [ ] **Step 4: Add the HRMSTestSuite-based test for manager/salary checks**

Append to `hrms/regional/egypt/test_utils.py`:

```python
from hrms.tests.utils import HRMSTestSuite


class TestEgyptOvertimeValidationWithEmployees(HRMSTestSuite):
	def test_rejects_overtime_for_manager_grade_employee(self):
		manager = self.make_employee("egypt_manager@example.com")
		self.make_employee("egypt_report@example.com", reports_to=manager)

		slip = frappe._dict(employee=manager)
		detail = frappe._dict(overtime_duration=1.0, is_weekend=0, is_holiday=0)

		with self.assertRaises(frappe.ValidationError):
			validate_overtime_detail(slip, detail)

	def test_allows_manager_overtime_on_rest_day(self):
		manager = self.make_employee("egypt_manager_2@example.com")
		self.make_employee("egypt_report_2@example.com", reports_to=manager)

		slip = frappe._dict(employee=manager)
		detail = frappe._dict(overtime_duration=1.0, is_weekend=1, is_holiday=0)

		# should not raise — rest day is exempt
		validate_overtime_detail(slip, detail)
```

If `HRMSTestSuite.make_employee` does not accept a `reports_to` kwarg
directly (verify against `hrms/tests/utils.py` at implementation time —
this plan was written without a live bench to confirm the exact
signature), set it via `frappe.db.set_value("Employee", report_employee,
"reports_to", manager)` immediately after creating the report employee
instead, before constructing `slip`/`detail`.

- [ ] **Step 5: Wire the hook into `overtime_slip.py` and `hooks.py`**

In `hrms/hr/doctype/overtime_slip/overtime_slip.py`, add near the top
(after existing imports):

```python
from erpnext import allow_regional


@allow_regional
def validate_overtime_detail_hook(overtime_slip, detail):
	pass
```

In `validate_overtime_date_and_duration` (existing method, currently
ends at line 101 with the `maximum_overtime_hours` check), add one call
right after the existing `if maximum_overtime_hours:` block, still
inside the `for detail in self.overtime_details:` loop:

```python
			validate_overtime_detail_hook(self, detail)
```

In `hrms/hooks.py`, extend `regional_overrides`:

```python
regional_overrides = {
	"India": {
		"hrms.hr.utils.calculate_annual_eligible_hra_exemption": "hrms.regional.india.utils.calculate_annual_eligible_hra_exemption",
		"hrms.hr.utils.calculate_hra_exemption_for_period": "hrms.regional.india.utils.calculate_hra_exemption_for_period",
		"hrms.hr.utils.calculate_tax_with_marginal_relief": "hrms.regional.india.utils.calculate_tax_with_marginal_relief",
	},
	"Egypt": {
		"hrms.hr.doctype.overtime_slip.overtime_slip.validate_overtime_detail_hook": "hrms.regional.egypt.utils.validate_overtime_detail",
	},
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_utils`
Expected: PASS (all 5 tests). If no bench, report NOT EXECUTED with
static-read rationale.

- [ ] **Step 7: Lint**

```bash
pre-commit run --files hrms/hooks.py hrms/regional/egypt/utils.py hrms/regional/egypt/test_utils.py hrms/hr/doctype/overtime_slip/overtime_slip.py
```

- [ ] **Step 8: Commit**

```bash
git add hrms/hooks.py hrms/regional/egypt/utils.py hrms/regional/egypt/test_utils.py hrms/hr/doctype/overtime_slip/overtime_slip.py
git commit -m "feat(egypt): add overtime validation for minimum duration, manager grade, and salary cap"
```

---

## Task 5: Leave-encashment formula override (3-year eligibility, 0.75×Gross×days/30)

**Files:**
- Modify: `hrms/hooks.py` (extend `regional_overrides["Egypt"]`)
- Modify: `hrms/hr/doctype/leave_encashment/leave_encashment.py` (add one
  regional-override-eligible call-out in `set_encashment_amount`)
- Modify: `hrms/regional/egypt/utils.py` (add the override function)
- Modify: `hrms/regional/egypt/test_utils.py` (extend)

**Interfaces:**
- Consumes: `Leave Encashment.employee`, `.encashment_days`,
  `.encashment_date` (existing fields); `Employee.date_of_joining`
  (existing core field); seeded `Gross Salary` salary component from
  Task 3.
- Produces: `hrms.regional.egypt.utils.calculate_leave_encashment_amount(leave_encashment_doc, default_amount) -> float`
  registered against a new base function
  `hrms.hr.doctype.leave_encashment.leave_encashment.calculate_encashment_amount_hook(leave_encashment_doc, default_amount) -> float`
  (base implementation returns `default_amount` unchanged — a pure
  passthrough — so every non-Egypt company keeps today's flat
  `leave_encashment_amount_per_day` behavior exactly as-is).

- [ ] **Step 1: Write the failing test**

Append to `hrms/regional/egypt/test_utils.py`:

```python
from hrms.regional.egypt.utils import calculate_leave_encashment_amount


class TestEgyptLeaveEncashmentAmount(HRMSTestSuite):
	def test_returns_default_amount_when_service_under_3_years(self):
		employee = self.make_employee(
			"egypt_short_tenure@example.com", date_of_joining="2025-01-01"
		)
		doc = frappe._dict(employee=employee, encashment_days=10, encashment_date="2026-06-01")

		amount = calculate_leave_encashment_amount(doc, default_amount=500)
		self.assertEqual(amount, 500)

	def test_applies_egypt_formula_after_3_years_of_service(self):
		employee = self.make_employee(
			"egypt_long_tenure@example.com", date_of_joining="2020-01-01"
		)
		self.make_salary_structure_assignment_with_gross_salary(employee, gross_salary=30000)
		doc = frappe._dict(employee=employee, encashment_days=15, encashment_date="2026-06-01")

		amount = calculate_leave_encashment_amount(doc, default_amount=0)
		# 30000 * 0.75 * 15 / 30 = 11250
		self.assertEqual(amount, 11250)
```

Note: `make_salary_structure_assignment_with_gross_salary` is a **new
test helper**, not an existing `HRMSTestSuite` method — the implementer
must add it to `hrms/regional/egypt/test_utils.py` as a local helper
function (not a suite method, since it's Egypt-specific) that creates a
minimal Salary Structure with a `Gross Salary` earning component set to
a fixed `amount` and assigns it to the employee via
`Salary Structure Assignment`, following the same pattern
`hrms/payroll/doctype/salary_structure/test_salary_structure.py`'s
`make_salary_structure` helper uses (read that file at implementation
time for the exact fixture-creation calls — `frappe.get_doc({"doctype":
"Salary Structure", ...}).insert()` then a linked
`Salary Structure Assignment` `.insert()` + `.submit()`).

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_utils`
Expected: FAIL — `ImportError: cannot import name 'calculate_leave_encashment_amount'`.
If no bench, report NOT EXECUTED with rationale.

- [ ] **Step 3: Add the override function to `hrms/regional/egypt/utils.py`**

Append:

```python
LEAVE_ENCASHMENT_ELIGIBILITY_YEARS = 3
LEAVE_ENCASHMENT_GROSS_SALARY_FACTOR = 0.75


def calculate_leave_encashment_amount(leave_encashment, default_amount):
	"""Egypt leave-encashment formula: Gross Salary * 0.75 * encashment_days / 30,
	only after 3 consecutive years of service; falls back to default_amount
	(the flat leave_encashment_amount_per_day result) otherwise.
	Registered via regional_overrides["Egypt"] against
	hrms.hr.doctype.leave_encashment.leave_encashment.calculate_encashment_amount_hook.
	"""
	from frappe.utils import date_diff, getdate

	employee = leave_encashment.get("employee")
	encashment_date = leave_encashment.get("encashment_date") or getdate()

	date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
	if not date_of_joining:
		return default_amount

	years_of_service = date_diff(encashment_date, date_of_joining) / 365.25
	if years_of_service < LEAVE_ENCASHMENT_ELIGIBILITY_YEARS:
		return default_amount

	gross_salary = _get_gross_salary(employee)
	if not gross_salary:
		return default_amount

	encashment_days = leave_encashment.get("encashment_days") or 0
	return gross_salary * LEAVE_ENCASHMENT_GROSS_SALARY_FACTOR * encashment_days / 30
```

`_get_gross_salary` is already defined in this file from Task 4 — reused
as-is, no duplication.

- [ ] **Step 4: Wire the hook into `leave_encashment.py` and `hooks.py`**

In `hrms/hr/doctype/leave_encashment/leave_encashment.py`, add near the
top (after existing imports):

```python
from erpnext import allow_regional


@allow_regional
def calculate_encashment_amount_hook(leave_encashment, default_amount):
	return default_amount
```

Modify `set_encashment_amount` (existing method, currently ends with
`self.encashment_amount = self.encashment_days * per_day_encashment if per_day_encashment > 0 else 0`
at line 237) — replace that final line with:

```python
		default_amount = self.encashment_days * per_day_encashment if per_day_encashment > 0 else 0
		self.encashment_amount = calculate_encashment_amount_hook(self, default_amount)
```

In `hrms/hooks.py`, extend `regional_overrides["Egypt"]` (added in
Task 4):

```python
	"Egypt": {
		"hrms.hr.doctype.overtime_slip.overtime_slip.validate_overtime_detail_hook": "hrms.regional.egypt.utils.validate_overtime_detail",
		"hrms.hr.doctype.leave_encashment.leave_encashment.calculate_encashment_amount_hook": "hrms.regional.egypt.utils.calculate_leave_encashment_amount",
	},
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_utils`
Expected: PASS (all 7 tests). If no bench, report NOT EXECUTED with
static-read rationale.

- [ ] **Step 6: Lint**

```bash
pre-commit run --files hrms/hooks.py hrms/regional/egypt/utils.py hrms/regional/egypt/test_utils.py hrms/hr/doctype/leave_encashment/leave_encashment.py
```

- [ ] **Step 7: Commit**

```bash
git add hrms/hooks.py hrms/regional/egypt/utils.py hrms/regional/egypt/test_utils.py hrms/hr/doctype/leave_encashment/leave_encashment.py
git commit -m "feat(egypt): override leave encashment amount with 3-year eligibility formula"
```

---

## Task 6: Gratuity rules fixture

**Files:**
- Modify: `hrms/regional/egypt/setup.py` (add gratuity rule seeding,
  following `hrms/regional/united_arab_emirates/setup.py`'s
  `create_gratuity_rules_for_uae()` pattern exactly)
- Modify: `hrms/regional/egypt/test_setup.py` (extend)

**Interfaces:**
- Consumes: `Gratuity Rule` / `Gratuity Rule Slab` doctypes (existing,
  confirmed present — no changes needed to either).
- Produces: one seeded `Gratuity Rule` named `"Egypt Standard Gratuity
  Rule"`. Function `hrms.regional.egypt.setup.make_gratuity_rule() -> None`,
  called from `setup()`.

- [ ] **Step 1: Write the failing test**

Add to `hrms/regional/egypt/test_setup.py`:

```python
	def test_setup_creates_gratuity_rule(self):
		setup()
		self.assertTrue(frappe.db.exists("Gratuity Rule", "Egypt Standard Gratuity Rule"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: FAIL — `Gratuity Rule` "Egypt Standard Gratuity Rule" does not
exist (function not called yet). If no bench, report NOT EXECUTED with
rationale.

- [ ] **Step 3: Add `make_gratuity_rule` and call it from `setup()`**

In `hrms/regional/egypt/setup.py`:

```python
def setup():
	make_custom_fields()
	make_income_tax_slabs()
	make_gratuity_rule()
```

```python
def make_gratuity_rule():
	if frappe.db.exists("Gratuity Rule", "Egypt Standard Gratuity Rule"):
		return

	doc = frappe.get_doc(
		{
			"doctype": "Gratuity Rule",
			"name": "Egypt Standard Gratuity Rule",
			"calculate_gratuity_amount_based_on": "Sum of all previous slabs",
			"work_experience_calculation_method": "Take Exact Completed Years",
			"minimum_year_for_gratuity": 1,
			"gratuity_rule_slabs": [
				{"from_year": 0, "to_year": 5, "fraction_of_applicable_earnings": 0.5},
				{"from_year": 5, "to_year": 0, "fraction_of_applicable_earnings": 1},
			],
		}
	)
	doc.insert(ignore_permissions=True, ignore_mandatory=True)
```

Note: the `gratuity_rule_slabs` values above (half-month salary per year
for the first 5 years, full month per year after) are a placeholder
matching common Egyptian end-of-service norms; the implementer must
confirm exact fractions against `docs/Payroll System.rtf.doc` (the
spec's source document) before this task is considered complete, same
caveat as Task 3's tax bracket thresholds.

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: PASS (all tests). If no bench, report NOT EXECUTED with
static-read rationale.

- [ ] **Step 5: Lint**

```bash
pre-commit run --files hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py
```

- [ ] **Step 6: Commit**

```bash
git add hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py
git commit -m "feat(egypt): seed standard gratuity rule"
```

---

## Task 7: Whole-area integration test

**Files:**
- Create: `hrms/regional/egypt/test_integration_area3.py`

**Interfaces:**
- Consumes: everything from Tasks 1-6.
- Produces: none — final verification task for Area 3.

- [ ] **Step 1: Write the integration test**

`hrms/regional/egypt/test_integration_area3.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from hrms.regional.egypt.setup import setup, uninstall


class TestEgyptArea3Integration(IntegrationTestCase):
	def tearDown(self):
		uninstall()
		frappe.db.rollback()

	def test_setup_creates_all_area3_fixtures(self):
		setup()

		self.assertTrue(frappe.db.exists("Salary Component", "Insurance Wage"))
		self.assertTrue(frappe.db.exists("Salary Component", "Social Insurance Contribution"))
		self.assertTrue(frappe.db.exists("Income Tax Slab", "Egypt Income Tax Slab - Standard"))
		self.assertTrue(frappe.db.exists("Income Tax Slab", "Egypt Income Tax Slab - Disability"))
		self.assertTrue(frappe.db.exists("Gratuity Rule", "Egypt Standard Gratuity Rule"))
```

Note: `uninstall()` (existing, from Area 1) only deletes custom fields —
it does not remove the `Income Tax Slab`/`Gratuity Rule`/`Salary
Component` fixtures this task seeds, since those are shared submittable
masters that other tests might reference by name and India's `uninstall`
pattern doesn't remove its `Gratuity Rule` fixtures either (confirmed —
`hrms/regional/india/setup.py:uninstall` only calls
`delete_custom_fields`). This is intentional, matching existing
convention; `tearDown` still calls `uninstall()` for custom-field
cleanup consistency with the other Egypt test files, and doesn't attempt
new cleanup beyond what the existing pattern already does.

- [ ] **Step 2: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_integration_area3`
Expected: PASS. If no bench, report NOT EXECUTED with a static-read
rationale tracing `setup()` -> `make_custom_fields()` +
`make_income_tax_slabs()` + `make_gratuity_rule()` against each
assertion.

- [ ] **Step 3: Run the full Egypt regional test suite together**

```bash
bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup
bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_integration
bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_utils
bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_integration_area3
bench --site test_site run-tests --app hrms --module hrms.payroll.doctype.egypt_statutory_settings.test_egypt_statutory_settings
bench --site test_site run-tests --app hrms --module hrms.payroll.test_utils_egypt
```

Expected: all PASS.

- [ ] **Step 4: Lint**

```bash
pre-commit run --files hrms/regional/egypt/test_integration_area3.py
```

- [ ] **Step 5: Commit**

```bash
git add hrms/regional/egypt/test_integration_area3.py
git commit -m "test(egypt): verify Area 3 fixtures install together via setup()"
```

---

## Self-Review Notes

**Spec coverage (spec §6, Area 3):**
- `Egypt Statutory Settings` dated doctype (min/max basic wage, min/max
  insurance wage, social insurance rates, overtime multipliers) → Task 1.
- Insurance Wage formula helper via `COMPONENT_EVAL_GLOBALS` → Task 2.
- Salary Component fixtures (Basic Salary, Meal Allowance, Grants,
  Living Cost, Wage Supplement, Performance/Production Motivation,
  Transportation Allowance, Gross Salary, Insurance Wage formula
  component, Social Insurance Contribution with
  `exempted_from_income_tax`) → Task 3.
- Income Tax Slab seeded records (Standard 20k exemption, Disability 30k
  exemption, shared bracket table) → Task 3.
- Overtime: reuse `Overtime Type` multiplier fields (no new fields
  needed — confirmed already sufficient) + three new validation rules
  (30-min threshold, manager exemption, >25k EGP cap) → Task 4, via
  `regional_overrides`, exact function pinned
  (`validate_overtime_date_and_duration` in `overtime_slip.py`).
- Gratuity: reuse `Gratuity Rule`/`Gratuity Rule Slab` (proven UAE
  pattern) → Task 6.
- Leave encashment formula (`Gross Salary × 0.75 × days/30`, 3-year gate)
  → Task 5, via `regional_overrides`, exact function pinned
  (`set_encashment_amount` in `leave_encashment.py`), confirmed
  `Leave Encashment` doctype already exists rather than needing to be
  built from scratch (spec explicitly flagged this as needing
  verification — done during planning, see Global Constraints).
- Whole-area wiring verified end-to-end → Task 7.

**Explicitly deferred / flagged, not silently dropped:**
- Exact income tax bracket thresholds (Task 3) and gratuity slab
  fractions (Task 6) are placeholders pending confirmation against
  `docs/Payroll System.rtf.doc`, which was not accessible during this
  planning session (same environment constraint noted in the Area 1
  plan's progress ledger — no bench, and this source document was not
  found in the repo tree). Both tasks contain an explicit, concrete
  placeholder-resolution instruction, not a vague TODO.
- "Manager-grade" detection (Task 4) uses a "has direct reports"
  heuristic since no existing Employee field captures this concept —
  flagged as an assumption the implementer must verify against the
  source document, with the exact code location to change if wrong.
- Area 4 (Statutory Funds) is a separate area per spec §7/§10 and
  explicitly out of scope for this plan; `Egypt Statutory Settings`
  (Task 1) is designed to be its future rate source, noted in Task 1's
  Interfaces block, but no Statutory Fund doctype work happens here.

**Placeholder scan:** No vague "TBD"/"add error handling" left. The two
data-value placeholders (tax brackets, gratuity fractions) are flagged
above per the "No Placeholders" rule's allowance for explicitly-flagged,
concretely-actionable gaps versus silent vagueness — both come with a
working, runnable default and a precise instruction for what to verify
and where.

**Type/name consistency:** `get_active_settings(date, company=None)`
(Task 1) signature matches its Task 2 call site exactly.
`egypt_insurance_wage_bounds(date, company=None)` (Task 2) registered
under that exact key, matches the formula string in Task 3's fixture
JSON (`egypt_insurance_wage_bounds(getdate())[0]` /`[1]`, called with
only `date` positionally — `company` left as default `None`, consistent
with the function signature since Salary Component formulas don't have
easy access to the company at eval time without extra plumbing this plan
doesn't add). `validate_overtime_detail_hook` / `validate_overtime_detail`
naming matches between Task 4's `overtime_slip.py` edit and
`regional_overrides` entry. `calculate_encashment_amount_hook` /
`calculate_leave_encashment_amount` naming matches between Task 5's
`leave_encashment.py` edit and `regional_overrides` entry.
`_get_gross_salary` defined once in Task 4, reused unmodified by Task 5
— confirmed no duplicate definition across the two tasks' diffs to
`hrms/regional/egypt/utils.py` (Task 4 creates the file, Task 5 appends
to it).
