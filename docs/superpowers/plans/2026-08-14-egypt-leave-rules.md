# Egypt Leave Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Egypt's leave entitlements (tenure-tiered Regular/Casual leave,
once-per-career Hajj leave, minimum-tenure and insurance-required
eligibility gates, tiered-payout Sick Leave) to `hrms/regional/egypt/`,
reusing HRMS's existing `Leave Type` / `Leave Policy` / `Leave Policy
Assignment` / `Leave Application` / `Leave Allocation` engines, extended
only where a genuine gap exists.

**Architecture:** Two new optional fields on `Leave Type`
(`min_years_of_service`, `max_lifetime_allocations`) gate allocation/
application the same way the existing `applicable_after` field already
does, via one new call-out each in `Leave Policy Assignment.
grant_leave_alloc_for_employee()` and `Leave Application.validate()`. A new
child doctype `Leave Type Service Tier` on `Leave Type` lets
tenure-dependent leave types (Regular, Casual) declare a
years-of-service → days table, read from a new call-out in `Leave Policy
Assignment.create_leave_allocation()` in place of the flat
`leave_policy_detail.annual_allocation` when tiers are configured. Sick
Leave's tiered payout (100% for 90 days, 85% for the next 90, 75% for the
next 90, within a rolling 3-year cycle) is **out of scope for this plan**
(see Task 6) because it requires new payroll-time consumption-tracking
that doesn't exist yet in `salary_slip.py`'s LWP/PPL machinery — Task 6
adds the entitlement as a flat non-tiered `is_ppl` leave type (100% paid,
correct up to the first 90 days) and files the tiered-decay gap explicitly
rather than building fabricated payroll logic.

**Tech Stack:** Frappe Framework doctype JSON + Python controllers,
`create_custom_fields`/fixture `insert(ignore_if_duplicate=True)`, one new
child doctype, `bench run-tests`.

**Spec:** `docs/superpowers/specs/2026-08-13-egypt-payroll-localization-design.md`
(Section 5 — Area 2: Leave Rules), cross-checked directly against
`docs/Payroll System.rtf.doc` ("Second Time and Attendance Monitoring"
section) during planning on 2026-08-14.

## Global Constraints

- Custom field `fieldname`s use **no `custom_` prefix**, consistent with
  Area 1/3 (`hrms/regional/egypt/setup.py`).
- New doctypes belong to the `HR` module (`Leave Type`, `Leave Policy
  Detail`, `Leave Application`, `Leave Allocation` all live under `HR` per
  `hrms/modules.txt`; this plan's one new child doctype
  `Leave Type Service Tier` follows suit).
- Tab indentation, double quotes, line length 110 (ruff,
  `pyproject.toml`). No bench/pre-commit/ruff binary was available in the
  session that wrote this plan — same constraint noted in the Area 3 plan.
  Trace changes by hand against each test's assertions if no bench is
  available at implementation time; do not fabricate PASS output.
- Tests live next to the code as `test_*.py`, extending
  `hrms.tests.utils.HRMSTestSuite` for anything needing `make_employee`,
  or `frappe.tests.IntegrationTestCase` for pure-function/fixture tests
  (matches `hrms/regional/egypt/test_utils.py`'s existing pattern from
  Area 3).
- Commit messages follow Conventional Commits — `feat(egypt): ...`,
  `test(egypt): ...`.
- All new fields on core doctypes (`Leave Type`, `Leave Application`) are
  **additive and optional** — every new call-out has a "field not set /
  table empty → behave exactly as today" fallback, so non-Egypt companies
  see zero behavior change. This is a repo convention (see the Area 3
  plan's `regional_overrides` additive-only rule and the spec's own
  framing in §5 "used only when populated").
- **Confirmed against current code** (read during planning, 2026-08-14):
  - `Leave Policy Detail` (`hrms/hr/doctype/leave_policy_detail/leave_policy_detail.json`)
    has exactly two fields: `leave_type` (Link), `annual_allocation`
    (Float, required). No tier table exists yet.
  - `Leave Policy Assignment.grant_leave_alloc_for_employee()`
    (`hrms/hr/doctype/leave_policy_assignment/leave_policy_assignment.py:109-133`)
    loops `leave_policy.leave_policy_details`, calling `self.create_leave_allocation(
    leave_policy_detail.annual_allocation, leave_details, date_of_joining)` per row
    (line 123-127) — this is the exact call site where a tenure-tiered
    lookup must replace the flat `leave_policy_detail.annual_allocation`
    value before it's passed in.
  - `create_leave_allocation(self, annual_allocation, leave_details, date_of_joining)`
    (`leave_policy_assignment.py:135-185`) receives `annual_allocation` as
    a plain number and passes it straight into `get_new_leaves()` — the
    tier resolution must happen in the caller
    (`grant_leave_alloc_for_employee`), computing an effective
    `annual_allocation` value before calling `create_leave_allocation`,
    not inside it — keeps `create_leave_allocation`'s signature unchanged.
  - `Leave Type` (`hrms/hr/doctype/leave_type/leave_type.json`) already
    has `is_ppl` (Check) + `fraction_of_daily_salary_per_leave` (Float) —
    **confirmed this is a single fixed fraction applied to every day of
    that leave type taken in a payroll period** (used in
    `salary_slip.py:766-804` `calculate_lwp_or_ppl_based_on_leave_application()`
    and `:840-889` `calculate_lwp_ppl_and_absent_days_based_on_attendance()`,
    both reading `leave.fraction_of_daily_salary_per_leave` per-record with
    no cumulative-days-consumed tracking anywhere). **This directly
    contradicts the spec's §5 framing of tiered sick leave as "extending
    the existing `is_ppl` mechanism"** — there is no existing mechanism to
    extend for the *tiered/decaying* part; only the "some leave types pay
    less than 100%" part is reusable. See Task 6 for the scoped-down
    approach this plan actually takes.
  - `Leave Application.validate()`
    (`hrms/hr/doctype/leave_application/leave_application.py:109-126`)
    already calls `self.validate_applicable_after()` (line 123), whose
    body (`leave_application.py:188-200`) is the exact existing pattern
    for a min-tenure gate: reads `leave_type.applicable_after` (Int,
    calendar days since date of joining), throws if the employee hasn't
    reached it yet. `min_years_of_service` (Task 2 of this plan) is a new
    sibling field + sibling validation method following this identical
    shape, not a new mechanism.
  - **No existing "once per career" / "max N lifetime allocations"
    mechanism exists anywhere** in `leave_application.py`,
    `leave_allocation.py`, or `leave_policy_assignment.py` (confirmed via
    full-file read + repo-wide grep for "lifetime", "once", "career" —
    zero hits outside unrelated `set_only_once` framework metadata this
    plan does not touch). Task 3 adds this from scratch.
  - `Leave Allocation` (`hrms/hr/doctype/leave_allocation/leave_allocation.json`)
    is submittable, has `employee` (Link), `leave_type` (Link), `from_date`/
    `to_date` (Date) — sufficient to count prior allocations via
    `frappe.db.count("Leave Allocation", {"employee": ..., "leave_type": ...,
    "docstatus": 1})` for both the lifetime-once gate (Task 3) and the
    Sick Leave 3-year-cycle boundary (Task 6, scoped down — see there).
  - `social_insurance_number` (Data field, Employee, no `custom_` prefix)
    already exists from Area 1 (`hrms/regional/egypt/setup.py:116`),
    confirmed present — Task 4's insurance-required gate reads this field
    directly, no new field needed.
  - `Leave Type` permissions
    (`hrms/hr/doctype/leave_type/leave_type.json:273-300`): `HR User` +
    `HR Manager` full CRUD, `Employee` read-only. New child doctype in
    Task 1 follows the same `istable: 1`, no independent `permissions`
    block (matches `Leave Policy Detail`'s empty `"permissions": []`,
    since child table permissions inherit from the parent).

---

## Task 1: `Leave Type Service Tier` child doctype + `Leave Type.service_tiers`

**Files:**
- Create: `hrms/hr/doctype/leave_type_service_tier/__init__.py`
- Create: `hrms/hr/doctype/leave_type_service_tier/leave_type_service_tier.json`
- Create: `hrms/hr/doctype/leave_type_service_tier/leave_type_service_tier.py`
- Modify: `hrms/hr/doctype/leave_type/leave_type.json` (add `service_tiers`
  Table field)
- Create: `hrms/hr/doctype/leave_type/test_leave_type_service_tier.py`

**Interfaces:**
- Produces: child doctype `Leave Type Service Tier` with fields
  `min_years` (Int, required, non-negative), `max_years` (Int, optional —
  empty means "and above"), `days` (Float, required, non-negative).
  Attached to `Leave Type` as table field `service_tiers`. Consumed by
  Task 2's `get_tiered_annual_allocation(leave_type, years_of_service) ->
  float | None` helper (returns `None` when `service_tiers` is empty, so
  callers fall back to the flat `Leave Policy Detail.annual_allocation`).

- [ ] **Step 1: Write the failing test**

`hrms/hr/doctype/leave_type/test_leave_type_service_tier.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestLeaveTypeServiceTier(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_leave_type_accepts_service_tiers(self):
		doc = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Egypt Regular Leave",
				"service_tiers": [
					{"min_years": 0, "max_years": 1, "days": 15},
					{"min_years": 1, "max_years": None, "days": 21},
				],
			}
		).insert()

		self.assertEqual(len(doc.service_tiers), 2)
		self.assertEqual(doc.service_tiers[0].days, 15)
		self.assertEqual(doc.service_tiers[1].max_years, None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.doctype.leave_type.test_leave_type_service_tier`
Expected: FAIL — `Unknown field 'service_tiers' in Leave Type` (child
table field doesn't exist yet). If no bench, report NOT EXECUTED with
rationale — the field is absent from the current
`hrms/hr/doctype/leave_type/leave_type.json` field list (confirmed during
planning, see Global Constraints), so the insert would raise.

- [ ] **Step 3: Create the child doctype JSON**

`hrms/hr/doctype/leave_type_service_tier/leave_type_service_tier.json`:

```json
{
 "actions": [],
 "creation": "2026-08-14 00:00:00.000000",
 "doctype": "DocType",
 "editable_grid": 1,
 "engine": "InnoDB",
 "field_order": [
  "min_years",
  "max_years",
  "days"
 ],
 "fields": [
  {
   "fieldname": "min_years",
   "fieldtype": "Int",
   "in_list_view": 1,
   "label": "Min Years of Service",
   "non_negative": 1,
   "reqd": 1
  },
  {
   "description": "Leave empty for \"and above\" (no upper bound)",
   "fieldname": "max_years",
   "fieldtype": "Int",
   "in_list_view": 1,
   "label": "Max Years of Service",
   "non_negative": 1
  },
  {
   "fieldname": "days",
   "fieldtype": "Float",
   "in_list_view": 1,
   "label": "Days",
   "non_negative": 1,
   "reqd": 1
  }
 ],
 "istable": 1,
 "links": [],
 "modified": "2026-08-14 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "HR",
 "name": "Leave Type Service Tier",
 "owner": "Administrator",
 "permissions": [],
 "sort_field": "creation",
 "sort_order": "DESC",
 "states": [],
 "track_changes": 1
}
```

`hrms/hr/doctype/leave_type_service_tier/leave_type_service_tier.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe.model.document import Document


class LeaveTypeServiceTier(Document):
	pass
```

`hrms/hr/doctype/leave_type_service_tier/__init__.py` (empty file).

- [ ] **Step 4: Add the `service_tiers` field to `Leave Type`**

In `hrms/hr/doctype/leave_type/leave_type.json`:

Add `"service_tiers"` to `field_order` right after `"earned_leave"` (end
of the Earned Leave section, before `"is_earned_leave"` — actually place
it as its own section for clarity: insert `"service_tiers_section"` and
`"service_tiers"` right before `"limits_tab"` in the `field_order` array).

Add to the `fields` array, right before the `limits_tab` Tab Break entry:

```json
  {
   "collapsible": 1,
   "fieldname": "service_tiers_section",
   "fieldtype": "Section Break",
   "label": "Service Tiers"
  },
  {
   "description": "When rows exist here, annual allocation is looked up by the employee's years of service instead of using a flat Leave Policy Detail amount.",
   "fieldname": "service_tiers",
   "fieldtype": "Table",
   "label": "Service Tiers",
   "options": "Leave Type Service Tier"
  },
```

Update `field_order` to insert `"service_tiers_section"` and
`"service_tiers"` immediately before the existing `"limits_tab"` entry.

- [ ] **Step 5: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.doctype.leave_type.test_leave_type_service_tier`
Expected: PASS. If no bench, report NOT EXECUTED with a static-read
rationale (trace the JSON field addition against the test's field access).

- [ ] **Step 6: Lint**

```bash
pre-commit run --files hrms/hr/doctype/leave_type_service_tier/leave_type_service_tier.json hrms/hr/doctype/leave_type_service_tier/leave_type_service_tier.py hrms/hr/doctype/leave_type_service_tier/__init__.py hrms/hr/doctype/leave_type/leave_type.json hrms/hr/doctype/leave_type/test_leave_type_service_tier.py
```

- [ ] **Step 7: Commit**

```bash
git add hrms/hr/doctype/leave_type_service_tier/ hrms/hr/doctype/leave_type/leave_type.json hrms/hr/doctype/leave_type/test_leave_type_service_tier.py
git commit -m "feat(hr): add optional service-tier table to Leave Type for tenure-based accrual"
```

---

## Task 2: Tenure-tiered accrual lookup wired into `Leave Policy Assignment`

**Files:**
- Modify: `hrms/hr/doctype/leave_policy_assignment/leave_policy_assignment.py`
- Create: `hrms/hr/doctype/leave_policy_assignment/test_leave_policy_assignment_egypt.py`

**Interfaces:**
- Consumes: `Leave Type.service_tiers` (Task 1).
- Produces: `hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment.get_tiered_annual_allocation(leave_type_name, years_of_service) -> float | None`
  (module-level function; `None` means "no tiers configured, use flat
  value"). Called from `grant_leave_alloc_for_employee()` before invoking
  `create_leave_allocation()`.

- [ ] **Step 1: Write the failing test**

`hrms/hr/doctype/leave_policy_assignment/test_leave_policy_assignment_egypt.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
	get_tiered_annual_allocation,
)


class TestTieredAnnualAllocation(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_returns_none_when_no_tiers_configured(self):
		leave_type = frappe.get_doc(
			{"doctype": "Leave Type", "leave_type_name": "Test No Tiers Leave"}
		).insert()

		self.assertIsNone(get_tiered_annual_allocation(leave_type.name, years_of_service=5))

	def test_returns_matching_tier_days(self):
		leave_type = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Tiered Leave",
				"service_tiers": [
					{"min_years": 0, "max_years": 1, "days": 15},
					{"min_years": 1, "max_years": 10, "days": 21},
					{"min_years": 10, "max_years": None, "days": 30},
				],
			}
		).insert()

		self.assertEqual(get_tiered_annual_allocation(leave_type.name, years_of_service=0), 15)
		self.assertEqual(get_tiered_annual_allocation(leave_type.name, years_of_service=1), 21)
		self.assertEqual(get_tiered_annual_allocation(leave_type.name, years_of_service=9), 21)
		self.assertEqual(get_tiered_annual_allocation(leave_type.name, years_of_service=10), 30)
		self.assertEqual(get_tiered_annual_allocation(leave_type.name, years_of_service=100), 30)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.doctype.leave_policy_assignment.test_leave_policy_assignment_egypt`
Expected: FAIL — `ImportError: cannot import name 'get_tiered_annual_allocation'`.
If no bench, report NOT EXECUTED with rationale.

- [ ] **Step 3: Add `get_tiered_annual_allocation` and wire it into `grant_leave_alloc_for_employee`**

In `hrms/hr/doctype/leave_policy_assignment/leave_policy_assignment.py`,
add after `get_leave_type_details()` (end of file):

```python
def get_tiered_annual_allocation(leave_type_name, years_of_service):
	"""Return the annual allocation from Leave Type.service_tiers matching
	years_of_service, or None if no tiers are configured (caller should
	fall back to the flat Leave Policy Detail.annual_allocation)."""
	tiers = frappe.get_all(
		"Leave Type Service Tier",
		filters={"parent": leave_type_name, "parenttype": "Leave Type"},
		fields=["min_years", "max_years", "days"],
	)
	if not tiers:
		return None

	for tier in tiers:
		if years_of_service < tier.min_years:
			continue
		if tier.max_years is not None and years_of_service >= tier.max_years:
			continue
		return tier.days

	return None
```

Modify `grant_leave_alloc_for_employee` (currently at line 109-133) —
replace the loop body's call to `self.create_leave_allocation(
leave_policy_detail.annual_allocation, ...)` with a resolved value:

```python
	def grant_leave_alloc_for_employee(self):
		if self.leaves_allocated:
			frappe.throw(_("Leave already have been assigned for this Leave Policy Assignment"))
		else:
			leave_allocations = {}
			leave_type_details = get_leave_type_details()

			leave_policy = frappe.get_doc("Leave Policy", self.leave_policy)
			date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")
			years_of_service = date_diff(getdate(self.effective_from), date_of_joining) / 365.25

			for leave_policy_detail in leave_policy.leave_policy_details:
				leave_details = leave_type_details.get(leave_policy_detail.leave_type)

				if not leave_details.is_lwp:
					tiered_allocation = get_tiered_annual_allocation(
						leave_policy_detail.leave_type, years_of_service
					)
					annual_allocation = (
						tiered_allocation
						if tiered_allocation is not None
						else leave_policy_detail.annual_allocation
					)
					leave_allocation, new_leaves_allocated = self.create_leave_allocation(
						annual_allocation,
						leave_details,
						date_of_joining,
					)
					leave_allocations[leave_details.name] = {
						"name": leave_allocation,
						"leaves": new_leaves_allocated,
					}
			self.db_set("leaves_allocated", 1)
			return leave_allocations
```

Note: `date_diff` and `getdate` are already imported at the top of this
file (`leave_policy_assignment.py:15,25`) — no new imports needed.

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.doctype.leave_policy_assignment.test_leave_policy_assignment_egypt`
Expected: PASS (2 tests). If no bench, report NOT EXECUTED with
static-read rationale.

- [ ] **Step 5: Run the existing Leave Policy Assignment test suite to confirm no regression**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.doctype.leave_policy_assignment.test_leave_policy_assignment`
Expected: PASS, unchanged — every existing test uses `Leave Type` records
with no `service_tiers` rows, so `get_tiered_annual_allocation` returns
`None` for all of them and `annual_allocation` resolves to the original
flat value exactly as before. If no bench, report NOT EXECUTED but note
this reasoning explicitly (it's the additive-only correctness argument,
not just an execution gap).

- [ ] **Step 6: Lint**

```bash
pre-commit run --files hrms/hr/doctype/leave_policy_assignment/leave_policy_assignment.py hrms/hr/doctype/leave_policy_assignment/test_leave_policy_assignment_egypt.py
```

- [ ] **Step 7: Commit**

```bash
git add hrms/hr/doctype/leave_policy_assignment/leave_policy_assignment.py hrms/hr/doctype/leave_policy_assignment/test_leave_policy_assignment_egypt.py
git commit -m "feat(hr): resolve tenure-tiered annual allocation in Leave Policy Assignment"
```

---

## Task 3: Minimum-tenure and lifetime-allocation-count gating on `Leave Type`

**Files:**
- Modify: `hrms/hr/doctype/leave_type/leave_type.json` (add
  `min_years_of_service`, `max_lifetime_allocations` fields)
- Modify: `hrms/hr/doctype/leave_application/leave_application.py`
- Create: `hrms/hr/doctype/leave_application/test_leave_application_egypt.py`

**Interfaces:**
- Produces: `Leave Type.min_years_of_service` (Int, default 0 — leave
  application blocked if employee's tenure at `from_date` is below this).
  `Leave Type.max_lifetime_allocations` (Int, default 0 meaning
  unlimited — blocks a **new Leave Allocation** once
  `frappe.db.count("Leave Allocation", {"employee": ..., "leave_type": ...,
  "docstatus": 1})` reaches this count). Two new methods on
  `LeaveApplication`: `validate_min_years_of_service()` (mirrors
  `validate_applicable_after`, called from `validate()`).
  `max_lifetime_allocations` is enforced at allocation time, not
  application time — see Step 3's placement in
  `leave_policy_assignment.py`, not `leave_application.py` (Hajj is
  granted via allocation, not via a Leave Application against an existing
  balance being unlimited).

- [ ] **Step 1: Write the failing test**

`hrms/hr/doctype/leave_application/test_leave_application_egypt.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, getdate

from hrms.tests.utils import HRMSTestSuite


class TestLeaveApplicationMinYearsOfService(HRMSTestSuite):
	def test_blocks_application_before_min_years_of_service(self):
		leave_type = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Hajj-Style Leave",
				"min_years_of_service": 5,
				"allow_negative": 1,
			}
		).insert()

		employee = self.make_employee("egypt_hajj_short_tenure@example.com")
		frappe.db.set_value("Employee", employee, "date_of_joining", add_days(getdate(), -365))

		application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": leave_type.name,
				"from_date": getdate(),
				"to_date": add_days(getdate(), 2),
				"company": frappe.db.get_value("Employee", employee, "company"),
			}
		)
		with self.assertRaises(frappe.ValidationError):
			application.insert()

	def test_allows_application_after_min_years_of_service(self):
		leave_type = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Hajj-Style Leave 2",
				"min_years_of_service": 5,
				"allow_negative": 1,
			}
		).insert()

		employee = self.make_employee("egypt_hajj_long_tenure@example.com")
		frappe.db.set_value("Employee", employee, "date_of_joining", add_days(getdate(), -365 * 6))

		application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": leave_type.name,
				"from_date": getdate(),
				"to_date": add_days(getdate(), 2),
				"company": frappe.db.get_value("Employee", employee, "company"),
			}
		)
		# should not raise on the min-years check (other validations still apply
		# via HRMSTestSuite's seeded holiday/leave-period fixtures)
		application.insert()
```

Note: `allow_negative=1` on the test Leave Type sidesteps
`validate_balance_leaves()` (an earlier check in `validate()`, since no
`Leave Allocation` exists for these ad-hoc test leave types) so the test
isolates the new `min_years_of_service` check specifically.

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.doctype.leave_application.test_leave_application_egypt`
Expected: FAIL — `test_blocks_application_before_min_years_of_service`
fails because `min_years_of_service` doesn't exist as a Leave Type field
yet (insert of the Leave Type itself raises `Unknown field`). If no
bench, report NOT EXECUTED with rationale (field absent from current
`leave_type.json`, confirmed during planning).

- [ ] **Step 3: Add the fields and validation method**

In `hrms/hr/doctype/leave_type/leave_type.json`, add to `fields` (near
`applicable_after`, in the same section) and to `field_order` right after
`"applicable_after"`:

```json
  {
   "default": "0",
   "description": "Leave cannot be applied for until the employee has completed this many years of service (in addition to any Allow Leave Application After day-based gate above).",
   "fieldname": "min_years_of_service",
   "fieldtype": "Int",
   "label": "Minimum Years of Service Required",
   "non_negative": 1
  },
```

In `hrms/hr/doctype/leave_application/leave_application.py`, modify
`validate()` (currently line 109-126) to add one call after
`self.validate_applicable_after()`:

```python
	def validate(self):
		validate_active_employee(self.employee)
		set_employee_name(self)
		self.validate_dates()
		self.validate_balance_leaves()
		self.validate_leave_overlap()
		self.validate_max_days()
		self.show_block_day_warning()
		self.validate_block_days()
		self.validate_salary_processed_days()
		self.validate_attendance()
		self.set_half_day_date()
		if frappe.db.get_value("Leave Type", self.leave_type, "is_optional_leave"):
			self.validate_optional_leave()
		self.validate_applicable_after()
		self.validate_min_years_of_service()
		self.validate_for_self_approval()
		self.validate_leave_approver()
		self.set_leave_approver_name()
```

Add the new method right after `validate_applicable_after`
(`leave_application.py:188-200`):

```python
	def validate_min_years_of_service(self):
		if not self.leave_type:
			return

		min_years_of_service = frappe.db.get_value("Leave Type", self.leave_type, "min_years_of_service")
		if not min_years_of_service:
			return

		date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")
		if not date_of_joining:
			return

		years_of_service = date_diff(getdate(self.from_date), date_of_joining) / 365.25
		if years_of_service < min_years_of_service:
			frappe.throw(
				_("{0} requires at least {1} years of service").format(
					self.leave_type, min_years_of_service
				)
			)
```

`date_diff` and `getdate` are confirmed already imported at the top of
`leave_application.py` (used elsewhere in the same file, e.g.
`validate_applicable_after`'s own `date_diff` call at line 193).

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.doctype.leave_application.test_leave_application_egypt`
Expected: PASS (2 tests). If no bench, report NOT EXECUTED with
static-read rationale.

- [ ] **Step 5: Add `max_lifetime_allocations` field and enforcement point**

In `hrms/hr/doctype/leave_type/leave_type.json`, add (same section,
`field_order` right after `min_years_of_service`):

```json
  {
   "default": "0",
   "description": "Maximum number of times this leave type can ever be allocated to one employee (0 = unlimited). E.g. Hajj leave: 1.",
   "fieldname": "max_lifetime_allocations",
   "fieldtype": "Int",
   "label": "Maximum Lifetime Allocations",
   "non_negative": 1
  },
```

In `hrms/hr/doctype/leave_policy_assignment/leave_policy_assignment.py`
(Task 2 already modified `grant_leave_alloc_for_employee` — extend the
same loop body), add the lifetime-count check right before the
`create_leave_allocation` call:

```python
			for leave_policy_detail in leave_policy.leave_policy_details:
				leave_details = leave_type_details.get(leave_policy_detail.leave_type)

				if not leave_details.is_lwp:
					if self._lifetime_allocation_limit_reached(leave_policy_detail.leave_type):
						continue

					tiered_allocation = get_tiered_annual_allocation(
						leave_policy_detail.leave_type, years_of_service
					)
					annual_allocation = (
						tiered_allocation
						if tiered_allocation is not None
						else leave_policy_detail.annual_allocation
					)
					leave_allocation, new_leaves_allocated = self.create_leave_allocation(
						annual_allocation,
						leave_details,
						date_of_joining,
					)
					leave_allocations[leave_details.name] = {
						"name": leave_allocation,
						"leaves": new_leaves_allocated,
					}
```

Add the new method to the `LeavePolicyAssignment` class, right after
`grant_leave_alloc_for_employee`:

```python
	def _lifetime_allocation_limit_reached(self, leave_type):
		max_lifetime_allocations = frappe.db.get_value(
			"Leave Type", leave_type, "max_lifetime_allocations"
		)
		if not max_lifetime_allocations:
			return False

		existing_count = frappe.db.count(
			"Leave Allocation",
			{"employee": self.employee, "leave_type": leave_type, "docstatus": 1},
		)
		return existing_count >= max_lifetime_allocations
```

- [ ] **Step 6: Write and run the lifetime-allocation test**

Append to `hrms/hr/doctype/leave_policy_assignment/test_leave_policy_assignment_egypt.py`:

```python
from hrms.tests.utils import HRMSTestSuite


class TestLifetimeAllocationLimit(HRMSTestSuite):
	def test_second_allocation_blocked_after_lifetime_limit(self):
		leave_type = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Once-Per-Career Leave",
				"max_lifetime_allocations": 1,
			}
		).insert()
		employee = self.make_employee("egypt_lifetime_once@example.com")

		frappe.get_doc(
			{
				"doctype": "Leave Allocation",
				"employee": employee,
				"leave_type": leave_type.name,
				"from_date": "2020-01-01",
				"to_date": "2020-12-31",
				"new_leaves_allocated": 30,
			}
		).submit()

		assignment = frappe.get_doc(
			doctype="Leave Policy Assignment",
			employee=employee,
		)
		self.assertTrue(assignment._lifetime_allocation_limit_reached(leave_type.name))
```

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.doctype.leave_policy_assignment.test_leave_policy_assignment_egypt`
Expected: PASS (3 tests total from Task 2 + this). If no bench, report
NOT EXECUTED with static-read rationale.

- [ ] **Step 7: Lint**

```bash
pre-commit run --files hrms/hr/doctype/leave_type/leave_type.json hrms/hr/doctype/leave_application/leave_application.py hrms/hr/doctype/leave_application/test_leave_application_egypt.py hrms/hr/doctype/leave_policy_assignment/leave_policy_assignment.py hrms/hr/doctype/leave_policy_assignment/test_leave_policy_assignment_egypt.py
```

- [ ] **Step 8: Commit**

```bash
git add hrms/hr/doctype/leave_type/leave_type.json hrms/hr/doctype/leave_application/leave_application.py hrms/hr/doctype/leave_application/test_leave_application_egypt.py hrms/hr/doctype/leave_policy_assignment/leave_policy_assignment.py hrms/hr/doctype/leave_policy_assignment/test_leave_policy_assignment_egypt.py
git commit -m "feat(hr): add minimum-tenure and lifetime-allocation-count gating to Leave Type"
```

---

## Task 4: Insurance-required eligibility gate

**Files:**
- Modify: `hrms/hr/doctype/leave_type/leave_type.json` (add
  `requires_insurance` field)
- Modify: `hrms/hr/doctype/leave_application/leave_application.py`
- Modify: `hrms/hr/doctype/leave_application/test_leave_application_egypt.py`

**Interfaces:**
- Consumes: `Employee.social_insurance_number` (existing Area 1 custom
  field, confirmed no `custom_` prefix).
- Produces: `Leave Type.requires_insurance` (Check, default 0). New
  `LeaveApplication.validate_requires_insurance()` method, called from
  `validate()` right after `validate_min_years_of_service()`.

- [ ] **Step 1: Write the failing test**

Append to `hrms/hr/doctype/leave_application/test_leave_application_egypt.py`:

```python
class TestLeaveApplicationRequiresInsurance(HRMSTestSuite):
	def test_blocks_application_when_employee_not_insured(self):
		leave_type = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Insured-Only Leave",
				"requires_insurance": 1,
				"allow_negative": 1,
			}
		).insert()

		employee = self.make_employee("egypt_uninsured@example.com")
		frappe.db.set_value("Employee", employee, "social_insurance_number", "")

		application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": leave_type.name,
				"from_date": getdate(),
				"to_date": add_days(getdate(), 2),
				"company": frappe.db.get_value("Employee", employee, "company"),
			}
		)
		with self.assertRaises(frappe.ValidationError):
			application.insert()

	def test_allows_application_when_employee_insured(self):
		leave_type = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Insured-Only Leave 2",
				"requires_insurance": 1,
				"allow_negative": 1,
			}
		).insert()

		employee = self.make_employee("egypt_insured@example.com")
		frappe.db.set_value("Employee", employee, "social_insurance_number", "SI-12345")

		application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": leave_type.name,
				"from_date": getdate(),
				"to_date": add_days(getdate(), 2),
				"company": frappe.db.get_value("Employee", employee, "company"),
			}
		)
		application.insert()
```

`HRMSTestSuite` and `frappe`/`getdate`/`add_days` are already imported at
the top of this test file from Task 3 — no new imports needed.

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.doctype.leave_application.test_leave_application_egypt`
Expected: FAIL on the two new tests — `requires_insurance` field doesn't
exist on `Leave Type` yet. If no bench, report NOT EXECUTED with
rationale.

- [ ] **Step 3: Add the field and validation method**

In `hrms/hr/doctype/leave_type/leave_type.json`, add to `fields` and
`field_order` (right after `max_lifetime_allocations` from Task 3):

```json
  {
   "default": "0",
   "description": "Leave can only be applied for by employees with a Social Insurance Number recorded on their Employee record.",
   "fieldname": "requires_insurance",
   "fieldtype": "Check",
   "label": "Requires Social Insurance"
  },
```

In `hrms/hr/doctype/leave_application/leave_application.py`, extend
`validate()`:

```python
		self.validate_applicable_after()
		self.validate_min_years_of_service()
		self.validate_requires_insurance()
		self.validate_for_self_approval()
```

Add the method after `validate_min_years_of_service` (added in Task 3):

```python
	def validate_requires_insurance(self):
		if not self.leave_type:
			return

		requires_insurance = frappe.db.get_value("Leave Type", self.leave_type, "requires_insurance")
		if not requires_insurance:
			return

		social_insurance_number = frappe.db.get_value(
			"Employee", self.employee, "social_insurance_number"
		)
		if not social_insurance_number:
			frappe.throw(_("{0} requires the employee to have a Social Insurance Number").format(self.leave_type))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.doctype.leave_application.test_leave_application_egypt`
Expected: PASS (4 tests total). If no bench, report NOT EXECUTED with
static-read rationale.

- [ ] **Step 5: Lint**

```bash
pre-commit run --files hrms/hr/doctype/leave_type/leave_type.json hrms/hr/doctype/leave_application/leave_application.py hrms/hr/doctype/leave_application/test_leave_application_egypt.py
```

- [ ] **Step 6: Commit**

```bash
git add hrms/hr/doctype/leave_type/leave_type.json hrms/hr/doctype/leave_application/leave_application.py hrms/hr/doctype/leave_application/test_leave_application_egypt.py
git commit -m "feat(hr): add insurance-required eligibility gate to Leave Type"
```

---

## Task 5: Egypt Leave Type fixtures

**Files:**
- Create: `hrms/regional/egypt/data/leave_types.json`
- Modify: `hrms/regional/egypt/setup.py` (add `make_leave_types()`, call
  from `setup()`)
- Modify: `hrms/regional/egypt/test_setup.py`

**Interfaces:**
- Consumes: `Leave Type.service_tiers` (Task 1),
  `min_years_of_service`/`max_lifetime_allocations` (Task 3),
  `requires_insurance` (Task 4).
- Produces: seeded `Leave Type` records for every entitlement in the
  source document except the tiered-payout Sick Leave (Task 6 handles
  that one separately, since it needs the `is_ppl` compromise explained
  there): `Egypt Regular Leave` (tiered: 8/14/23/38 days — see mapping
  note below), `Egypt Casual Leave` (flat 7 days, `is_earned_leave=0`),
  `Egypt Hard Work Leave` (flat 7 days), `Egypt Paternity Leave` (flat 3
  days, `max_lifetime_allocations=3` — "one day per newborn, max 3 over
  career" is approximated as a 3-day lifetime pool, see note),
  `Egypt Hajj Leave` (flat 30 days, `min_years_of_service=5`,
  `max_lifetime_allocations=1`), `Egypt Maternity Leave` (flat 120 days,
  `max_lifetime_allocations=3`), `Egypt Work Injury Leave` (flat 0 days,
  `allow_negative=1` — see note), `Egypt Military Conscription Leave`
  (flat 0 days, `allow_negative=1`), `Egypt Mission Leave` (flat 0 days,
  `allow_negative=1`), `Egypt Study Leave` (flat 0 days,
  `allow_negative=1`), `Egypt Absence With Permission` (`is_lwp=1`),
  `Egypt Absence Without Permission` (`is_lwp=1`). Function
  `hrms.regional.egypt.setup.make_leave_types() -> None`, called from
  `setup()`.

Mapping notes (document → fixture, since several entitlements in the
document are open-ended/policy-driven rather than fixed day counts, and
`Leave Type` requires no particular starting balance — balances come from
`Leave Policy Detail`/`Leave Policy Assignment`, not from `Leave Type`
itself):
- **Regular Leave tiers**: the document's table (`docs/Payroll System.rtf.doc`,
  "leaves balances entitled" table) gives *combined* Regular+Casual totals
  per tier (15/21/30/45) with Cascasual flat at 7 in every tier. This
  fixture seeds `Egypt Regular Leave` with `service_tiers` = the
  Regular-only figures obtained by subtracting the flat 7-day Casual
  share from each tier total: `{0-1yr: 8, 1-10yr: 14, 10yr-or-50-age-or-10-insurance-yrs: 23, disability: 38}`.
  **The "50 years old OR 10 insurance years" and "disability" tiers are
  eligibility conditions this plan's `service_tiers` table cannot express
  on their own** (it only keys on years-of-service) — flagged explicitly,
  not silently dropped: the 23-day tier is seeded keyed on
  `min_years=10` (the insurance-years threshold, approximated as
  service-years since there's no separate "insurance years" counter
  anywhere in HRMS), and the 38-day disability tier is **not** seedable
  via `service_tiers` at all since it depends on
  `Employee.is_person_of_determination` (Area 1 field), not tenure. The
  implementer must additionally special-case this in
  `get_tiered_annual_allocation`'s caller (`grant_leave_alloc_for_employee`,
  Task 2) — **do not attempt this in the current plan's scope**; file it
  as a follow-up (see Self-Review Notes) since it requires reading
  `Employee.is_person_of_determination` inside `Leave Policy Assignment`,
  which is an Employee-attribute-based override on top of the
  tenure-tiered mechanism this plan builds, not a same-shape extension of
  it.
- **Work Injury / Military Conscription / Mission / Study Leave**: the
  document describes these as event-triggered, variable-duration leave
  (exam days, task duration, injury-committee-determined duration) with
  no fixed annual entitlement — seeded as `allow_negative=1`,
  zero-allocation `Leave Type`s so HR can grant ad-hoc `Leave Allocation`
  records per event rather than an auto-computed annual balance. This
  matches how the document itself describes them (conditions/process, not
  a days figure) — flagged, not a numeric guess.
- **Paternity Leave**: "3 days throughout the work period, one day per
  newborn" is a lifetime pool consumed one allocation at a time, not an
  annual grant — modeled as `max_lifetime_allocations=3` with each
  `Leave Allocation` granting some number of days per birth event (HR
  grants manually per newborn, capped at 3 total allocations by this
  plan's Task 3 mechanism). Annual/tiered auto-accrual doesn't apply here.
- **Public holidays, Weekly rest, Weekly rest2, Instead-of-weekly-rest,
  Instead-of-public-holidays** are **not** seeded as `Leave Type`s — the
  document itself describes these as governed by `Holiday List`
  (existing ERPNext doctype, already used by Overtime Slip's holiday
  detection per the Area 3 plan) and shift/overtime compensation, not
  employee-requested leave balances. Out of scope for this Leave Type
  fixture task; flagged so it isn't mistaken for a silent drop.

- [ ] **Step 1: Write the failing test**

Add to `hrms/regional/egypt/test_setup.py`:

```python
	def test_setup_creates_leave_types(self):
		setup()
		self.assertTrue(frappe.db.exists("Leave Type", "Egypt Regular Leave"))
		self.assertTrue(frappe.db.exists("Leave Type", "Egypt Casual Leave"))
		self.assertTrue(frappe.db.exists("Leave Type", "Egypt Hajj Leave"))

		regular = frappe.get_doc("Leave Type", "Egypt Regular Leave")
		self.assertEqual(len(regular.service_tiers), 3)
		tier_days = {t.min_years: t.days for t in regular.service_tiers}
		self.assertEqual(tier_days[0], 8)
		self.assertEqual(tier_days[1], 14)
		self.assertEqual(tier_days[10], 23)

		hajj = frappe.get_doc("Leave Type", "Egypt Hajj Leave")
		self.assertEqual(hajj.min_years_of_service, 5)
		self.assertEqual(hajj.max_lifetime_allocations, 1)

		absence_with_permission = frappe.get_doc("Leave Type", "Egypt Absence With Permission")
		self.assertTrue(absence_with_permission.is_lwp)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: FAIL — `make_leave_types` doesn't exist yet, `Leave Type`
"Egypt Regular Leave" not found. If no bench, report NOT EXECUTED with
rationale (`hrms/regional/egypt/data/leave_types.json` doesn't exist yet,
confirmed).

- [ ] **Step 3: Create the leave types fixture**

`hrms/regional/egypt/data/leave_types.json`:

```json
[
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Regular Leave",
		"is_carry_forward": 1,
		"service_tiers": [
			{"min_years": 0, "max_years": 1, "days": 8},
			{"min_years": 1, "max_years": 10, "days": 14},
			{"min_years": 10, "max_years": null, "days": 23}
		]
	},
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Casual Leave",
		"is_carry_forward": 0
	},
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Hard Work Leave"
	},
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Paternity Leave",
		"max_lifetime_allocations": 3
	},
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Hajj Leave",
		"min_years_of_service": 5,
		"max_lifetime_allocations": 1
	},
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Maternity Leave",
		"max_lifetime_allocations": 3
	},
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Work Injury Leave",
		"allow_negative": 1,
		"requires_insurance": 1
	},
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Military Conscription Leave",
		"allow_negative": 1
	},
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Mission Leave",
		"allow_negative": 1
	},
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Study Leave",
		"allow_negative": 1
	},
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Absence With Permission",
		"is_lwp": 1
	},
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Absence Without Permission",
		"is_lwp": 1
	}
]
```

- [ ] **Step 4: Add `make_leave_types()` to `setup.py`**

In `hrms/regional/egypt/setup.py`:

```python
def setup():
	make_custom_fields()
	make_income_tax_slabs()
	make_gratuity_rule()
	make_leave_types()
```

```python
def make_leave_types():
	file_path = frappe.get_app_path("hrms", "regional", "egypt", "data", "leave_types.json")
	with open(file_path) as f:
		leave_types = json.load(f)

	for d in leave_types:
		if frappe.db.exists("Leave Type", d["leave_type_name"]):
			continue
		doc = frappe.get_doc(d)
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
```

Add `import json` to the top of `hrms/regional/egypt/setup.py` if not
already present (confirm at implementation time — the file currently
imports `frappe` and `create_custom_fields`/`delete_custom_fields` only,
per Area 1/3's existing header).

- [ ] **Step 5: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: PASS. If no bench, report NOT EXECUTED with static-read
rationale.

- [ ] **Step 6: Lint**

```bash
pre-commit run --files hrms/regional/egypt/data/leave_types.json hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py
```

- [ ] **Step 7: Commit**

```bash
git add hrms/regional/egypt/data/leave_types.json hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py
git commit -m "feat(egypt): seed Leave Type fixtures for Egypt leave entitlements"
```

---

## Task 6: Sick Leave — flat 90-day paid leave type, tiered decay explicitly deferred

**Files:**
- Modify: `hrms/regional/egypt/data/leave_types.json` (add one record)
- Modify: `hrms/regional/egypt/test_setup.py`

**Interfaces:**
- Produces: `Egypt Sick Leave` (`Leave Type`, `min_years_of_service=0`,
  `requires_insurance=1`, flat non-tiered, correct for the first 90 days
  at 100% pay per period — no `is_ppl`, since HRMS's `is_lwp`-only default
  already pays 100% for any leave type where `is_lwp=0` and `is_ppl=0`).

**Why this task exists separately, and what it deliberately does NOT do:**
the source document specifies Sick Leave as three sequential 90-day bands
at 100% / 85% / 75% pay, refreshed on a rolling 3-year cycle, requiring
the employee to be insured. Per the Global Constraints research (see
"Confirmed against current code" above), HRMS's only partial-pay
mechanism — `Leave Type.is_ppl` +
`fraction_of_daily_salary_per_leave` — applies **one fixed fraction to
every day of that leave type used in a payroll period**, with **no
tracking anywhere of cumulative days-used-so-far within a rolling
window**. Building that tracking correctly (three separate `Leave Type`
records with different `fraction_of_daily_salary_per_leave` values, each
capped by a distinct 90-day sub-balance, all resetting together every 3
years, consumed in order) needs new `Leave Allocation`/`Leave Balance`
accounting logic in the payroll-calculation path
(`salary_slip.py:766-889`) that does not exist today and would be
fabricated, not confirmed, if written into this plan. This task therefore
seeds a single **flat, always-100%-paid** `Egypt Sick Leave` type — this
is exactly correct for the first 90 days of any 3-year cycle (matching
the document's first band) and is a safe, conservative default (never
under-pays; may over-pay past day 90 within a cycle until the tiered
mechanism is built). The 85%/75% decay bands are filed as an explicit
follow-up, not silently dropped — see Self-Review Notes.

- [ ] **Step 1: Write the failing test**

Add to `hrms/regional/egypt/test_setup.py`:

```python
	def test_setup_creates_sick_leave_type(self):
		setup()
		sick_leave = frappe.get_doc("Leave Type", "Egypt Sick Leave")
		self.assertTrue(sick_leave.requires_insurance)
		self.assertFalse(sick_leave.is_ppl)
		self.assertFalse(sick_leave.is_lwp)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: FAIL — `frappe.get_doc` raises `DoesNotExistError` for "Egypt
Sick Leave". If no bench, report NOT EXECUTED with rationale.

- [ ] **Step 3: Add the fixture record**

Add to `hrms/regional/egypt/data/leave_types.json` (insert as a new array
element, anywhere in the list — order doesn't matter for
`frappe.db.exists`-guarded inserts):

```json
	{
		"doctype": "Leave Type",
		"leave_type_name": "Egypt Sick Leave",
		"requires_insurance": 1,
		"applicable_after": 0
	},
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: PASS. If no bench, report NOT EXECUTED with static-read
rationale.

- [ ] **Step 5: Lint**

```bash
pre-commit run --files hrms/regional/egypt/data/leave_types.json hrms/regional/egypt/test_setup.py
```

- [ ] **Step 6: Commit**

```bash
git add hrms/regional/egypt/data/leave_types.json hrms/regional/egypt/test_setup.py
git commit -m "feat(egypt): seed flat 100%-paid Sick Leave type, defer tiered payout decay"
```

---

## Self-Review Notes

**Spec coverage (spec §5, Area 2), cross-checked against the source
document directly:**
- Tenure-tiered Regular Leave accrual → Tasks 1, 2, 5 (partial — the
  disability/50-years-old/10-insurance-years tiers are flagged as
  needing an Employee-attribute override on top of tenure, not
  implemented in this plan; see Task 5's mapping notes).
- Once-per-career / max-N-lifetime leave (Hajj, Maternity, Paternity) →
  Task 3, seeded in Task 5.
- Minimum-tenure gating (Hajj: 5 years) → Task 3, seeded in Task 5.
- Insurance-required eligibility (Sick Leave, Work Injury Leave) → Task
  4, seeded in Tasks 5/6.
- Tiered sick-leave payout (90d@100%/90d@85%/90d@75%, 3-year cycle) →
  **explicitly NOT implemented**; Task 6 seeds a safe flat-100%
  approximation and documents exactly why the tiered version is out of
  scope (no existing consumption-tracking machinery to extend; building
  it correctly is a payroll-engine change, not a Leave Type fixture, and
  deserves its own plan once the maintainers confirm the approach —
  candidate designs: (a) three chained `Leave Type`s with
  `max_leaves_allowed` caps consumed in Leave Application UI order, or
  (b) a new `Leave Allocation`-linked day-counter read inside
  `salary_slip.py`'s LWP/PPL calculation, keyed by a rolling 3-year
  window over `Leave Allocation.from_date`. Neither is built here because
  guessing which one the maintainers want and half-implementing it would
  be worse than a clearly flagged gap).
- Other leave types (Hard work, Study, Public holiday comp, Weekly rest
  comp, Work injury, Military conscription, Mission, Absence with/without
  permission) → Task 5, with Public-holiday/Weekly-rest variants
  explicitly scoped out as Holiday-List/shift-compensation concerns, not
  Leave Type concerns (see Task 5 mapping notes).
- Late Policy (5-minute grace period before late-hours deduction) → **not
  covered by this plan** — this is an Attendance/Shift Type concern, not
  a Leave Rules concern; the spec doesn't mention it under Area 2, and
  the document places it under "Employee deductions," which belongs with
  Area 3 (already implemented) or a payroll-deduction-specific follow-up,
  not this plan. Flagged here so it isn't assumed silently covered.

**Explicitly deferred / flagged, not silently dropped:**
- Sick Leave tiered decay (Task 6) — see above, largest deferred item.
- Disability/insurance-years Regular Leave tier (Task 5 mapping notes) —
  needs an Employee-attribute override layered on the tenure-tiers
  mechanism; not attempted here to avoid inventing an untested
  cross-cutting rule inside `grant_leave_alloc_for_employee`.
- Late Policy 5-minute grace period — out of this plan's area entirely,
  noted for whoever scopes the next Attendance-related plan.

**Placeholder scan:** No vague "TBD"/"add error handling" left. Every
deferred item above has a concrete reason it's deferred (missing
machinery, cross-cutting Employee-attribute dependency) and a candidate
next step, not a bare gap.

**Type/name consistency:** `get_tiered_annual_allocation(leave_type_name,
years_of_service)` (Task 2) matches its Task 2 test's call signature
exactly and its Task 2 wiring call site. `_lifetime_allocation_limit_reached`
(Task 3) is a method on `LeavePolicyAssignment`, matching its Task 3 test
call (`assignment._lifetime_allocation_limit_reached(...)`).
`validate_min_years_of_service` / `validate_requires_insurance` (Tasks
3/4) both follow the exact `validate_applicable_after` naming/shape
pattern confirmed in Global Constraints, called from `validate()` in the
order they're added (Task 3 before Task 4, matching each task's Step 3
edit to the same `validate()` method — later task's diff assumes the
earlier task's line is already present).
