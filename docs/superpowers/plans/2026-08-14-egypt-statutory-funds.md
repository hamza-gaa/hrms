# Egypt Statutory Funds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new `Egypt Statutory Fund` doctype implementing the
source document's "Special Funds Calculation Screen" — one record per
fund type per company per period, with a `compute()` method that counts
insured employees, applies the fund's rate/min/max, and stores the
computed contribution. Standalone compliance/reporting data; does not
post to Salary Slip or GL (per spec §9 explicit scope note).

**Architecture:** One new submittable doctype in the `Payroll` module,
following the `Income Tax Slab`/`Egypt Statutory Settings` structural
pattern (dated/period-scoped record, `System Manager`+`HR Manager`
permissions). `Egypt Statutory Settings` (already built in the Area 3
plan) is extended with four new rate/bound fields so fund rates stay
in the same single "Fixed Parameters" source of truth the spec's §3
describes, rather than hardcoding rates into the new doctype. A
whitelisted `compute()` document method counts active employees with a
non-empty `social_insurance_number` (Area 1 field) for the record's
company, checks the fund's headcount threshold, applies the rate with
min/max bounds, and sets `computed_contribution` + `status`.

**Tech Stack:** Frappe Framework doctype JSON + Python controllers,
`frappe.whitelist()` document method, `bench run-tests`.

**Spec:** `docs/superpowers/specs/2026-08-13-egypt-payroll-localization-design.md`
(Section 7 — Area 4: Statutory Funds), cross-checked against
`docs/Payroll System.rtf.doc` ("Special Funds Calculation Screen" table
and the "Emergency Relief Fund" / "Martyrs' Families Fund" / "Training and
Rehabilitation Fund" / "Social, Health, and Cultural Services Fund"
definitions in the "Some important definitions" table) during planning on
2026-08-14.

## Global Constraints

- Custom field / doctype field `fieldname`s use **no `custom_` prefix**,
  consistent with Areas 1/3.
- New doctype belongs to the `Payroll` module (`Egypt Statutory Settings`,
  `Income Tax Slab`, `Gratuity Rule` all live there per
  `hrms/modules.txt` — this doctype follows suit as a
  payroll-parameters/compliance doctype).
- Tab indentation, double quotes, line length 110 (ruff,
  `pyproject.toml`). No bench/pre-commit/ruff binary was available in the
  session that wrote this plan — trace changes by hand against each
  test's assertions if unavailable at implementation time; do not
  fabricate PASS output.
- Tests live next to the code as `test_*.py`, extending
  `hrms.tests.utils.HRMSTestSuite` for anything needing `make_employee`.
- Commit messages follow Conventional Commits.
- Per spec §9 ("Explicitly Out of Scope"): this doctype does **not** post
  to Salary Slip or GL. `compute()` only writes to its own document.
- **Confirmed against current code** (read during planning, 2026-08-14):
  - No `Egypt Statutory Fund` doctype exists anywhere in the repo
    (confirmed via filesystem search).
  - `Egypt Statutory Settings`
    (`hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json`,
    built in the Area 3 plan) currently has exactly these fields:
    `effective_from`, `company`, `disabled`, `min_basic_wage`,
    `max_basic_wage`, `min_insurance_wage`, `max_insurance_wage`,
    `social_insurance_employee_rate`, `social_insurance_employer_rate`,
    `overtime_day_multiplier`, `overtime_night_multiplier`,
    `overtime_rest_day_multiplier` — **zero fund-rate fields**, confirmed
    directly from the JSON. Task 1 of this plan adds four new fields to
    this existing doctype (not a new one) for the fund rates/bounds.
  - `Income Tax Slab`
    (`hrms/payroll/doctype/income_tax_slab/income_tax_slab.json`) is
    `is_submittable: 1` with permissions `System Manager` / `HR Manager`
    / `HR User` (all `submit`+`cancel`) — the closest existing
    period-scoped payroll-parameters doctype; `Egypt Statutory Fund`
    follows this exact permission shape (Task 2).
  - `social_insurance_number` (Data, Employee, no `custom_` prefix)
    confirmed present from Area 1 (`hrms/regional/egypt/setup.py:116`) —
    Task 2's `compute()` filters on
    `["social_insurance_number", "is", "set"]` combined with
    `status = "Active"` and `company = self.company`.
  - No existing "count employees matching filter, apply rate with
    min/max, save computed amount, Draft/Computed/Paid status" doctype
    exists in this codebase to copy verbatim (researched:
    `Payroll Entry.fill_employee_details()` at
    `hrms/payroll/doctype/payroll_entry/payroll_entry.py:264` is the
    closest structural analog for "aggregate employees for a company +
    period, store the count/list on self" — used as the shape reference
    for `compute()`'s employee-counting step, not copied verbatim since
    Payroll Entry's `get_employee_list()` is salary-structure-scoped and
    not applicable here). `Gratuity.get_gratuity_amount()`
    (`hrms/payroll/doctype/gratuity/gratuity.py:234`) is the closest
    analog for "apply min/max-bounded rate to a base amount," used as
    the shape reference for the rate-application step.
  - `Payroll Entry`'s `status` field
    (`hrms/payroll/doctype/payroll_entry/payroll_entry.json`) uses
    `Select: Draft\nSubmitted\nCancelled\nQueued\nFailed`, distinct from
    `docstatus` — `Egypt Statutory Fund`'s `status` field (Task 2) follows
    the same "separate Select field from docstatus" shape, with the
    spec's own proposed values `Draft\nComputed\nPaid`.

---

## Task 1: Extend `Egypt Statutory Settings` with fund rates/bounds

**Files:**
- Modify: `hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json`
- Modify: `hrms/payroll/doctype/egypt_statutory_settings/test_egypt_statutory_settings.py`

**Interfaces:**
- Produces: four new fields on the existing `Egypt Statutory Settings`
  doctype: `emergency_relief_fund_rate` (Percent, default 1 — "1% from
  basic salary" per the document's Emergency Relief Fund definition and
  Special Funds table row 1), `cultural_services_fund_min` /
  `cultural_services_fund_max` (Currency, defaults 8 / 16 — "8 EGP" per
  the fund definition table, "8-16 EGP" per the Special Funds table;
  document has two slightly different figures for this fund, see Task 3
  note), `training_fund_rate` (Percent, default 0.25),
  `training_fund_min` / `training_fund_max` (Currency, defaults 10 / 30).
  Consumed by Task 2's `Egypt Statutory Fund.compute()`.

- [ ] **Step 1: Write the failing test**

Add to `hrms/payroll/doctype/egypt_statutory_settings/test_egypt_statutory_settings.py`:

```python
	def test_create_settings_with_fund_rates(self):
		doc = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"effective_from": "2026-02-01",
				"emergency_relief_fund_rate": 1,
				"cultural_services_fund_min": 8,
				"cultural_services_fund_max": 16,
				"training_fund_rate": 0.25,
				"training_fund_min": 10,
				"training_fund_max": 30,
			}
		).insert()

		self.assertEqual(doc.emergency_relief_fund_rate, 1)
		self.assertEqual(doc.cultural_services_fund_max, 16)
		self.assertEqual(doc.training_fund_rate, 0.25)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.doctype.egypt_statutory_settings.test_egypt_statutory_settings`
Expected: FAIL — `Unknown field 'emergency_relief_fund_rate' in Egypt
Statutory Settings`. If no bench, report NOT EXECUTED with rationale
(fields absent from current JSON, confirmed during planning).

- [ ] **Step 3: Add the fields**

In `hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json`,
add `"statutory_funds_section"` and the six new fieldnames to
`field_order`, right after the existing `"overtime_rest_day_multiplier"`
entry:

```json
  "statutory_funds_section",
  "emergency_relief_fund_rate",
  "column_break_5",
  "cultural_services_fund_min",
  "cultural_services_fund_max",
  "training_funds_column_break",
  "training_fund_rate",
  "training_fund_min",
  "training_fund_max"
```

Add to the `fields` array, right before the final closing `]`:

```json
  {
   "fieldname": "statutory_funds_section",
   "fieldtype": "Section Break",
   "label": "Statutory Fund Rates"
  },
  {
   "default": "1",
   "description": "Emergency Assistance Fund: percent of total basic salaries, for companies with 30+ insured employees.",
   "fieldname": "emergency_relief_fund_rate",
   "fieldtype": "Percent",
   "label": "Emergency Relief Fund Rate"
  },
  {
   "fieldname": "column_break_5",
   "fieldtype": "Column Break"
  },
  {
   "default": "8",
   "description": "Cultural Services Fund: fixed amount per insured employee, for companies with 20+ insured employees.",
   "fieldname": "cultural_services_fund_min",
   "fieldtype": "Currency",
   "label": "Cultural Services Fund Min",
   "non_negative": 1,
   "options": "currency"
  },
  {
   "default": "16",
   "fieldname": "cultural_services_fund_max",
   "fieldtype": "Currency",
   "label": "Cultural Services Fund Max",
   "non_negative": 1,
   "options": "currency"
  },
  {
   "fieldname": "training_funds_column_break",
   "fieldtype": "Column Break"
  },
  {
   "default": "0.25",
   "description": "Training and Rehabilitation Fund: percent of minimum insurance wage per insured employee, for companies with 30+ insured employees.",
   "fieldname": "training_fund_rate",
   "fieldtype": "Percent",
   "label": "Training Fund Rate"
  },
  {
   "default": "10",
   "fieldname": "training_fund_min",
   "fieldtype": "Currency",
   "label": "Training Fund Min",
   "non_negative": 1,
   "options": "currency"
  },
  {
   "default": "30",
   "fieldname": "training_fund_max",
   "fieldtype": "Currency",
   "label": "Training Fund Max",
   "non_negative": 1,
   "options": "currency"
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.doctype.egypt_statutory_settings.test_egypt_statutory_settings`
Expected: PASS. If no bench, report NOT EXECUTED with static-read
rationale.

- [ ] **Step 5: Lint**

```bash
pre-commit run --files hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json hrms/payroll/doctype/egypt_statutory_settings/test_egypt_statutory_settings.py
```

- [ ] **Step 6: Commit**

```bash
git add hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json hrms/payroll/doctype/egypt_statutory_settings/test_egypt_statutory_settings.py
git commit -m "feat(egypt): add statutory fund rate/bound fields to Egypt Statutory Settings"
```

---

## Task 2: `Egypt Statutory Fund` doctype with `compute()`

**Files:**
- Create: `hrms/payroll/doctype/egypt_statutory_fund/__init__.py`
- Create: `hrms/payroll/doctype/egypt_statutory_fund/egypt_statutory_fund.json`
- Create: `hrms/payroll/doctype/egypt_statutory_fund/egypt_statutory_fund.py`
- Create: `hrms/payroll/doctype/egypt_statutory_fund/test_egypt_statutory_fund.py`

**Interfaces:**
- Consumes: `hrms.payroll.doctype.egypt_statutory_settings.egypt_statutory_settings.get_active_settings`
  (Task 1's fields, Area 3's existing function), `Employee.social_insurance_number`
  (Area 1), `Employee.status`, `Employee.company`.
- Produces: doctype `Egypt Statutory Fund` with fields `fund_type`
  (Select: `Emergency Relief Fund\nMartyrs' Families Fund\nTraining and
  Rehabilitation Fund\nSocial, Health and Cultural Services Fund`),
  `company` (Link, required), `period_start`/`period_end` (Date,
  required), `insured_employee_count` (Int, read-only, set by
  `compute()`), `rate_or_amount` (Percent, read-only, set by
  `compute()`), `min_value`/`max_value` (Currency, read-only),
  `computed_contribution` (Currency, read-only), `status` (Select:
  `Draft\nComputed\nPaid`, default `Draft`). Whitelisted document method
  `compute(self) -> None` — counts insured active employees for
  `self.company`, checks the fund's headcount threshold (per-fund
  constant, see Step 3), applies the matching rate from `Egypt Statutory
  Settings`, sets `self.insured_employee_count`,
  `self.computed_contribution`, `self.status = "Computed"`, saves.

- [ ] **Step 1: Write the failing test**

`hrms/payroll/doctype/egypt_statutory_fund/test_egypt_statutory_fund.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.tests.utils import HRMSTestSuite


class TestEgyptStatutoryFund(HRMSTestSuite):
	def setUp(self):
		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"effective_from": "2026-01-01",
				"emergency_relief_fund_rate": 1,
				"cultural_services_fund_min": 8,
				"cultural_services_fund_max": 16,
				"training_fund_rate": 0.25,
				"training_fund_min": 10,
				"training_fund_max": 30,
			}
		).insert(ignore_if_duplicate=True)

	def test_compute_below_headcount_threshold_yields_zero_contribution(self):
		employee = self.make_employee("egypt_fund_single_employee@example.com")
		frappe.db.set_value("Employee", employee, "social_insurance_number", "SI-001")

		fund = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Fund",
				"fund_type": "Emergency Relief Fund",
				"company": frappe.db.get_value("Employee", employee, "company"),
				"period_start": "2026-01-01",
				"period_end": "2026-01-31",
			}
		).insert()
		fund.compute()

		self.assertEqual(fund.insured_employee_count, 0)
		self.assertEqual(fund.computed_contribution, 0)
		self.assertEqual(fund.status, "Draft")

	def test_compute_counts_only_insured_active_employees_for_the_company(self):
		company = "_Test Company"
		insured = self.make_employee("egypt_fund_insured@example.com", company=company)
		frappe.db.set_value("Employee", insured, "social_insurance_number", "SI-002")
		uninsured = self.make_employee("egypt_fund_uninsured@example.com", company=company)
		frappe.db.set_value("Employee", uninsured, "social_insurance_number", "")

		fund = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Fund",
				"fund_type": "Cultural Services Fund"
				if False
				else "Social, Health and Cultural Services Fund",
				"company": company,
				"period_start": "2026-01-01",
				"period_end": "2026-01-31",
			}
		).insert()

		# force the headcount threshold check to pass regardless of how many
		# real insured employees exist in the shared test company by
		# monkeypatching the threshold map is unnecessary here: the test only
		# asserts the *counting* is correct, not the threshold gate — use
		# test_compute_applies_min_bound_when_above_threshold below for that.
		count = fund.get_insured_employee_count()
		self.assertGreaterEqual(count, 1)
```

Note: this first draft of Step 1's test intentionally only exercises the
zero-headcount / below-threshold path plus the raw counting helper,
because the shared `HRMSTestSuite` company (`_Test Company`) accumulates
employees across many other tests in the same transaction and this plan
cannot assume an exact total headcount — Step 4 replaces the second test
with an isolated-company version once `compute()` exists. Do not try to
assert an exact `computed_contribution` value against `_Test Company`
directly; use a dedicated test company (see Step 4).

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.doctype.egypt_statutory_fund.test_egypt_statutory_fund`
Expected: FAIL — `ModuleNotFoundError` (doctype doesn't exist). If no
bench, report NOT EXECUTED with rationale.

- [ ] **Step 3: Create the doctype JSON**

`hrms/payroll/doctype/egypt_statutory_fund/egypt_statutory_fund.json`:

```json
{
 "actions": [],
 "autoname": "hash",
 "creation": "2026-08-14 00:00:00.000000",
 "doctype": "DocType",
 "editable_grid": 1,
 "engine": "InnoDB",
 "field_order": [
  "fund_type",
  "company",
  "column_break_1",
  "status",
  "period_section",
  "period_start",
  "period_end",
  "computation_section",
  "insured_employee_count",
  "rate_or_amount",
  "column_break_2",
  "min_value",
  "max_value",
  "computed_contribution"
 ],
 "fields": [
  {
   "fieldname": "fund_type",
   "fieldtype": "Select",
   "in_list_view": 1,
   "label": "Fund Type",
   "options": "Emergency Relief Fund\nMartyrs' Families Fund\nTraining and Rehabilitation Fund\nSocial, Health and Cultural Services Fund",
   "reqd": 1
  },
  {
   "fieldname": "company",
   "fieldtype": "Link",
   "in_list_view": 1,
   "label": "Company",
   "options": "Company",
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
   "options": "Draft\nComputed\nPaid",
   "read_only": 1
  },
  {
   "fieldname": "period_section",
   "fieldtype": "Section Break",
   "label": "Period"
  },
  {
   "fieldname": "period_start",
   "fieldtype": "Date",
   "in_list_view": 1,
   "label": "Period Start",
   "reqd": 1
  },
  {
   "fieldname": "period_end",
   "fieldtype": "Date",
   "in_list_view": 1,
   "label": "Period End",
   "reqd": 1
  },
  {
   "fieldname": "computation_section",
   "fieldtype": "Section Break",
   "label": "Computation"
  },
  {
   "fieldname": "insured_employee_count",
   "fieldtype": "Int",
   "label": "Insured Employee Count",
   "non_negative": 1,
   "read_only": 1
  },
  {
   "description": "Percent for rate-based funds, or fixed amount for min/max-bounded funds.",
   "fieldname": "rate_or_amount",
   "fieldtype": "Float",
   "label": "Rate or Amount",
   "read_only": 1
  },
  {
   "fieldname": "column_break_2",
   "fieldtype": "Column Break"
  },
  {
   "fieldname": "min_value",
   "fieldtype": "Currency",
   "label": "Min Value",
   "non_negative": 1,
   "options": "currency",
   "read_only": 1
  },
  {
   "fieldname": "max_value",
   "fieldtype": "Currency",
   "label": "Max Value",
   "non_negative": 1,
   "options": "currency",
   "read_only": 1
  },
  {
   "fieldname": "computed_contribution",
   "fieldtype": "Currency",
   "label": "Computed Contribution",
   "non_negative": 1,
   "options": "currency",
   "read_only": 1
  }
 ],
 "links": [],
 "modified": "2026-08-14 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "Payroll",
 "name": "Egypt Statutory Fund",
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

- [ ] **Step 4: Create the controller with `compute()`**

`hrms/payroll/doctype/egypt_statutory_fund/egypt_statutory_fund.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# minimum insured headcount required before a fund applies to a company,
# per docs/Payroll System.rtf.doc "Special Funds Calculation Screen" table
FUND_HEADCOUNT_THRESHOLDS = {
	"Emergency Relief Fund": 30,
	"Martyrs' Families Fund": 0,  # document states no explicit headcount minimum
	"Training and Rehabilitation Fund": 30,
	"Social, Health and Cultural Services Fund": 20,
}


class EgyptStatutoryFund(Document):
	@frappe.whitelist()
	def compute(self):
		self.insured_employee_count = self.get_insured_employee_count()

		threshold = FUND_HEADCOUNT_THRESHOLDS.get(self.fund_type, 0)
		if self.insured_employee_count < threshold:
			self.rate_or_amount = 0
			self.min_value = 0
			self.max_value = 0
			self.computed_contribution = 0
			self.status = "Draft"
			self.save()
			return

		self._apply_fund_rate()
		self.status = "Computed"
		self.save()

	def get_insured_employee_count(self):
		return frappe.db.count(
			"Employee",
			{
				"company": self.company,
				"status": "Active",
				"social_insurance_number": ["not in", ["", None]],
			},
		)

	def _apply_fund_rate(self):
		from hrms.payroll.doctype.egypt_statutory_settings.egypt_statutory_settings import (
			get_active_settings,
		)

		settings = get_active_settings(self.period_start, company=self.company)
		if not settings:
			frappe.throw(_("No Egypt Statutory Settings found effective on or before {0}").format(self.period_start))

		if self.fund_type == "Emergency Relief Fund":
			basic_wage_total = self._get_total_basic_salary()
			self.rate_or_amount = settings.emergency_relief_fund_rate or 0
			self.min_value = 0
			self.max_value = 0
			self.computed_contribution = basic_wage_total * (self.rate_or_amount / 100)
		elif self.fund_type == "Martyrs' Families Fund":
			gross_salary_total = self._get_total_gross_salary()
			self.rate_or_amount = 0.05  # 0.05% per document ("0.0005 of monthly gross salaries")
			self.min_value = 0
			self.max_value = 0
			self.computed_contribution = gross_salary_total * (self.rate_or_amount / 100)
		elif self.fund_type == "Training and Rehabilitation Fund":
			self.rate_or_amount = settings.training_fund_rate or 0
			self.min_value = settings.training_fund_min or 0
			self.max_value = settings.training_fund_max or 0
			per_employee = (settings.min_insurance_wage or 0) * (self.rate_or_amount / 100)
			per_employee = min(max(per_employee, self.min_value), self.max_value)
			self.computed_contribution = per_employee * self.insured_employee_count
		elif self.fund_type == "Social, Health and Cultural Services Fund":
			self.rate_or_amount = 0
			self.min_value = settings.cultural_services_fund_min or 0
			self.max_value = settings.cultural_services_fund_max or 0
			per_employee = self.min_value
			self.computed_contribution = per_employee * self.insured_employee_count

	def _get_total_basic_salary(self):
		from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
			get_assigned_salary_structure,
		)

		employees = frappe.get_all(
			"Employee",
			filters={
				"company": self.company,
				"status": "Active",
				"social_insurance_number": ["not in", ["", None]],
			},
			pluck="name",
		)
		total = 0
		for employee in employees:
			salary_structure = get_assigned_salary_structure(employee, self.period_start)
			if not salary_structure:
				continue
			amount = frappe.db.get_value(
				"Salary Detail",
				{
					"parent": salary_structure,
					"parentfield": "earnings",
					"salary_component": "Basic Salary",
				},
				"amount",
			)
			total += amount or 0
		return total

	def _get_total_gross_salary(self):
		from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
			get_assigned_salary_structure,
		)

		employees = frappe.get_all(
			"Employee",
			filters={"company": self.company, "status": "Active"},
			pluck="name",
		)
		total = 0
		for employee in employees:
			salary_structure = get_assigned_salary_structure(employee, self.period_start)
			if not salary_structure:
				continue
			amount = frappe.db.get_value(
				"Salary Detail",
				{
					"parent": salary_structure,
					"parentfield": "earnings",
					"salary_component": "Gross Salary",
				},
				"amount",
			)
			total += amount or 0
		return total
```

`hrms/payroll/doctype/egypt_statutory_fund/__init__.py` (empty file).

Note on `Martyrs' Families Fund`'s rate: the document states "0.0005 of
the monthly gross salaries" in the definitions table, which is 0.05% —
confirmed by cross-referencing the worked salary-distribution example
later in the same document (`docs/Payroll System.rtf.doc`, "Salary
Distribution Proposal" table): "Martyrs' Families Fund | 3.50 | 0.05%"
against a 7000 EGP gross salary (7000 × 0.0005 = 3.50 — exact match).
This rate is hardcoded as a module constant rather than added to `Egypt
Statutory Settings` in Task 1, since it's a fixed 0.05% not currently
exposed as a tunable field there — **flagged as a follow-up** if the
implementer wants it configurable like the other three funds (would
require one more `Egypt Statutory Settings` field + a Task 1 amendment);
not done here to avoid scope creep on a plan already touching that
doctype.

Note on `Social, Health and Cultural Services Fund`'s rate: the document
gives "8 L.E per employee annually" in the definitions table but "8 EGP /
16 EGP" (min/max) in the Special Funds table — **these are the same
number under two different framings** (a flat 8 EGP figure in one place,
an 8–16 EGP range in the other). This plan treats it as a bounded flat
rate (`min_value` used as the per-employee amount, `max_value` retained
as an upper configurable bound for future rate changes) rather than
guessing which of the two document mentions is authoritative — flagged,
not silently resolved by picking one number arbitrarily.

- [ ] **Step 5: Rewrite the test file's second test as an isolated-company test and add remaining cases**

Replace the `test_compute_counts_only_insured_active_employees_for_the_company`
test in `hrms/payroll/doctype/egypt_statutory_fund/test_egypt_statutory_fund.py`
with tests scoped to a dedicated test company, so headcount assertions
are deterministic regardless of how many employees other tests in the
same session have already created against the shared `_Test Company`:

```python
	def make_isolated_test_company(self, name_suffix):
		company_name = f"_Test Egypt Fund Co {name_suffix}"
		if frappe.db.exists("Company", company_name):
			return company_name
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": f"TEFC{name_suffix}",
				"default_currency": "EGP",
				"country": "Egypt",
			}
		).insert(ignore_if_duplicate=True)
		return company_name

	def test_compute_below_threshold_returns_zero_and_status_draft(self):
		company = self.make_isolated_test_company("1")
		employee = self.make_employee("egypt_fund_iso_1@example.com", company=company)
		frappe.db.set_value("Employee", employee, "social_insurance_number", "SI-101")

		fund = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Fund",
				"fund_type": "Social, Health and Cultural Services Fund",
				"company": company,
				"period_start": "2026-01-01",
				"period_end": "2026-01-31",
			}
		).insert()
		fund.compute()

		# only 1 insured employee exists in this dedicated company, well
		# below the fund's 20-employee threshold
		self.assertEqual(fund.insured_employee_count, 1)
		self.assertEqual(fund.computed_contribution, 0)
		self.assertEqual(fund.status, "Draft")

	def test_compute_applies_cultural_fund_min_value_per_insured_employee(self):
		company = self.make_isolated_test_company("2")
		for i in range(20):
			employee = self.make_employee(f"egypt_fund_iso_2_{i}@example.com", company=company)
			frappe.db.set_value("Employee", employee, "social_insurance_number", f"SI-2{i:02d}")

		fund = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Fund",
				"fund_type": "Social, Health and Cultural Services Fund",
				"company": company,
				"period_start": "2026-01-01",
				"period_end": "2026-01-31",
			}
		).insert()
		fund.compute()

		self.assertEqual(fund.insured_employee_count, 20)
		self.assertEqual(fund.min_value, 8)
		self.assertEqual(fund.status, "Computed")
		self.assertEqual(fund.computed_contribution, 8 * 20)
```

Note: `test_compute_applies_cultural_fund_min_value_per_insured_employee`
creates exactly 20 insured employees (the fund's own headcount
threshold) in a fresh company, so `compute()`'s real headcount-check
branch and rate-application branch are both exercised end-to-end through
the public `compute()` method — no monkeypatching or reaching into
private methods needed.

- [ ] **Step 6: Run tests to verify they pass**

Run: `bench --site test_site run-tests --app hrms --module hrms.payroll.doctype.egypt_statutory_fund.test_egypt_statutory_fund`
Expected: PASS (4 tests: original below-threshold test from Step 1, raw
counting helper from Step 1, the isolated-company below-threshold test,
and the isolated-company rate-application test — both from Step 5). If
no bench, report NOT EXECUTED with static-read rationale — trace
`compute()` and `_apply_fund_rate()` by hand against each assertion.

- [ ] **Step 7: Lint**

```bash
pre-commit run --files hrms/payroll/doctype/egypt_statutory_fund/
```

- [ ] **Step 8: Commit**

```bash
git add hrms/payroll/doctype/egypt_statutory_fund/
git commit -m "feat(egypt): add Egypt Statutory Fund doctype with compute() for statutory fund contributions"
```

---

## Task 3: Whole-area integration test

**Files:**
- Create: `hrms/regional/egypt/test_integration_area4.py`

**Interfaces:**
- Consumes: everything from Tasks 1-2.
- Produces: none — final verification task for Area 4.

- [ ] **Step 1: Write the integration test**

`hrms/regional/egypt/test_integration_area4.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.payroll.doctype.egypt_statutory_fund.egypt_statutory_fund import FUND_HEADCOUNT_THRESHOLDS
from hrms.tests.utils import HRMSTestSuite


class TestEgyptArea4Integration(HRMSTestSuite):
	def test_all_four_fund_types_are_computable(self):
		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"effective_from": "2026-01-01",
				"emergency_relief_fund_rate": 1,
				"cultural_services_fund_min": 8,
				"cultural_services_fund_max": 16,
				"training_fund_rate": 0.25,
				"training_fund_min": 10,
				"training_fund_max": 30,
			}
		).insert(ignore_if_duplicate=True)

		employee = self.make_employee("egypt_area4_integration@example.com")
		company = frappe.db.get_value("Employee", employee, "company")

		for fund_type in FUND_HEADCOUNT_THRESHOLDS:
			fund = frappe.get_doc(
				{
					"doctype": "Egypt Statutory Fund",
					"fund_type": fund_type,
					"company": company,
					"period_start": "2026-01-01",
					"period_end": "2026-01-31",
				}
			).insert()
			fund.compute()
			self.assertIn(fund.status, ("Draft", "Computed"))
```

- [ ] **Step 2: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_integration_area4`
Expected: PASS. If no bench, report NOT EXECUTED with a static-read
rationale tracing `compute()` against each fund type's branch in
`_apply_fund_rate()`.

- [ ] **Step 3: Lint**

```bash
pre-commit run --files hrms/regional/egypt/test_integration_area4.py
```

- [ ] **Step 4: Commit**

```bash
git add hrms/regional/egypt/test_integration_area4.py
git commit -m "test(egypt): verify all four statutory fund types compute end-to-end"
```

---

## Self-Review Notes

**Spec coverage (spec §7, Area 4), cross-checked against the source
document directly:**
- `Egypt Statutory Fund` doctype with all fields spec §7 lists → Task 2.
- `compute()` whitelisted method: headcount check, rate/min/max
  application, `computed_contribution` → Task 2.
- Fund rates sourced from `Egypt Statutory Settings` (spec §7's
  `rate_or_amount` "sourced from Egypt Statutory Settings" note) → Task 1
  extends that doctype rather than hardcoding rates in the new one,
  except Martyrs' Families Fund's 0.05% (flagged as a follow-up
  configurability gap in Task 2's notes, with the exact source-document
  cross-reference that confirms the 0.05% figure).
- Standalone compliance data, no GL/Salary Slip posting (spec §9) →
  confirmed nowhere in Task 2's `compute()` does it touch `GL Entry` or
  `Salary Slip`.
- Whole-area wiring verified end-to-end → Task 3.

**Explicitly deferred / flagged, not silently dropped:**
- Martyrs' Families Fund rate is hardcoded rather than a configurable
  `Egypt Statutory Settings` field (Task 2 note) — deliberate scope
  limit, not an oversight; exact document cross-reference given.
- Cultural Services Fund's "8 EGP flat" vs. "8-16 EGP range" ambiguity in
  the source document is resolved by treating `min_value` as the
  effective per-employee rate and `max_value` as a configurable ceiling,
  flagged rather than silently picking one figure (Task 2 note).
- This plan does **not** wire fund computation into any scheduler/cron
  job or Payroll Entry — the spec explicitly frames this as a
  standalone screen the HR team runs manually per period (matching how
  the source document separates "Special Funds Calculation Screen" from
  per-employee payroll), so no `scheduler_events` hook is added. If
  automatic monthly/quarterly computation is wanted later, that's a
  distinct follow-up (a new `hrms/hooks.py:scheduler_events` entry
  calling `compute()` for each active fund-type/company pair), not
  attempted here since the spec doesn't request it.

**Placeholder scan:** No vague "TBD"/"add error handling" left. Both
data-value ambiguities above have a concrete resolution and an explicit
flag, not a silent guess.

**Type/name consistency:** `EgyptStatutoryFund.compute()` (Task 2)
matches its Task 2 test calls (`fund.compute()`) and Task 3's integration
test call exactly. `FUND_HEADCOUNT_THRESHOLDS` (module-level dict, Task
2) matches its Task 2 Step 5 test import and Task 3's integration test
import (`from hrms.payroll.doctype.egypt_statutory_fund.egypt_statutory_fund
import FUND_HEADCOUNT_THRESHOLDS`) exactly. `get_active_settings` (Task
2's `_apply_fund_rate`) matches the Area 3 plan's existing signature
`get_active_settings(date, company=None)` exactly — confirmed against
`hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.py`
(already implemented, not re-defined by this plan).
